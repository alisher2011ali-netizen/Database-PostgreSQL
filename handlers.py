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
import datetime

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
        "Вы успешно зарегистрированы! Чтобы пополнить счет используйте /deposit"
    )


@router.message(Command("deposit"))
@router.callback_query(F.data == "top_up")
async def add_money_handler(event: Message | CallbackQuery, state: FSMContext):
    if isinstance(event, Message):
        await event.answer(
            "Введите сумму в рублях (RUB), на которую хотите пополнить баланс:",
            reply_markup=get_undo_kb(),
        )
    else:
        await event.message.answer(
            "Введите сумму рублях (RUB), на которую хотите пополнить баланс:",
            reply_markup=get_undo_kb(),
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
            f"Для оплаты {amount} руб. <b>перейдите по ссылке.</b> После, <b>проверьте оплату.</b>",
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
        f"🆔 <code>100{product['id']}</code>"
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
        await state.clear()
        return

    data = await state.get_data()
    status, order_code = await db.buy_product(
        message.from_user.id, data["prod_id"], data["price"]
    )

    try:
        if status == "low_balance":
            await message.answer(
                "❌ Недостаточно средств на балансе! Покупка отменена.\nДля пополнения используйте\n/deposit",
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


@router.message(Command("profile"))
@router.callback_query(F.data == "profile")
async def show_profile(event: Message | CallbackQuery, state: FSMContext, db: Database):
    await state.clear()
    user_id = event.from_user.id
    user = await db.get_user(user_id)
    last_order = await db.get_last_order(user_id)

    if not user:
        if isinstance(event, Message):
            await event.answer("Вы не зарегистрированы! Нажмите /start для регистрации")
        else:
            await event.message.answer(
                "Вы не зарегистрированы! Нажмите /start для регистрации"
            )
        return

    text = (
        f"👤 <b>Личный кабинет</b>\n"
        f"🆔 ID: <code>{user['user_id']}</code>\n"
        f"💰 Баланс: <b>{user['balance']} руб.</b>\n"
        f"────────────────────\n"
    )

    if last_order:
        status_key = last_order["status"]
        status_text = STATUS_TRANSLATIONS.get(status_key, status_key)

        created_date = last_order["created_at"].strftime("%d.%m.%Y")

        text += (
            f"📦 <b>Последний заказ:</b>\n"
            f"🏷 Товар: {last_order['product_name']}\n"
            f"🔢 Код: <code>{last_order['order_code']}</code>\n"
            f"📊 Статус: {status_text}\n"
        )
        if status_key == "completed" and last_order.get("completed_at"):
            comp_date = last_order["completed_at"].strftime("%d.%m.%Y в %H:%M")
            text += f"🏁 <b>Получен:</b> {comp_date}\n"
        else:
            text += f"📅 <b>Заказан:</b> {created_date}\n"

    else:
        text += "📦 У вас пока нет заказов.\n"

    if isinstance(event, Message):
        await event.answer(
            text,
            reply_markup=get_profile_kb(user_id),
        )
    else:
        await event.message.answer(
            text,
            reply_markup=get_profile_kb(user_id),
        )


@router.callback_query(F.data == "order_history")
async def show_order_history(callback: CallbackQuery, db: Database):
    orders = await db.get_orders_by_user_id(callback.from_user.id)

    if not orders:
        text = "📜 У вас пока нет заказов."
    else:
        text = "<b>🗄 Ваша история заказов:</b>\n\n"
        for order in orders:
            date_str = order["created_at"].strftime("%d.%m.%Y %H:%M")
            if order["status"] == "completed" and order.get("completed_at"):
                date_str = order["completed_at"].strftime("%d.%m.%Y %H:%M")

            raw_status = order["status"]
            status_text = STATUS_TRANSLATIONS.get(raw_status, raw_status)

            text += (
                f"📦 <b>{order['product_name']}</b>\n"
                f"├ Код: <code>{order['order_code']}</code>\n"
                f"├ Статус: {status_text}\n"
                f"└ Дата: {date_str}\n\n"
            )

    await callback.message.answer(text)
    callback.answer()


@router.callback_query(F.data == "admin_main")
async def admin_orders_list(callback: CallbackQuery, db: Database):
    orders = await db.get_active_orders()

    if not orders:
        return await callback.message.edit_text("📭 Новых заказов пока нет.")

    builder = InlineKeyboardBuilder()

    text = "🔍 <b>Активные заказы:</b>\n"
    for order in orders:
        status = STATUS_TRANSLATIONS.get(order["status"], order["status"])
        text += f"\n🆔 {order['id']} | <code>{order['order_code']}</code> | {order['name']}\nСтатус: <b>{status}</b>\n"
        builder.button(
            text=f"⚙️ Статус #{order['id']}",
            callback_data=f"edit_st:{order['id']}:{order['status']}",
        )

    builder.adjust(1)
    await callback.message.edit_text(text, reply_markup=builder.as_markup())


@router.callback_query(F.data.startswith("edit_st:"))
async def process_edit_status(callback: CallbackQuery):
    data = callback.data.split(":")

    order_id = int(data[1])
    raw_status = data[2]
    status = STATUS_TRANSLATIONS.get(raw_status, raw_status)

    kb = InlineKeyboardBuilder()
    for status_key, status_name in STATUS_TRANSLATIONS.items():
        kb.button(text=status_name, callback_data=f"save_st:{order_id}:{status_key}")
    kb.adjust(2)

    kb.row(InlineKeyboardButton(text="❌ Отмена", callback_data="admin_main"))

    await callback.message.edit_text(
        f"Текущий статус заказа №{order_id}:\n<b>{status}</b>\nВыберите новый статус:",
        reply_markup=kb.as_markup(),
    )


@router.callback_query(F.data.startswith("save_st:"))
async def save_new_order_status(callback: CallbackQuery, db: Database):
    data = callback.data.split(":")

    order_id = int(data[1])
    status_key = data[2]

    order = await db.get_order_by_id(order_id)

    if not order:
        await callback.answer("Заказ не найден!", show_alert=True)
        return

    buyer_id = order["user_id"]
    order_code = order["order_code"]
    product_id = order["product_id"]

    await db.update_order_status(status_key, order_id=order_id)

    status_text = STATUS_TRANSLATIONS.get(status_key, status_key)
    text = f"✅ Статус заказа №{order_id} успешно изменен на «{status_text}»"

    try:
        await callback.bot.send_message(
            chat_id=buyer_id,
            text=(
                f"🔔 <b>Статус вашего заказа обновлен!</b>\n\n"
                f"📦 Заказ: <code>{order_code}</code>\n"
                f"🔄 Новый статус: <b>{status_text}</b>"
            ),
            reply_markup=get_customers_kb(product_id=product_id),
        )
        text += ".\nКлиент получил уведомление."
    except Exception as e:
        print(f"Не удалось отправить уведомление пользователю {buyer_id}: {e}")

    await callback.message.answer(
        text,
        reply_markup=get_undo_to_admin_orders_list_kb(),
    )
    await callback.answer()


@router.callback_query(F.data == "search_order")
async def process_search_order(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("Введите номер вашего заказа:")
    await state.set_state(SearchOrder.waiting_for_code)


@router.message(SearchOrder.waiting_for_code)
async def result_search_order(message: Message, db: Database):
    if not message.text:
        await message.answer("Пожалуйста, введите номер заказа текстом:")
        return

    order = await db.get_order_by_code(message.text)

    if not order:
        await message.answer(
            "Заказа с таким кодом не существует. Попробуйте снова, или вернитесь назад.",
            reply_markup=get_undo_to_profile_kb(),
        )
        return
    status_key = order["status"]
    status_text = STATUS_TRANSLATIONS.get(status_key, status_key)

    created_date = order["created_at"].strftime("%d.%m.%Y")

    text = (
        f"Найденный заказ:\n"
        f"📦 <b>{order['name']}</b>\n"
        f"🔢 Код: <code>{order['order_code']}</code>\n"
        f"📊 Статус: {status_text}\n"
    )
    if status_key == "completed" and order.get("completed_at"):
        comp_date = order["completed_at"].strftime("%d.%m.%Y в %H:%M")
        text += f"🏁 <b>Получен:</b> {comp_date}\n"
    else:
        text += f"📅 <b>Заказан:</b> {created_date}\n"

    in_stock = (
        f"✅ В наличии {order['stock']} шт." if order["stock"] else "🚫 Нет в наличии"
    )
    text += (
        f"<b>🔍 О товаре:</b>\n"
        f"━━━━━━━━━━━━━━━\n"
        f"📦 <b>Категория:</b> {order['type']}\n"
        f"📝 <b>Описание:</b>\n"
        f"{order['description']}\n"
        f"💰 Цена: <b>{order['price']} руб.</b>\n"
        f"{in_stock}\n"
    )

    text += "Можете ввести код, для поиска другого заказа:"

    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="💳 Купить еще", callback_data=f"buy_{order['product_id']}"
        )
    )
    builder.row(InlineKeyboardButton(text="⬅️ Назад", callback_data=f"profile"))

    await message.answer(text, reply_markup=builder.as_markup())


@router.callback_query(F.data == "search_product")
async def process_search_product(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("Пожалуйста, введите ID товара:")
    await state.set_state(SearchProduct.waiting_for_id)


@router.message(SearchProduct.waiting_for_id)
async def result_search_product(message: Message, db: Database):
    if not message.text:
        await message.answer("Пожалуйста, введите номер заказа текстом:")
        return

    product_id = int(message.text.replace("100", ""))

    product = await db.get_product_by_id(product_id)

    if not product:
        await message.answer(
            "Заказа с таким кодом не существует. Попробуйте снова, или вернитесь назад.",
            reply_markup=get_undo_to_profile_kb(),
        )
        return

    in_stock = (
        f"✅ В наличии {product['stock']} шт."
        if product["stock"]
        else "🚫 Нет в наличии"
    )

    text = (
        f"<b> Найденный товар:</b>\n"
        f"━━━━━━━━━━━━━━━\n"
        f"📦 <b>Категория:</b> {product['type']}\n"
        f"📝 <b>Описание:</b>\n"
        f"{product['description']}\n"
        f"💰 Цена: <b>{product['price']} руб.</b>\n"
        f"{in_stock}\n"
        f"🆔 <code>100{product['id']}</code>"
    )

    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="💳 Купить еще", callback_data=f"buy_{product['id']}")
    )
    builder.row(InlineKeyboardButton(text="⬅️ Назад", callback_data=f"profile"))

    await message.answer(text, reply_markup=builder.as_markup())
