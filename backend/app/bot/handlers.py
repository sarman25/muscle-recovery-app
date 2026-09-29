from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message, WebAppInfo, InlineKeyboardMarkup, InlineKeyboardButton

router = Router()

# Временно — ссылка на фронтенд. Позже заменим на постоянный адрес после деплоя.
WEBAPP_URL = "https://frontend-rose-phi-lx0ntcomjx.vercel.app"


@router.message(CommandStart())
async def cmd_start(message: Message):
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="💪 Открыть приложение",
                    web_app=WebAppInfo(url=WEBAPP_URL),
                )
            ]
        ]
    )

    await message.answer(
        "Привет! 👋\n\n"
        "Я помогу тебе следить за восстановлением мышц после тренировок.\n"
        "Нажми кнопку ниже, чтобы открыть приложение.",
        reply_markup=keyboard,
    )