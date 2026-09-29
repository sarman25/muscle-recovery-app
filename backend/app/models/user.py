from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import String, Integer, Float, DateTime, Enum, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Gender(str, PyEnum):
    male = "male"
    female = "female"


class ExperienceLevel(str, PyEnum):
    beginner = "beginner"
    amateur = "amateur"
    advanced = "advanced"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    telegram_id: Mapped[int] = mapped_column(Integer, unique=True, index=True)
    username: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    # связь "один пользователь -> один профиль"
    profile: Mapped["UserProfile"] = relationship(back_populates="user", uselist=False)


class UserProfile(Base):
    __tablename__ = "user_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True)

    gender: Mapped[Gender] = mapped_column(Enum(Gender))
    height_cm: Mapped[float] = mapped_column(Float)
    weight_kg: Mapped[float] = mapped_column(Float)
    age: Mapped[int] = mapped_column(Integer)
    level: Mapped[ExperienceLevel] = mapped_column(Enum(ExperienceLevel))

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, onupdate=func.now(), nullable=True)

    user: Mapped["User"] = relationship(back_populates="profile")