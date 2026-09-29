from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.exercise import Exercise
from app.schemas.exercise import ExerciseResponse

router = APIRouter(prefix="/api/v1", tags=["exercises"])


@router.get("/exercises", response_model=list[ExerciseResponse])
async def list_exercises(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Exercise).options(selectinload(Exercise.muscles))
    )
    return result.scalars().all()
