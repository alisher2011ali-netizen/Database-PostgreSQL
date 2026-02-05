from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext

from database import Database
from states import *

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message, db: Database):
    user_id = message.from_user.id
    if not user_id:
        await message.answer(
            "Похоже что-то не так. Попробуйте запустить бота еще раз. /start"
        )
        return

    await db.register_user(user_id, message.from_user.username)
    user = await db.get_user(user_id)
    if not user:
        await message.answer(
            "Похоже что-то не так. Попробуйте запустить бота еще раз. /start"
        )
        return

    await message.answer(
        "Вы успешно зарегистрированы! Чтобы пополнить счет используйте /add_test_money"
    )


@router.message(Command("add_test_money"))
async def add_money_handler(message: Message, state: FSMContext, db: Database):
    user_id = message.from_user.id
    if not user_id:
        await message.answer(
            "Похоже что-то не так. Попробуйте запустить бота еще раз. /start"
        )
        return

    await message.answer("Введите сумму, на которую хотите пополнить баланс:")
    await state.set_state(AddMoney.waiting_for_amount)


@router.message(AddMoney.waiting_for_amount)
async def finish_adding_money(message: Message, state: FSMContext, db: Database):
    user_id = message.from_user.id
    amount = float(message.text)
    await db.add_money(user_id, amount, "Тестовое пополнение через команду")

    new_balance = await db.get_balance(user_id)

    await message.answer(f"✅ Баланс пополнен!\nТекущий баланс: 💰 {new_balance} руб.")

    await state.clear()
