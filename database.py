import asyncpg
from datetime import datetime
from dotenv import load_dotenv
import os

load_dotenv()

DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_NAME = os.getenv("DB_NAME")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")


class Database:
    def __init__(self):
        self.pool = None

    async def connect(self):
        try:
            self.pool = await asyncpg.create_pool(
                user=DB_USER,
                password=DB_PASSWORD,
                database=DB_NAME,
                host=DB_HOST,
                port=int(DB_PORT),
            )
            print("✅ База данных успешно подключена!")
        except Exception as e:
            print(f"❌ Ошибка подключения к БД: {e}")
            import sys

            sys.exit(1)

    async def _execute(self, query: str, *args):
        async with self.pool.acquire() as conn:
            return await conn.execute(query, *args)

    async def _fetchrow(self, query: str, *args):
        async with self.pool.acquire() as connection:
            return await connection.fetchrow(query, *args)

    async def _fetchval(self, query: str, *args):
        async with self.pool.acquire() as conn:
            return await conn.fetchval(query, *args)

    async def create_tables(self):
        query = """
        CREATE TABLE IF NOT EXISTS users (
            user_id BIGINT PRIMARY KEY,
            username TEXT,
            balance NUMERIC(12, 2) DEFAULT 0.00
        );

        CREATE TABLE IF NOT EXISTS transactions (
            id SERIAL PRIMARY KEY,
            user_id BIGINT REFERENCES users(user_id),
            amount NUMERIC(12, 2),
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS payments (
            id SERIAL PRIMARY KEY,
            user_id BIGINT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
            amount NUMERIC(12, 2),
            label TEXT UNIQUE,
            is_paid BOOLEAN DEFAULT FALSE
        );
        """
        await self._execute(query)

    async def register_user(self, user_id: int, username):
        query = """
        INSERT INTO users (user_id, username)
        VALUES ($1, $2)
        ON CONFLICT (user_id) DO NOTHING
        """
        await self._execute(query, user_id, username)

    async def get_user(self, user_id: int):
        query = """
        SELECT * FROM users WHERE user_id = $1"""
        return await self._fetchrow(query, user_id)

    async def get_balance(self, user_id: int):
        query = "SELECT balance FROM users WHERE user_id = $1"
        balance = await self._fetchval(query, user_id)
        return balance if balance is not None else 0

    async def create_payment(self, user_id: int, amount: float, label: str):
        """Создает запись о платеже в БД"""
        query = """
        INSERT INTO payments (user_id, amount, label)
        VALUES ($1, $2, $3)
        RETURNING id
        """
        return await self._fetchval(query, user_id, amount, label)

    async def get_payment(self, label: str):
        """Получает данные о платеже по его метке"""
        query = "SELECT * FROM payments WHERE label = $1;"
        return await self._fetchrow(query, label)

    async def set_payment_paid(self, label: str):
        """Помечает платеж как исполненный"""
        query = "UPDATE payments SET is_paid = TRUE WHERE label = $1;"
        await self._execute(query, label)

    async def get_unpaid_payments(self):
        """Возвращает список всех неоплаченных платежей"""
        query = "SELECT user_id, amount, label FROM payments WHERE is_paid = FALSE;"
        return await self._fetchrow(query)

    async def add_money(self, user_id: int, amount: float, description: str):
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                await conn.execute(
                    "UPDATE users SET balance = balance + $1 WHERE user_id = $2;",
                    amount,
                    user_id,
                )

                await conn.execute(
                    "INSERT INTO transactions (user_id, amount, description) VALUES ($1, $2, $3)",
                    user_id,
                    amount,
                    description,
                )
