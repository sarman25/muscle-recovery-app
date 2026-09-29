import asyncio
import logging
import os

from aiohttp import web
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.bot.bot import bot, dp
from app.bot.handlers import router
from app.services.notifier import check_and_notify


async def health_handler(request):
    return web.Response(text="Bot is running")


async def start_health_server():
    app = web.Application()
    app.router.add_get("/", health_handler)

    port = int(os.environ.get("PORT", 10000))
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()


async def main():
    logging.basicConfig(level=logging.INFO)
    dp.include_router(router)

    await start_health_server()

    scheduler = AsyncIOScheduler()
    scheduler.add_job(check_and_notify, "interval", minutes=5, args=[bot])
    scheduler.start()

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())