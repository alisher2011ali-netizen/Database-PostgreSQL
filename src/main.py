from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import BotCommand
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


async def set_main_menu(bot: Bot):
    main_menu_commands = [
        BotCommand(command="/start", description="Запустить бота"),
        BotCommand(command="/view_goods", description="🛒 Каталог товаров"),
        BotCommand(command="/profile", description="👤 Личный кабинет"),
        BotCommand(command="/deposit", description="➕ Пополнить баланс"),
        BotCommand(command="/help", description="❓ Справка"),
    ]
    await bot.set_my_commands(main_menu_commands)


async def main():
    await db.connect()
    await db.create_tables()

    scheduler = AsyncIOScheduler()

    scheduler.add_job(check_pending_payments, "interval", minutes=5, args=(db, bot))
    scheduler.start()

    await set_main_menu(bot)

    dp.include_router(user_router)

    try:
        print("Бот запущен и база готова!")
        await dp.start_polling(bot, db=db)
    finally:
        scheduler.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
