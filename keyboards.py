from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)


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
        keyboard=[[KeyboardButton(text="✅ Подтвердить")]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def get_undo_to_products_kb():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Назад", callback_data=f"page_0")]
        ]
    )


def get_undo_kb():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel")]
        ]
    )
