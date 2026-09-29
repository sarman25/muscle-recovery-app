from enum import Enum as PyEnum

from sqlalchemy import String, Float, ForeignKey, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.workout import MuscleGroup


class ExerciseCategory(str, PyEnum):
    chest = "chest"
    back = "back"
    legs = "legs"
    shoulders = "shoulders"
    arms = "arms"
    abs = "abs"
    cardio = "cardio"


class Exercise(Base):
    __tablename__ = "exercises"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(150), unique=True)
    category: Mapped[ExerciseCategory] = mapped_column(Enum(ExerciseCategory))

    muscles: Mapped[list["ExerciseMuscle"]] = relationship(back_populates="exercise")


class ExerciseMuscle(Base):
    """Связь: какое упражнение нагружает какую мышцу и насколько сильно."""
    __tablename__ = "exercise_muscles"

    id: Mapped[int] = mapped_column(primary_key=True)
    exercise_id: Mapped[int] = mapped_column(ForeignKey("exercises.id"))
    muscle_group: Mapped[MuscleGroup] = mapped_column(Enum(MuscleGroup))
    coefficient: Mapped[float] = mapped_column(Float, default=1.0)

    exercise: Mapped["Exercise"] = relationship(back_populates="muscles")