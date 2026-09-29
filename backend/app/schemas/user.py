from datetime import datetime
from pydantic import Field, computed_field

from app.models.user import Gender, ExperienceLevel
from app.schemas.base import UTCModel


class UserProfileCreate(UTCModel):
    """То, что фронтенд присылает при заполнении анкеты онбординга."""
    telegram_id: int
    gender: Gender
    height_cm: float = Field(..., gt=100, lt=250)
    weight_kg: float = Field(..., gt=30, lt=300)
    age: int = Field(..., ge=12, le=100)
    level: ExperienceLevel


class UserProfileResponse(UTCModel):
    """То, что бэкенд отдаёт обратно после сохранения."""
    id: int
    user_id: int
    gender: Gender
    height_cm: float
    weight_kg: float
    age: int
    level: ExperienceLevel
    created_at: datetime
    updated_at: datetime | None = None

    @computed_field
    @property
    def bmi(self) -> float:
        return round(self.weight_kg / ((self.height_cm / 100) ** 2), 2)

    class Config:
        from_attributes = True