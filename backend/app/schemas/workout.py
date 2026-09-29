from datetime import datetime
from pydantic import Field

from app.schemas.base import UTCModel


class WorkoutSetCreate(UTCModel):
    exercise_id: int

    # силовые (обязательны для не-кардио упражнений — проверяется в коде эндпоинта)
    sets: int | None = Field(default=None, gt=0, le=20)
    reps: int | None = Field(default=None, gt=0, le=200)
    load_kg: float | None = Field(default=0, ge=0, le=500)

    # кардио
    duration_minutes: float | None = Field(default=None, gt=0, le=600)
    distance_km: float | None = Field(default=None, gt=0, le=200)


class WorkoutCreate(UTCModel):
    telegram_id: int
    trained_at_offset_hours: int = 0  # 0 = сегодня, -24 = вчера
    exercises: list[WorkoutSetCreate]


class WorkoutSetResponse(UTCModel):
    id: int
    exercise_id: int
    exercise_name: str
    sets: int | None = None
    reps: int | None = None
    load_kg: float | None = None
    duration_minutes: float | None = None
    distance_km: float | None = None
    created_at: datetime

    class Config:
        from_attributes = True


class WorkoutResponse(UTCModel):
    id: int
    user_id: int
    started_at: datetime
    exercises: list[WorkoutSetResponse]

    class Config:
        from_attributes = True