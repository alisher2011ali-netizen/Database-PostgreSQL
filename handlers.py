from aiogram import Router, F, types
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardRemove,
)
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from dotenv import load_dotenv
import os
from decimal import Decimal, InvalidOperation

from database import Database
from states import *
from payment import *
from keyboards import *
from other import *

load_dotenv()

ADMIN_ID = int(os.getenv("ADMIN_ID"))
YOOMONEY_WALLET = os.getenv("YOOMONEY_WALLET")
YOOMONEY_TOKEN = os.getenv("YOOMONEY_TOKEN")
router = Router()


@router.callback_query(F.data == "cancel")
async def go_undo(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.answer("⬅️ Действие отменено")


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

    await message.answer(
        "Введите сумму, на которую хотите пополнить баланс:", reply_markup=get_undo_kb()
    )
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
        await message.answer("Введите корректное число (например: 100 или 250.50)")
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
        f"Ваш баланс: <b>{balance} руб.</b>\nДля пополнения используйте /top_up_balance"
    )


@router.message(Command("view_goods"))
@router.callback_query(F.data.startswith("page_"))
async def show_goods_page(event: Message | CallbackQuery, db: Database):
    if isinstance(event, Message):
        page = 0
    else:
        page = int(event.data.split("_")[1])

    limit = 5
    offset = page * limit
    products = await db.get_goods(limit, offset)

    builder = InlineKeyboardBuilder()

    for prod in products:
        builder.row(
            InlineKeyboardButton(
                text=f"{prod['name']} — {prod['price']} руб.",
                callback_data=f"prod_{prod['id']}_p{page}",
            )
        )

    nav_buttons = []
    if page > 0:
        nav_buttons.append(
            InlineKeyboardButton(text="⬅️", callback_data=f"page_{page-1}")
        )

    if len(products) == limit:
        nav_buttons.append(
            InlineKeyboardButton(text="➡️", callback_data=f"page_{page+1}")
        )

    if nav_buttons:
        builder.row(*nav_buttons)

    text = "<b>🛒 Наш ассортимент:</b>"

    if isinstance(event, Message):
        await event.answer(text, reply_markup=builder.as_markup())
    else:
        await event.message.edit_text(text, reply_markup=builder.as_markup())
        await event.answer()


@router.callback_query(F.data.startswith("prod_"))
async def show_product(callback: CallbackQuery, db: Database):
    data = callback.data.split("_")
    product_id = int(data[1])
    page_info = data[2] if len(data) > 2 else "p0"
    product = await db.get_product_by_id(product_id)

    if not product:
        await callback.answer("Товар не найден", show_alert=True)
        return

    in_stock = (
        f"✅ В наличии {product['stock']} шт."
        if product["stock"]
        else "🚫 Нет в наличии"
    )
    text = (
        f"<b>{product['name']}</b>\n"
        f"━━━━━━━━━━━━━━━\n"
        f"📦 <b>Категория:</b> {product['type']}\n"
        f"📝 <b>Описание:</b>\n"
        f"{product['description']}\n"
        f"💰 Цена: <b>{product['price']} руб.</b>\n"
        f"{in_stock}\n"
    )

    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="💳 Купить", callback_data=f"buy_{product['id']}")
    )
    builder.row(
        InlineKeyboardButton(text="⬅️ Назад", callback_data=f"page_{page_info[1:]}")
    )

    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await callback.answer()


