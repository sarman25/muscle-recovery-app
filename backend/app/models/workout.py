from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import Integer, Float, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class MuscleGroup(str, PyEnum):
    chest = "chest"
    back = "back"
    legs = "legs"
    shoulders = "shoulders"
    biceps = "biceps"
    triceps = "triceps"
    abs = "abs"
    calves = "calves"
    forearms = "forearms"


class Workout(Base):
    __tablename__ = "workouts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    started_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    sets: Mapped[list["WorkoutSet"]] = relationship(back_populates="workout")


class WorkoutSet(Base):
    __tablename__ = "workout_sets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    workout_id: Mapped[int] = mapped_column(ForeignKey("workouts.id"), index=True)
    exercise_id: Mapped[int] = mapped_column(ForeignKey("exercises.id"))

    # силовые поля — опциональны (не нужны для кардио)
    sets: Mapped[int | None] = mapped_column(Integer, nullable=True)
    reps: Mapped[int | None] = mapped_column(Integer, nullable=True)
    load_kg: Mapped[float | None] = mapped_column(Float, default=0, nullable=True)

    # кардио-поля — опциональны (не нужны для силовых)
    duration_minutes: Mapped[float | None] = mapped_column(Float, nullable=True)
    distance_km: Mapped[float | None] = mapped_column(Float, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    workout: Mapped["Workout"] = relationship(back_populates="sets")