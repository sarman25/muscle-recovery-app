from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, UniqueConstraint, func, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.workout import MuscleGroup
from sqlalchemy import Enum


class MuscleState(Base):
    __tablename__ = "muscle_states"
    __table_args__ = (
        UniqueConstraint("user_id", "muscle_group", name="uq_user_muscle"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    muscle_group: Mapped[MuscleGroup] = mapped_column(Enum(MuscleGroup))

    trained_at: Mapped[datetime] = mapped_column(DateTime)
    fully_recovered_at: Mapped[datetime] = mapped_column(DateTime)
    notified: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")

    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())