from aiogram.fsm.state import StatesGroup, State


class AddMoney(StatesGroup):
    waiting_for_amount = State()
