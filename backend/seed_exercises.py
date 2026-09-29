import asyncio

from app.database import async_session
from app.models.exercise import Exercise, ExerciseMuscle
from sqlalchemy import select

EXERCISES = [
    # ГРУДЬ
    {"name": "Жим штанги лёжа", "category": "chest", "muscles": [("chest", 1.0), ("triceps", 0.5), ("shoulders", 0.3)]},
    {"name": "Жим гантелей на наклонной скамье", "category": "chest", "muscles": [("chest", 1.0), ("shoulders", 0.4), ("triceps", 0.3)]},
    {"name": "Отжимания от пола", "category": "chest", "muscles": [("chest", 1.0), ("triceps", 0.5), ("abs", 0.2)]},
    {"name": "Сведение в бабочке", "category": "chest", "muscles": [("chest", 1.0)]},

    # СПИНА
    {"name": "Тяга верхнего блока", "category": "back", "muscles": [("back", 1.0), ("biceps", 0.4)]},
    {"name": "Тяга штанги в наклоне", "category": "back", "muscles": [("back", 1.0), ("biceps", 0.3), ("shoulders", 0.2)]},
    {"name": "Подтягивания", "category": "back", "muscles": [("back", 1.0), ("biceps", 0.5), ("forearms", 0.3)]},

    # НОГИ
    {"name": "Приседания со штангой", "category": "legs", "muscles": [("legs", 1.0), ("abs", 0.2)]},
    {"name": "Румынская тяга", "category": "legs", "muscles": [("legs", 1.0), ("back", 0.3)]},
    {"name": "Выпады с гантелями", "category": "legs", "muscles": [("legs", 1.0), ("calves", 0.2)]},
    {"name": "Подъём на носки", "category": "legs", "muscles": [("calves", 1.0)]},

    # ПЛЕЧИ
    {"name": "Жим гантелей сидя (плечи)", "category": "shoulders", "muscles": [("shoulders", 1.0), ("triceps", 0.3)]},
    {"name": "Махи гантелями в стороны", "category": "shoulders", "muscles": [("shoulders", 1.0)]},

    # РУКИ
    {"name": "Подъём штанги на бицепс", "category": "arms", "muscles": [("biceps", 1.0), ("forearms", 0.3)]},
    {"name": "Молотки с гантелями", "category": "arms", "muscles": [("biceps", 1.0), ("forearms", 0.4)]},
    {"name": "Французский жим", "category": "arms", "muscles": [("triceps", 1.0)]},
    {"name": "Разгибание рук на блоке", "category": "arms", "muscles": [("triceps", 1.0)]},

    # ПРЕСС
    {"name": "Скручивания", "category": "abs", "muscles": [("abs", 1.0)]},
    {"name": "Планка", "category": "abs", "muscles": [("abs", 1.0), ("back", 0.2)]},

    # КАРДИО (без мышц — не влияет на heatmap)
    {"name": "Бег", "category": "cardio", "muscles": []},
    {"name": "Велотренажёр", "category": "cardio", "muscles": []},
    {"name": "Скакалка", "category": "cardio", "muscles": []},
]


async def seed():
    async with async_session() as session:
        for ex_data in EXERCISES:
            result = await session.execute(select(Exercise).where(Exercise.name == ex_data["name"]))
            existing = result.scalar_one_or_none()
            if existing:
                continue

            exercise = Exercise(name=ex_data["name"], category=ex_data["category"])
            session.add(exercise)
            await session.flush()

            for muscle_group, coefficient in ex_data["muscles"]:
                session.add(
                    ExerciseMuscle(
                        exercise_id=exercise.id,
                        muscle_group=muscle_group,
                        coefficient=coefficient,
                    )
                )

        await session.commit()
    print("Справочник упражнений заполнен!")


if __name__ == "__main__":
    asyncio.run(seed())