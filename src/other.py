import secrets
import string

STATUS_TRANSLATIONS = {
    "paid": "✅ Оплачен",
    "packing": "📦 Собирается",
    "shipping": "🚚 В пути",
    "delivered": "🏢 Доставлен",
    "completed": "🏁 Получен",
    "refunded": "🔄 Возврат",
}


def generate_other_code(length=8):
    characters = string.ascii_uppercase + string.digits
    return "".join(secrets.choice(characters) for _ in range(length))
