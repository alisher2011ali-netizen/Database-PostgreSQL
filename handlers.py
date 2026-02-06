from aiogram import Router, F, types
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from dotenv import load_dotenv
import os
from decimal import Decimal, InvalidOperation

from database import Database
from states import *
from payment import *

load_dotenv()

YOOMONEY_WALLET = os.getenv("YOOMONEY_WALLET")
YOOMONEY_TOKEN = os.getenv("YOOMONEY_TOKEN")
router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message, db: Database):
    user_id = message.from_user.id

    await db.register_user(user_id, message.from_user.username)
    user = await db.get_user(user_id)
    if not user:
        await message.answer(
            "Похоже что-то не так. Попробуйте запустить бота еще раз. /start"
        )
        return

    await message.answer(
        "Вы успешно зарегистрированы! Чтобы пополнить счет используйте /top_up_balance"
    )


@router.message(Command("top_up_balance"))
async def add_money_handler(message: Message, state: FSMContext):

    await message.answer("Введите сумму, на которую хотите пополнить баланс:")
    await state.set_state(AddMoney.waiting_for_amount)


@router.message(AddMoney.waiting_for_amount)
async def finish_adding_money(message: Message, state: FSMContext, db: Database):
    user_id = message.from_user.id
    if not message.text:
        await message.answer("Укажите сумму в виде цифр.")
        return
    try:
        amount = Decimal(message.text.replace(",", "."))
        amount = amount.quantize(Decimal("0.00"))

        if amount <= 0:
            await message.answer("Сумма должна быть больше нуля.")
            return

        pay_url, label = create_yoomoney_link(YOOMONEY_WALLET, amount)

        await db.create_payment(user_id, amount, label)

        await message.answer(
            f"Для оплаты {amount} руб. <b>перейдите по ссылке.</b> После, <b>обязательно проверьте оплату.</b>",
            reply_markup=types.InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        types.InlineKeyboardButton(text="Оплатить", url=pay_url),
                        types.InlineKeyboardButton(
                            text="Проверить оплату", callback_data=f"check_pay_{label}"
                        ),
                    ]
                ]
            ),
        )
        await state.clear()

    except (ValueError, InvalidOperation) as e:
        await message.answer(
            "Ошибка! Введите корректное число (например: 100 или 250.50)"
        )
        print(e)


@router.callback_query(F.data.startswith("check_pay_"))
async def verify_payment_handler(callback: CallbackQuery, db: Database):
    payment_label = callback.data.replace("check_pay_", "")

    payment_record = await db.get_payment(payment_label)

    if not payment_record:
        await callback.answer("Платеж не найден.", show_alert=True)
        return

    if payment_record["is_paid"]:
        await callback.answer("Этот счет уже оплачен!", show_alert=True)
        return

    is_confirmed = await check_yoomoney_payment(YOOMONEY_TOKEN, payment_label)

    if is_confirmed:
        await db.set_payment_paid(payment_label)

        await db.add_money(
            payment_record["user_id"], payment_record["amount"], "Пополнение счета"
        )

        await callback.message.edit_text(
            f"✅ Оплата подтверждена! Зачислено {payment_record['amount']} руб."
        )
    else:
        await callback.answer(
            "Оплата пока не обнаружена. Попробуйте через минуту.", show_alert=True
        )


@router.message(Command("balance"))
async def show_balance(message: Message, db: Database):
    user = await db.get_user(message.from_user.id)
    if not user:
        await message.answer("Вы не зарегистрированы. Нажмите /start для регистрации")
        return

    balance = await db.get_balance(message.from_user.id)

    await message.answer(
        f"Ваш баланс: <b>{balance} руб.</b>\n Для пополнения используйте /top_up_balance"
    )
