"""
Recovery Engine — расчёт времени восстановления мышечных групп.

Решает физиологическую проблему линейного суммирования: раньше несколько
упражнений на одну группу мышц просто складывали часы восстановления
(3 упражнения на грудь -> 100+ часов), что не соответствует спортивной
физиологии и ломает UX.

Модуль учитывает:
  • жёсткий потолок — мышца не может "утомляться" дольше MAX_RECOVERY_HOURS
    независимо от объёма и количества упражнений за сессию;
  • закон убывающей отдачи — каждое следующее упражнение на ту же мышцу
    добавляет всё меньше часов по мере приближения к потолку;
  • базовый вес упражнения по типу (многосуставное / изолирующее) и тоннажу;
  • перенос доли утомления на вторичные мышцы с тем же законом затухания
    (через engagement_coefficient);
  • тумблер "тренировка была вчера" (-24ч от итога сессии);
  • расчёт текущей готовности мышцы в реальном времени (для heatmap).
"""

from __future__ import annotations

from datetime import datetime, timedelta
from enum import Enum

from pydantic import BaseModel, Field

from app.models.user import ExperienceLevel
from app.models.workout import MuscleGroup


# ============================================================================
# Константы
# ============================================================================

#: Жёсткий потолок: мышца не может восстанавливаться дольше 3 суток
#: независимо от объёма и количества упражнений за сессию.
MAX_RECOVERY_HOURS: float = 72.0

#: Сдвиг при пометке "тренировка была вчера".
YESTERDAY_OFFSET_HOURS: float = 24.0

#: Коэффициент уровня подготовки: опытные тренируются тяжелее ->
#: больше микроповреждений -> дольше восстановление.
LEVEL_COEFFICIENTS: dict[ExperienceLevel, float] = {
    ExperienceLevel.beginner: 0.85,
    ExperienceLevel.amateur: 1.0,
    ExperienceLevel.advanced: 1.2,
}


class ExerciseComplexity(str, Enum):
    """Тип упражнения по числу вовлечённых суставов."""

    compound = "compound"      # жим лёжа, присед, тяга и т.п.
    isolation = "isolation"    # разводки, кроссовер, разгибания и т.п.


#: Диапазон базового веса утомления (часы) для "холодной" мышцы от одного
#: упражнения — нижняя граница при малом тоннаже, верхняя при большом.
BASE_HOURS_RANGE: dict[ExerciseComplexity, tuple[float, float]] = {
    ExerciseComplexity.compound: (36.0, 48.0),
    ExerciseComplexity.isolation: (18.0, 24.0),
}


class MuscleStatus(str, Enum):
    peak_fatigue = "peak_fatigue"
    recovering = "recovering"
    recovered = "recovered"


# ============================================================================
# Pydantic-модели
# ============================================================================

class SetVolume(BaseModel):
    """Параметры подхода, из которых считается тоннаж упражнения."""

    sets: int = Field(gt=0, description="Количество подходов")
    reps: int = Field(gt=0, description="Повторений в подходе")
    load_kg: float = Field(ge=0, default=0.0, description="Рабочий вес, кг")
    bodyweight_kg: float = Field(gt=0, description="Вес пользователя, кг")

    @property
    def tonnage(self) -> float:
        """Условный тоннаж: подходы × повторения × (1 + относительная нагрузка).

        Относительная нагрузка (load / bodyweight) отражает, что один и тот же
        подъём тяжелее для лёгкого атлета, чем для тяжёлого.
        """
        relative_load = self.load_kg / self.bodyweight_kg
        return self.sets * self.reps * (1.0 + relative_load)


class ExerciseImpact(BaseModel):
    """Вклад одного упражнения в утомление одной мышечной группы."""

    muscle_group: MuscleGroup
    complexity: ExerciseComplexity
    volume: SetVolume
    engagement_coefficient: float = Field(
        gt=0.0, le=1.0, default=1.0,
        description="1.0 для целевой мышцы, 0.3-0.6 для вторичной",
    )


class MuscleFatigueResult(BaseModel):
    """Итог обработки одной или нескольких ExerciseImpact для одной мышцы."""

    muscle_group: MuscleGroup
    total_hours: float = Field(ge=0.0, le=MAX_RECOVERY_HOURS)
    trained_at: datetime
    fully_recovered_at: datetime


class CurrentFatigue(BaseModel):
    """Состояние восстановления мышцы в конкретный момент времени (для heatmap)."""

    muscle_group: MuscleGroup
    hours_remaining: float = Field(ge=0.0)
    readiness_percent: float = Field(ge=0.0, le=100.0)
    status: MuscleStatus


# ============================================================================
# Recovery Engine
# ============================================================================

