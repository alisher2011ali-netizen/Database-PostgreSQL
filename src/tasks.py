from database import Database
from payment import check_yoomoney_payment
from aiogram import Bot
import os

YOOMONEY_TOKEN = os.getenv("YOOMONEY_TOKEN")


async def check_pending_payments(db: Database, bot: Bot):
    pending_payments = await db.get_unpaid_payments()

    for pay in pending_payments:
        label = pay["label"]
        user_id = pay["user_id"]
        amount = pay["amount"]

        is_confirmed = await check_yoomoney_payment(YOOMONEY_TOKEN, label)

        if is_confirmed:
            await db.set_payment_paid(label)
            await db.add_money(user_id, amount, "Автоматическое зачисление")

            try:
                await bot.send_message(
                    user_id,
                    f"✅ Мы обнаружили вашу оплату на сумму {amount} руб. Баланс пополнен!",
                )
            except Exception as e:
                print(f"Не удалось отправить сообщение пользователю {user_id}: {e}")
