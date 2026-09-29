from datetime import datetime

from aiogram import Bot
from sqlalchemy import select

from app.database import async_session
from app.models.user import User
from app.models.muscle_state import MuscleState

MUSCLE_GROUP_LABELS = {
    "chest": "Грудь",
    "back": "Спина",
    "legs": "Ноги",
    "shoulders": "Плечи",
    "biceps": "Бицепс",
    "triceps": "Трицепс",
    "abs": "Пресс",
    "calves": "Икры",
    "forearms": "Предплечья",
}


async def check_and_notify(bot: Bot):
    """Проверяет базу на восстановленные мышцы и рассылает уведомления."""
    now = datetime.utcnow()

    async with async_session() as session:
        result = await session.execute(
            select(MuscleState, User.telegram_id)
            .join(User, User.id == MuscleState.user_id)
            .where(
                MuscleState.fully_recovered_at <= now,
                MuscleState.notified == False,  # noqa: E712
            )
        )
        rows = result.all()

        if not rows:
            return

        # группируем восстановленные мышцы по пользователю,
        # чтобы прислать одно сообщение, а не спамить несколькими
        by_user: dict[int, list[MuscleState]] = {}
        for muscle_state, telegram_id in rows:
            by_user.setdefault(telegram_id, []).append(muscle_state)

        for telegram_id, states in by_user.items():
            names = [
                MUSCLE_GROUP_LABELS.get(s.muscle_group.value, s.muscle_group.value)
                for s in states
            ]
            if len(names) == 1:
                text_msg = f"💪 {names[0]} восстановилась и готова к новой тренировке!"
            else:
                text_msg = f"💪 {', '.join(names)} восстановились и готовы к новой тренировке!"

            try:
                await bot.send_message(telegram_id, text_msg)
            except Exception as e:
                print(f"Не удалось отправить уведомление {telegram_id}: {e}")

            for s in states:
                s.notified = True

        await session.commit()