@router.message(Command("add_product"))
async def adding_product(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        await message.answer("❌ Вы не можете добавлять товары!")
        return

    await message.answer(
        "Вы добавляете новый товар. Выберите категорию:",
        reply_markup=get_product_types_kb(),
    )
    await state.set_state(AddProduct.waiting_for_type)


@router.message(AddProduct.waiting_for_type)
async def type_added(message: Message, state: FSMContext):
    if not message.text:
        await message.answer(
            "Пожалуйста, выберите категорию либо напишите ее самостоятельно:"
        )
        return

    await state.update_data(type=message.text)
    await message.answer(
        "Теперь напишите название товара:", reply_markup=ReplyKeyboardRemove()
    )
    await state.set_state(AddProduct.waiting_for_name)


@router.message(AddProduct.waiting_for_name)
async def name_added(message: Message, state: FSMContext, db: Database):
    if not message.text:
        await message.answer("Пожалуйста, напишите название текстом:")
        return

    await state.update_data(name=message.text)
    await message.answer("Дайте описание своему товару (до 600 симв.):")
    await state.set_state(AddProduct.waiting_for_description)


@router.message(AddProduct.waiting_for_description)
async def description_added(message: Message, state: FSMContext):
    if not message.text:
        await message.answer("Пожалуйста, напишите описание текстом:")
        return
    if len(message.text) > 600:
        await message.answer(
            "Лимит символов превышен. Сократите длину до 600 символов:"
        )
        return

    await state.update_data(description=message.text)
    await message.answer("Выставьте стоимомть товара за шт:")
    await state.set_state(AddProduct.waiting_for_price)


@router.message(AddProduct.waiting_for_price)
async def price_added(message: Message, state: FSMContext):
    if not message.text:
        await message.answer("Пожалуйста, напишите цену цифрами:")
        return
    clean_text = message.text.replace(",", ".")

    try:
        price = Decimal(clean_text)

        if price <= 0:
            await message.answer("Цена должна быть больше нуля!")
            return

        await state.update_data(price=price)
        await message.answer("Напишите количество товара в наличии (шт):")
        await state.set_state(AddProduct.waiting_for_stock)

    except InvalidOperation:
        await message.answer("Ошибка! Введите число (например 99.90):")


@router.message(AddProduct.waiting_for_stock)
async def stock_added(message: Message, state: FSMContext, db: Database):
    if not message.text or not message.text.isdigit():
        await message.answer("Пожалуйста, напишите кол-во товаров цифрами:")
        return
    if int(message.text) < 0:
        await message.answer("Кол-во товаров не может быть меньше 0")
        return

    product = await state.get_data()
    await db.add_product(
        type=product["type"],
        name=product["name"],
        description=product["description"],
        price=product["price"],
        stock=int(message.text),
    )

    await message.answer("✅ Товар успешно добавлен.")
    await state.clear()


@router.callback_query(F.data.startswith("buy_"))
async def process_buying(callback: CallbackQuery, state: FSMContext, db: Database):
    prod_id = int(callback.data.replace("buy_", ""))
    product = await db.get_product_by_id(prod_id)

    if not product:
        await callback.answer("Товар не найден")
        return

    if not product["stock"] > 0:
        await callback.answer("Товар уже раскуплен")
        return

    await state.update_data(prod_id=prod_id, price=product["price"])
    await callback.message.answer(
        f"Вы хотите купить {product['name']} за {product['price']} руб?",
        reply_markup=get_confirm_buy_kb(),
    )
    await state.set_state(BuyProduct.waiting_for_confirm)


@router.message(BuyProduct.waiting_for_confirm)
async def buy_confirmed(message: Message, state: FSMContext, db: Database):
    if not message.text or not message.text == "✅ Подтвердить":
        await message.answer(
            "Покупка отменена. Нажмите <b>Купить</b> заново",
            reply_markup=ReplyKeyboardRemove(),
        )
        state.clear()
        return

    data = await state.get_data()
    status, order_code = await db.buy_product(
        message.from_user.id, data["prod_id"], data["price"]
    )

    try:
        if status == "low_balance":
            await message.answer(
                "❌ Недостаточно средств на балансе! Покупка отменена.\nДля пополнения используйте\n/top_up_balance",
                reply_markup=ReplyKeyboardRemove(),
            )
            await state.clear()
        elif status == "success":
            await message.answer(
                f"✅ Покупка прошла успешно!\n"
                f"Номер заказа: <code>{order_code}</code>\n"
                f"Сатус: Оплачен\n\n"
                f"По всем вопросам: @si_zin_pin1989",
                reply_markup=get_undo_to_products_kb(),
            )
        await state.clear()

    except Exception as e:
        if str(e) == "no_stock":
            await message.answer("📦 Товар закончился!", reply_markup=get_undo_kb())

        elif str(e) == "duplicate_code":
            await message.answer()
