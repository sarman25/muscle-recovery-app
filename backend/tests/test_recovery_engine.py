"""
Тесты Recovery Engine: жёсткий потолок, убывающая отдача, тумблер "вчера",
расчёт готовности в реальном времени.

Запуск через pytest:
    pytest test_recovery_engine.py -v

Либо напрямую (обычными assert, без pytest):
    python test_recovery_engine.py
"""
from datetime import datetime, timedelta

import pytest

from app.models.user import ExperienceLevel
from app.models.workout import MuscleGroup
from app.services.recovery_engine import (
    MAX_RECOVERY_HOURS,
    ExerciseComplexity,
    ExerciseImpact,
    MuscleStatus,
    RecoveryEngine,
    SetVolume,
)


def _compound_impact(
    muscle: MuscleGroup = MuscleGroup.chest, engagement: float = 1.0
) -> ExerciseImpact:
    """Типовой жим лёжа: 3 подхода по 10 повторений с 40кг при массе тела 80кг."""
    return ExerciseImpact(
        muscle_group=muscle,
        complexity=ExerciseComplexity.compound,
        engagement_coefficient=engagement,
        volume=SetVolume(sets=3, reps=10, load_kg=40, bodyweight_kg=80),
    )


def test_single_exercise_within_base_range():
    """Одно упражнение остаётся в пределах базового диапазона (36-48ч для compound)."""
    result = RecoveryEngine.process_session(
        current_hours=0.0,
        impacts=[_compound_impact()],
        level=ExperienceLevel.amateur,
        age=30,
    )
    assert 36.0 <= result.total_hours <= 48.0


def test_three_exercises_stay_within_60_65_hours():
    """Ключевой кейс из задания: 3 упражнения подряд на грудь не улетают за
    100+ часов, а укладываются в 60-65ч благодаря убывающей отдаче."""
    impacts = [_compound_impact() for _ in range(3)]
    result = RecoveryEngine.process_session(
        current_hours=0.0,
        impacts=impacts,
        level=ExperienceLevel.amateur,
        age=30,
    )
    assert result.total_hours <= 65.0, f"Получили {result.total_hours}ч — потолок нарушен"
    assert result.total_hours >= 58.0, "Убывающая отдача не должна душить рост слишком рано"


def test_diminishing_returns_each_addition_smaller():
    """Каждое следующее упражнение должно добавлять меньше часов, чем предыдущее."""
    hours = 0.0
    additions = []
    for _ in range(4):
        new_hours = RecoveryEngine.apply_exercise(
            hours, _compound_impact(), ExperienceLevel.amateur, 30
        )
        additions.append(new_hours - hours)
        hours = new_hours

    assert additions == sorted(additions, reverse=True), additions
    assert all(a > 0 for a in additions)


def test_hard_cap_never_exceeded_even_with_many_exercises():
    """Даже 10 тяжёлых упражнений подряд (плюс худшие физиологические
    коэффициенты) не должны пробить потолок в 72ч."""
    impacts = [_compound_impact() for _ in range(10)]
    result = RecoveryEngine.process_session(
        current_hours=0.0,
        impacts=impacts,
        level=ExperienceLevel.advanced,
        age=60,
    )
    assert result.total_hours <= MAX_RECOVERY_HOURS


def test_hard_cap_respected_starting_from_near_max():
    """Если мышца уже почти на потолке, новое упражнение не должно его пробить."""
    new_hours = RecoveryEngine.apply_exercise(
        current_hours=70.0,
        impact=_compound_impact(),
        level=ExperienceLevel.advanced,
        age=60,
    )
    assert new_hours <= MAX_RECOVERY_HOURS


def test_secondary_muscle_gets_reduced_fraction():
    """Вторичная мышца (например, трицепс при жиме лёжа) должна получать
    меньше часов, чем основная (грудь), за счёт engagement_coefficient."""
    primary = RecoveryEngine.apply_exercise(
        0.0, _compound_impact(MuscleGroup.chest, engagement=1.0),
        ExperienceLevel.amateur, 30,
    )
    secondary = RecoveryEngine.apply_exercise(
        0.0, _compound_impact(MuscleGroup.triceps, engagement=0.4),
        ExperienceLevel.amateur, 30,
    )
    assert secondary < primary


def test_yesterday_toggle_subtracts_24_hours():
    """Тумблер 'вчера' должен вычитать 24ч из итогового результата сессии
    (а не из каждого упражнения по отдельности)."""
    impacts = [_compound_impact()]
    normal = RecoveryEngine.process_session(0.0, impacts, ExperienceLevel.amateur, 30)
    backdated = RecoveryEngine.process_session(
        0.0, impacts, ExperienceLevel.amateur, 30, is_yesterday=True
    )
    assert backdated.total_hours == pytest.approx(max(0.0, normal.total_hours - 24.0))


def test_yesterday_toggle_never_goes_negative():
    """Если итог меньше 24ч, вычитание не должно уходить в минус."""
    light_impact = ExerciseImpact(
        muscle_group=MuscleGroup.biceps,
        complexity=ExerciseComplexity.isolation,
        volume=SetVolume(sets=2, reps=10, load_kg=5, bodyweight_kg=80),
    )
    result = RecoveryEngine.process_session(
        0.0, [light_impact], ExperienceLevel.beginner, 22, is_yesterday=True
    )
    assert result.total_hours >= 0.0


def test_get_current_fatigue_freshly_trained():
    """Сразу после тренировки готовность 0%, статус — peak_fatigue."""
    now = datetime.utcnow()
    fatigue = RecoveryEngine.get_current_fatigue(
        last_workout_time=now, calculated_hours=48.0, muscle_group=MuscleGroup.chest, now=now
    )
    assert fatigue.readiness_percent == 0.0
    assert fatigue.status == MuscleStatus.peak_fatigue
    assert fatigue.hours_remaining == pytest.approx(48.0)


def test_get_current_fatigue_fully_recovered_after_deadline():
    """После истечения расчётного времени готовность 100%, статус — recovered."""
    trained_at = datetime.utcnow() - timedelta(hours=100)
    fatigue = RecoveryEngine.get_current_fatigue(
        last_workout_time=trained_at, calculated_hours=48.0, muscle_group=MuscleGroup.chest
    )
    assert fatigue.readiness_percent == 100.0
    assert fatigue.hours_remaining == 0.0
    assert fatigue.status == MuscleStatus.recovered


def test_get_current_fatigue_halfway():
    """На полпути готовность ~50%, статус — recovering."""
    trained_at = datetime.utcnow() - timedelta(hours=24)
    fatigue = RecoveryEngine.get_current_fatigue(
        last_workout_time=trained_at, calculated_hours=48.0, muscle_group=MuscleGroup.chest
    )
    assert 45.0 <= fatigue.readiness_percent <= 55.0
    assert fatigue.status == MuscleStatus.recovering


if __name__ == "__main__":
    import sys

    tests = [obj for name, obj in list(globals().items()) if name.startswith("test_")]
    failed = 0
    for test in tests:
        try:
            test()
            print(f"OK   {test.__name__}")
        except AssertionError as e:
            failed += 1
            print(f"FAIL {test.__name__}: {e}")
    print(f"\n{len(tests) - failed}/{len(tests)} passed")
    sys.exit(1 if failed else 0)
