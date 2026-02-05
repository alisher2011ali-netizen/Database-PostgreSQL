import asyncpg
from dotenv import load_dotenv
import os

load_dotenv()

PASSWORD = os.getenv("PASSWORD")


class Database:
    def __init__(self):
        self.pool = None

    async def connect(self):
        try:
            self.pool = await asyncpg.create_pool(
                user="postgres",
                password=PASSWORD,
                database="my_bot_db",
                host="172.30.112.1",
            )
            print("✅ База данных успешно подключена!")
        except Exception as e:
            print(f"❌ Ошибка подключения к БД: {e}")

    async def _execute(self, query: str, *args):
        async with self.pool.acquire() as conn:
            return await conn.execute(query, *args)

    async def _fetchrow(self, query: str, *args):
        async with self.pool.acquire() as connection:
            return await connection.fetchrow(query, *args)

    async def _fetchval(self, query, *args):
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

    async def add_money(self, user_id, amount, description):
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
