from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from dotenv import load_dotenv
import os

load_dotenv()

ADMIN_ID = int(os.getenv("ADMIN_ID"))


def get_product_types_kb():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Игрушки"), KeyboardButton(text="Книги")],
            [KeyboardButton(text="Игры"), KeyboardButton(text="Электроника")],
        ],
        resize_keyboard=True,
    )


def get_confirm_buy_kb():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="✅ Подтвердить")],
            [KeyboardButton(text="❌ Отмена")],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def get_undo_to_products_kb():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🛒 К товарам", callback_data=f"page_0")],
            {InlineKeyboardButton(text="👤 В кабинет", callback_data="profile")},
        ]
    )


def get_undo_kb():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel")]
        ]
    )


def get_profile_kb(user_id: int):
    kb = [
        [InlineKeyboardButton(text="💳 Пополнить баланс", callback_data="top_up")],
        [
            InlineKeyboardButton(
                text="📜 История заказов", callback_data="order_history"
            )
        ],
        [
            InlineKeyboardButton(text="🔍 Найти заказ", callback_data="search_order"),
            InlineKeyboardButton(text="🔍 Найти товар", callback_data="search_product"),
        ],
    ]
    if user_id == ADMIN_ID:
        kb.append(
            [InlineKeyboardButton(text="💎 Админ-панель", callback_data="admin_main")]
        )
    return InlineKeyboardMarkup(inline_keyboard=kb)


def get_undo_to_admin_orders_list_kb():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="⬅️ Назад к списку заказов", callback_data="admin_main"
                )
            ]
        ]
    )


def get_customers_kb(product_id):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📜 Мои заказы", callback_data="order_history"
                ),
                InlineKeyboardButton(
                    text="🔍 О товаре", callback_data=f"prod_{product_id}_p0"
                ),
            ]
        ]
    )


def get_undo_to_profile_kb():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Назад", callback_data=f"profile")]
        ]
    )
