from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import os
from dotenv import load_dotenv

from database import Database
from tasks import check_pending_payments
from handlers import router as user_router

load_dotenv()

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

if TOKEN is None:
    raise ValueError("Токен TELEGRAM_BOT_TOKEN не найден в переменных окружения.")

bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()
db = Database()


async def main():
    await db.connect()
    await db.create_tables()

    scheduler = AsyncIOScheduler()
    scheduler.add_job(check_pending_payments, "interval", minutes=5, args=(db, bot))

    scheduler.start()
    dp.include_router(user_router)

    try:
        print("Бот запущен и база готова!")
        await dp.start_polling(bot, db=db)
    finally:
        scheduler.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
