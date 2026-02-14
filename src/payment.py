import uuid
from yoomoney import Quickpay, Client
import asyncio


def create_yoomoney_link(receiver: str, amount: float):
    """
    Генерирует уникальный label и ссылку на оплату.
    :param receiver: Номер кошелька ЮMoney (не токен!)
    :param amount: Сумма оплаты
    :return: кортеж (link, label)
    """
    label = str(uuid.uuid4())

    quickpay = Quickpay(
        receiver=receiver,
        quickpay_form="shop",
        targets="Пополнение баланса в боте",
        paymentType="SB",
        sum=amount,
        label=label,
    )
    return quickpay.base_url, label


def _check_payment_sync(token: str, label: str):
    """Проверяет, поступил ли платеж с конкретным label"""
    try:
        client = Client(token)
        history = client.operation_history(label=label, records=3)
        for operation in history.operations:
            if operation.status == "success":
                return True
    except Exception as e:
        print(f"Ошибка при запросе к ЮMoney: {e}")
    return False


async def check_yoomoney_payment(token: str, label: str):
    return await asyncio.to_thread(_check_payment_sync, token, label)
