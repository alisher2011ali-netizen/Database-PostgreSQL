import asyncpg
from decimal import Decimal
from dotenv import load_dotenv
import os

from other import *

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

    async def _fetch(self, query: str, *args):
        async with self.pool.acquire() as conn:
            return await conn.fetch(query, *args)

    async def _fetchrow(self, query: str, *args):
        async with self.pool.acquire() as conn:
            return await conn.fetchrow(query, *args)

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
            created_at TIMESTAMP DEFAULT NOW()
        );
        CREATE TABLE IF NOT EXISTS payments (
            id SERIAL PRIMARY KEY,
            user_id BIGINT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
            amount NUMERIC(12, 2),
            label TEXT UNIQUE,
            is_paid BOOLEAN DEFAULT FALSE
        );
        CREATE TABLE IF NOT EXISTS goods (
            id SERIAL PRIMARY KEY,
            type TEXT,
            name TEXT UNIQUE,
            description TEXT,
            price NUMERIC(12, 2),
            stock INT DEFAULT 0 CHECK (stock >= 0)
        );
        CREATE TABLE IF NOT EXISTS orders (
            id SERIAL PRIMARY KEY,
            order_code TEXT UNIQUE NOT NULL,
            user_id BIGINT NOT NULL,
            product_id INT NOT NULL,
            price_at_purchase NUMERIC(12, 2) NOT NULL,
            status TEXT DEFAULT 'paid',
            created_at TIMESTAMP DEFAULT NOW(),
            completed_at TIMESTAMP,
            
            FOREIGN KEY (user_id) REFERENCES users(user_id),
            FOREIGN KEY (product_id) REFERENCES goods(id)
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

    async def create_payment(self, user_id: int, amount: Decimal, label: str):
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
        return await self._fetch(query)

    async def add_money(self, user_id: int, amount: Decimal, description: str):
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

    async def get_goods(self, limit: int, offset: int):
        query = "SELECT * FROM goods ORDER BY id LIMIT $1 OFFSET $2"
        return await self._fetch(query, limit, offset)

    async def add_product(
        self, type: str, name: str, description: str, price: Decimal, stock: int
    ):
        query = """
        INSERT INTO goods (type, name, description, price, stock)
        VALUES ($1, $2, $3, $4, $5)
        """
        await self._execute(query, type, name, description, price, stock)

    async def get_product_by_id(self, product_id: int):
        query = """
        SELECT * FROM goods WHERE id = $1
        """
        return await self._fetchrow(query, product_id)

    async def edit_product(
        self,
        product_id: int,
        type: str,
        name: str,
        description: str,
        price: Decimal,
        stock: int,
    ):
        query = """
        UPDATE goods SET type = $2, name = $3, description = $4, price = $5, stock = $6
        WHERE id = $1
        """
        await self._execute(query, product_id, type, name, description, price, stock)

    async def update_stock(self, product_id: int, stock: int):
        query = """
        UPDATE goods SET stock = $1 WHERE id = $2
        """
        await self._execute(query, stock, product_id)

    async def buy_product(self, user_id: int, product_id: int, price: Decimal):
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                user_update = await conn.execute(
                    "UPDATE users SET balance = balance - $1 WHERE user_id = $2 AND balance >= $1",
                    price,
                    user_id,
                )
                if user_update == "UPDATE 0":
                    return "low_balance", None

                stock_update = await conn.execute(
                    "UPDATE goods SET stock = stock - 1 WHERE id = $1 AND stock > 0",
                    product_id,
                )
                if stock_update == "UPDATE 0":
                    return "no_stock", None

                for _ in range(5):
                    new_code = generate_other_code()
                    try:
                        async with conn.transaction():
                            await conn.execute(
                                """INSERT INTO orders (order_code, user_id, product_id, price_at_purchase) 
                                   VALUES ($1, $2, $3, $4)""",
                                new_code,
                                user_id,
                                product_id,
                                price,
                            )
                        return "success", new_code
                    except asyncpg.UniqueViolationError:
                        continue

        raise Exception("could_not_generate_unique_code")

    async def get_order_by_id(self, order_id: int):
        query = "SELECT * FROM orders WHERE id = $1"
        return await self._fetchrow(query, order_id)

    async def get_order_by_code(self, order_code: str):
        query = """
        SELECT * FROM orders o
        JOIN goods g ON o.product_id = g.id
        WHERE o.order_code = $1
        """
        return await self._fetchrow(query, order_code)

    async def get_orders_by_user_id(self, user_id: int):
        query = """
        SELECT
            o.order_code,
            o.price_at_purchase,
            o.status,
            o.created_at,
            g.name as product_name
        FROM orders o
        JOIN goods g ON o.product_id = g.id
        WHERE o.user_id = $1
        ORDER BY o.created_at DESC
        """
        return await self._fetch(query, user_id)

    async def update_order_status(
        self, new_status: str, *, order_id: int = None, order_code: str = None
    ):
        set_clause = "status = $1"
        if new_status == "completed":
            set_clause += ", completed_at = NOW()"

        if order_id is not None:
            query = f"UPDATE orders SET {set_clause} WHERE id = $2"
            params = (new_status, order_id)
        elif order_code is not None:
            query = f"UPDATE orders SET {set_clause} WHERE order_code = $2"
            params = (new_status, order_code)
        else:
            raise ValueError("Нужно указать либо order_id, либо order_code")

        return await self._execute(query, *params)

    async def get_active_orders(self):
        query = """
        SELECT o.id, o.order_code, g.name, o.status 
        FROM orders o 
        JOIN goods g ON o.product_id = g.id 
        WHERE o.status != 'completed' 
        ORDER BY o.created_at DESC
        """
        return await self._fetch(query)

    async def get_last_order(self, user_id):
        query = """
        SELECT
            o.order_code, o.status, o.created_at, o.completed_at, g.name AS product_name
        FROM orders o
        JOIN goods g ON o.product_id = g.id
        WHERE o.user_id = $1
        ORDER BY created_at DESC
        LIMIT 1
        """
        return await self._fetchrow(query, user_id)
