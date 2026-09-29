from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models.user import User, UserProfile
from app.schemas.user import UserProfileCreate, UserProfileResponse

router = APIRouter(prefix="/api/v1", tags=["users"])


@router.post("/profile", response_model=UserProfileResponse)
async def create_or_update_profile(
    data: UserProfileCreate,
    db: AsyncSession = Depends(get_db),
):
    # 1. Ищем пользователя по telegram_id, если нет — создаём
    result = await db.execute(select(User).where(User.telegram_id == data.telegram_id))
    user = result.scalar_one_or_none()

    if user is None:
        user = User(telegram_id=data.telegram_id)
        db.add(user)
        await db.flush()  # получаем user.id, не завершая транзакцию

    # 2. Ищем существующий профиль этого пользователя
    result = await db.execute(select(UserProfile).where(UserProfile.user_id == user.id))
    profile = result.scalar_one_or_none()

    if profile is None:
        profile = UserProfile(
            user_id=user.id,
            gender=data.gender,
            height_cm=data.height_cm,
            weight_kg=data.weight_kg,
            age=data.age,
            level=data.level,
        )
        db.add(profile)
    else:
        # обновляем существующий профиль новыми данными анкеты
        profile.gender = data.gender
        profile.height_cm = data.height_cm
        profile.weight_kg = data.weight_kg
        profile.age = data.age
        profile.level = data.level

    await db.commit()
    await db.refresh(profile)

    return profile


@router.get("/profile/{telegram_id}", response_model=UserProfileResponse)
async def get_profile(telegram_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.telegram_id == telegram_id))
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(status_code=404, detail="Пользователь не найден")

    result = await db.execute(select(UserProfile).where(UserProfile.user_id == user.id))
    profile = result.scalar_one_or_none()

    if profile is None:
        raise HTTPException(status_code=404, detail="Профиль не заполнен")

    return profile