class RecoveryEngine:
    """Stateless-калькулятор восстановления. Все методы — чистые функции,
    не обращаются к базе данных — это ответственность вызывающего кода."""

    # ---- базовый вес упражнения ------------------------------------------

    @staticmethod
    def base_added_hours(complexity: ExerciseComplexity, volume: SetVolume) -> float:
        """Базовый вес утомления "холодной" мышцы от одного упражнения,
        интерполированный внутри диапазона типа упражнения по тоннажу.
        """
        low, high = BASE_HOURS_RANGE[complexity]
        tonnage = volume.tonnage

        if tonnage < 50:
            factor = 0.2
        elif tonnage < 150:
            factor = 0.5
        elif tonnage < 300:
            factor = 0.8
        else:
            factor = 1.0

        return low + (high - low) * factor

    # ---- физиологические модификаторы -------------------------------------

    @staticmethod
    def age_coefficient(age: int) -> float:
        if age < 25:
            return 0.9
        if age < 40:
            return 1.0
        if age < 55:
            return 1.15
        return 1.3

    @classmethod
    def apply_physiology(cls, base_hours: float, level: ExperienceLevel, age: int) -> float:
        return base_hours * LEVEL_COEFFICIENTS[level] * cls.age_coefficient(age)

    # ---- закон убывающей отдачи --------------------------------------------

    @staticmethod
    def diminishing_addition(current_hours: float, added_hours: float) -> float:
        """Сколько часов реально добавится к текущему утомлению мышцы.

            real_addition = added_hours * (1 - current_hours / MAX_RECOVERY_HOURS)

        Чем ближе мышца к потолку, тем меньше эффект от нового упражнения —
        это и не даёт нескольким упражнениям на одну группу линейно улетать
        за 100+ часов.
        """
        if current_hours >= MAX_RECOVERY_HOURS:
            return 0.0
        real_addition = added_hours * (1.0 - current_hours / MAX_RECOVERY_HOURS)
        return max(0.0, real_addition)

    @classmethod
    def apply_exercise(
        cls,
        current_hours: float,
        impact: ExerciseImpact,
        level: ExperienceLevel,
        age: int,
    ) -> float:
        """Применяет одно упражнение к текущему накопленному утомлению мышцы
        и возвращает новое значение (часы), гарантированно не превышающее
        MAX_RECOVERY_HOURS.
        """
        base = cls.base_added_hours(impact.complexity, impact.volume)
        modified = cls.apply_physiology(base, level, age)
        per_muscle = modified * impact.engagement_coefficient
        addition = cls.diminishing_addition(current_hours, per_muscle)
        return min(MAX_RECOVERY_HOURS, current_hours + addition)

    # ---- обработка целой тренировочной сессии -------------------------------

    @classmethod
    def process_session(
        cls,
        current_hours: float,
        impacts: list[ExerciseImpact],
        level: ExperienceLevel,
        age: int,
        trained_at: datetime | None = None,
        is_yesterday: bool = False,
    ) -> MuscleFatigueResult:
        """Обрабатывает все упражнения сессии, затрагивающие ОДНУ мышечную
        группу (все impacts должны иметь одинаковый muscle_group),
        последовательно применяя закон убывающей отдачи, а затем один раз
        применяет тумблер "вчера" к итоговому результату всей сессии
        (не к каждому упражнению по отдельности).

        current_hours — текущее накопленное утомление мышцы ДО этой сессии
        (0, если мышца полностью восстановлена; иначе — hours_remaining на
        момент начала новой тренировки).
        """
        if not impacts:
            raise ValueError("impacts не может быть пустым")

        muscle_group = impacts[0].muscle_group
        if any(i.muscle_group != muscle_group for i in impacts):
            raise ValueError("все impacts в сессии должны относиться к одной мышце")

        hours = current_hours
        for impact in impacts:
            hours = cls.apply_exercise(hours, impact, level, age)

        if is_yesterday:
            hours = max(0.0, hours - YESTERDAY_OFFSET_HOURS)

        trained_at = trained_at or datetime.now(datetime.UTC)
        recovered_at = trained_at + timedelta(hours=hours)

        return MuscleFatigueResult(
            muscle_group=muscle_group,
            total_hours=hours,
            trained_at=trained_at,
            fully_recovered_at=recovered_at,
        )

    # ---- состояние в реальном времени ----------------------------------------

    @staticmethod
    def get_current_fatigue(
        last_workout_time: datetime,
        calculated_hours: float,
        muscle_group: MuscleGroup,
        now: datetime | None = None,
    ) -> CurrentFatigue:
        """Сколько часов осталось до полного восстановления и % готовности
        мышцы прямо сейчас (используется для heatmap)."""
        now = now or datetime.now(datetime.UTC)

        if calculated_hours <= 0:
            return CurrentFatigue(
                muscle_group=muscle_group,
                hours_remaining=0.0,
                readiness_percent=100.0,
                status=MuscleStatus.recovered,
            )

        elapsed_hours = (now - last_workout_time).total_seconds() / 3600.0
        hours_remaining = max(0.0, calculated_hours - elapsed_hours)
        readiness_percent = max(
            0.0, min(100.0, (1.0 - hours_remaining / calculated_hours) * 100.0)
        )

        if hours_remaining <= 0:
            status = MuscleStatus.recovered
        elif readiness_percent >= 50.0:
            status = MuscleStatus.recovering
        else:
            status = MuscleStatus.peak_fatigue

        return CurrentFatigue(
            muscle_group=muscle_group,
            hours_remaining=round(hours_remaining, 1),
            readiness_percent=round(readiness_percent, 1),
            status=status,
        )
