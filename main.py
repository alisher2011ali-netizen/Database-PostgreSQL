from aiogram import Bot, Dispatcher
import asyncio
import os
from dotenv import load_dotenv

from database import Database
from handlers import router as user_router

load_dotenv()

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

if TOKEN is None:
    raise ValueError("Токен TELEGRAM_BOT_TOKEN не найден в переменных окружения.")

bot = Bot(token=TOKEN)
dp = Dispatcher()
db = Database()


async def main():
    await db.connect()
    await db.create_tables()

    dp.include_router(user_router)

    print("Бот запущен и база готова!")
    await dp.start_polling(bot, db=db)


if __name__ == "__main__":
    asyncio.run(main())
