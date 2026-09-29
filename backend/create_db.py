import asyncio
from app.database import engine, Base
from app import models  # важно: подтягивает все модели, чтобы SQLAlchemy их увидел


async def create_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("Таблицы успешно созданы!")


if __name__ == "__main__":
    asyncio.run(create_tables())