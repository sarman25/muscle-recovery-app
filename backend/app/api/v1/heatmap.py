from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models.user import User
from app.models.muscle_state import MuscleState
from app.schemas.heatmap import MuscleHeatmapResponse, MuscleFatigueItem, MuscleStatus, COLOR_MAP
from app.services.recovery_engine import RecoveryEngine

router = APIRouter(prefix="/api/v1", tags=["heatmap"])


@router.get("/heatmap/{telegram_id}", response_model=MuscleHeatmapResponse)
async def get_heatmap(telegram_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.telegram_id == telegram_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=404, detail="Пользователь не найден")

    result = await db.execute(select(MuscleState).where(MuscleState.user_id == user.id))
    muscle_states = result.scalars().all()

    now = datetime.utcnow()
    muscles = []

    for state in muscle_states:
        # Длительность, на которую изначально была рассчитана эта запись
        # (RecoveryEngine хранит итог как trained_at + total_hours).
        total_hours = (state.fully_recovered_at - state.trained_at).total_seconds() / 3600.0

        fatigue = RecoveryEngine.get_current_fatigue(
            last_workout_time=state.trained_at,
            calculated_hours=total_hours,
            muscle_group=state.muscle_group,
            now=now,
        )

        # У schemas.heatmap.MuscleStatus те же значения ("peak_fatigue" /
        # "recovering" / "recovered"), что и у recovery_engine.MuscleStatus —
        # это два независимых enum'а с одинаковыми строками, сопоставляем по .value.
        status = MuscleStatus(fatigue.status.value)
        # readiness_percent (0% только что тренировали -> 100% восстановлена)
        # переворачиваем в fatigue_percent (100% только что тренировали -> 0%),
        # как ожидает существующая схема ответа.
        fatigue_percent = round(100.0 - fatigue.readiness_percent, 1)

        muscles.append(
            MuscleFatigueItem(
                muscle_group=state.muscle_group,
                status=status,
                fatigue_percent=fatigue_percent,
                color_hex=COLOR_MAP[status],
                trained_at=state.trained_at,
                fully_recovered_at=state.fully_recovered_at,
                hours_remaining=fatigue.hours_remaining,
            )
        )

    return MuscleHeatmapResponse(user_id=user.id, generated_at=now, muscles=muscles)