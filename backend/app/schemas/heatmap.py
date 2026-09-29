from datetime import datetime
from enum import Enum as PyEnum

from app.models.workout import MuscleGroup
from app.schemas.base import UTCModel


class MuscleStatus(str, PyEnum):
    peak_fatigue = "peak_fatigue"   # красный
    recovering = "recovering"        # оранжевый
    recovered = "recovered"          # зелёный


COLOR_MAP: dict[MuscleStatus, str] = {
    MuscleStatus.peak_fatigue: "#FF0000",
    MuscleStatus.recovering: "#FFA500",
    MuscleStatus.recovered: "#00FF00",
}


class MuscleFatigueItem(UTCModel):
    muscle_group: MuscleGroup
    status: MuscleStatus
    fatigue_percent: float
    color_hex: str
    trained_at: datetime
    fully_recovered_at: datetime
    hours_remaining: float


class MuscleHeatmapResponse(UTCModel):
    user_id: int
    generated_at: datetime
    muscles: list[MuscleFatigueItem]