from aiogram.fsm.state import StatesGroup, State


class AddMoney(StatesGroup):
    waiting_for_amount = State()


class AddProduct(StatesGroup):
    waiting_for_type = State()
    waiting_for_name = State()
    waiting_for_description = State()
    waiting_for_price = State()
    waiting_for_stock = State()


class BuyProduct(StatesGroup):
    waiting_for_confirm = State()


class SearchOrder(StatesGroup):
    waiting_for_code = State()


class SearchProduct(StatesGroup):
    waiting_for_id = State()
