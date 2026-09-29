from app.schemas.base import UTCModel
from app.models.workout import MuscleGroup
from app.models.exercise import ExerciseCategory


class ExerciseMuscleResponse(UTCModel):
    muscle_group: MuscleGroup
    coefficient: float

    class Config:
        from_attributes = True


class ExerciseResponse(UTCModel):
    id: int
    name: str
    category: ExerciseCategory
    muscles: list[ExerciseMuscleResponse]

    class Config:
        from_attributes = True