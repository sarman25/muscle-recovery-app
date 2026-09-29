from collections import defaultdict
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.user import User, UserProfile
from app.models.workout import Workout, WorkoutSet, MuscleGroup
from app.models.muscle_state import MuscleState
from app.models.exercise import Exercise, ExerciseCategory
from app.schemas.workout import WorkoutCreate, WorkoutResponse, WorkoutSetResponse
from app.services.recovery_engine import (
    RecoveryEngine,
    ExerciseComplexity,
    ExerciseImpact,
    SetVolume,
)

router = APIRouter(prefix="/api/v1", tags=["workouts"])


def _infer_complexity(muscle_count: int) -> ExerciseComplexity:
    """В модели Exercise пока нет отдельного поля complexity, поэтому определяем
    тип упражнения эвристикой без изменения схемы БД: если упражнение задействует
    2+ мышцы (основную + хотя бы одну вторичную), считаем его многосуставным
    (compound), иначе — изолирующим (isolation). На текущем справочнике
    (seed_exercises.py) эта эвристика совпадает с реальной классификацией
    упражнений. Если захочешь точности — добавь поле complexity в Exercise и
    замени эту функцию на чтение поля."""
    return ExerciseComplexity.compound if muscle_count >= 2 else ExerciseComplexity.isolation


@router.post("/workouts", response_model=WorkoutResponse)
async def log_workout(data: WorkoutCreate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.telegram_id == data.telegram_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=404, detail="Пользователь не найден")

    result = await db.execute(select(UserProfile).where(UserProfile.user_id == user.id))
    profile = result.scalar_one_or_none()
    if profile is None:
        raise HTTPException(status_code=400, detail="Сначала заполните анкету профиля")

    # Если пользователь отметил "вчера" — сдвигаем базовую точку времени назад.
    # ВАЖНО: этот сдвиг уже даёт тот же эффект на итоговое fully_recovered_at,
    # что и is_yesterday-вычитание -24ч внутри RecoveryEngine.process_session
    # (сдвинуть trained_at на -24ч и оставить длительность — то же самое,
    # что оставить trained_at=now и вычесть 24ч из длительности). Поэтому
    # здесь used только сдвиг base_time, а is_yesterday в process_session
    # ниже всегда False — иначе эффект применился бы дважды.
    base_time = datetime.utcnow() + timedelta(hours=data.trained_at_offset_hours)

    workout = Workout(user_id=user.id, started_at=base_time)
    db.add(workout)
    await db.flush()

    response_sets = []
    # Копим все impact'ы по мышцам за ВСЮ сессию — так убывающая отдача
    # применяется последовательно по всем упражнениям сессии, а не по одному
    # изолированно (что и было исходным багом с линейным суммированием).
    impacts_by_muscle: dict[MuscleGroup, list[ExerciseImpact]] = defaultdict(list)

    for item in data.exercises:
        result = await db.execute(
            select(Exercise)
            .options(selectinload(Exercise.muscles))
            .where(Exercise.id == item.exercise_id)
        )
        exercise = result.scalar_one_or_none()
        if exercise is None:
            raise HTTPException(status_code=404, detail=f"Упражнение id={item.exercise_id} не найдено")

        is_cardio = exercise.category == ExerciseCategory.cardio

        if not is_cardio and (item.sets is None or item.reps is None):
            raise HTTPException(status_code=422, detail="Для силового упражнения нужны подходы и повторения")

        workout_set = WorkoutSet(
            workout_id=workout.id,
            exercise_id=exercise.id,
            sets=item.sets,
            reps=item.reps,
            load_kg=item.load_kg,
            duration_minutes=item.duration_minutes,
            distance_km=item.distance_km,
            created_at=base_time,
        )
        db.add(workout_set)

        # Кардио не влияет на восстановление мышц — просто логируется как активность.
        if not is_cardio:
            complexity = _infer_complexity(len(exercise.muscles))
            volume = SetVolume(
                sets=item.sets,
                reps=item.reps,
                load_kg=item.load_kg or 0,
                bodyweight_kg=profile.weight_kg,
            )
            for exercise_muscle in exercise.muscles:
                impacts_by_muscle[exercise_muscle.muscle_group].append(
                    ExerciseImpact(
                        muscle_group=exercise_muscle.muscle_group,
                        complexity=complexity,
                        volume=volume,
                        engagement_coefficient=exercise_muscle.coefficient,
                    )
                )

        response_sets.append(
            WorkoutSetResponse(
                id=0,
                exercise_id=exercise.id,
                exercise_name=exercise.name,
                sets=item.sets,
                reps=item.reps,
                load_kg=item.load_kg,
                duration_minutes=item.duration_minutes,
                distance_km=item.distance_km,
                created_at=base_time,
            )
        )

    # Применяем Recovery Engine один раз НА МЫШЦУ — сразу по всем упражнениям
    # сессии, которые её затронули, чтобы закон убывающей отдачи сработал
    # правильно (3 упражнения на грудь подряд -> не более 60-65ч, а не 100+).
    for muscle_group, impacts in impacts_by_muscle.items():
        result = await db.execute(
            select(MuscleState).where(
                MuscleState.user_id == user.id,
                MuscleState.muscle_group == muscle_group,
            )
        )
        muscle_state = result.scalar_one_or_none()

        if muscle_state is not None:
            # Сколько часов "утомления" ещё оставалось у мышцы на момент
            # начала ЭТОЙ тренировки (а не прямо сейчас) — учитывает и
            # случай бэкдейта ("вчера"), и случай, когда мышца уже
            # восстановилась (тогда current_hours получится 0).
            prior_total_hours = (
                muscle_state.fully_recovered_at - muscle_state.trained_at
            ).total_seconds() / 3600.0
            current_fatigue = RecoveryEngine.get_current_fatigue(
                last_workout_time=muscle_state.trained_at,
                calculated_hours=prior_total_hours,
                muscle_group=muscle_group,
                now=base_time,
            )
            current_hours = current_fatigue.hours_remaining
        else:
            current_hours = 0.0

        session_result = RecoveryEngine.process_session(
            current_hours=current_hours,
            impacts=impacts,
            level=profile.level,
            age=profile.age,
            trained_at=base_time,
            is_yesterday=False,  # см. комментарий про base_time выше
        )

        if muscle_state is None:
            db.add(
                MuscleState(
                    user_id=user.id,
                    muscle_group=muscle_group,
                    trained_at=session_result.trained_at,
                    fully_recovered_at=session_result.fully_recovered_at,
                    notified=False,
                )
            )
        else:
            muscle_state.trained_at = session_result.trained_at
            muscle_state.fully_recovered_at = session_result.fully_recovered_at
            muscle_state.notified = False

    await db.commit()
    await db.refresh(workout)

    saved_sets = (
        await db.execute(select(WorkoutSet).where(WorkoutSet.workout_id == workout.id))
    ).scalars().all()
    for i, ws in enumerate(saved_sets):
        response_sets[i].id = ws.id

    return WorkoutResponse(
        id=workout.id,
        user_id=workout.user_id,
        started_at=workout.started_at,
        exercises=response_sets,
    )