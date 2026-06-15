"""Encrypted persistent storage for user Exchange credentials and session state."""
import aiosqlite
import json
from cryptography.fernet import Fernet
from config import DB_PATH, ENCRYPTION_KEY

_fernet = Fernet(ENCRYPTION_KEY)


async def init_db() -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS user_sessions (
                telegram_id INTEGER PRIMARY KEY,
                username    TEXT NOT NULL,
                enc_password BLOB NOT NULL,
                state       TEXT DEFAULT 'authenticated',
                created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS user_state (
                telegram_id INTEGER PRIMARY KEY,
                state_data  TEXT NOT NULL DEFAULT '{}'
            )
        """)
        await db.commit()


async def save_credentials(telegram_id: int, username: str, password: str) -> None:
    enc_password = _fernet.encrypt(password.encode())
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO user_sessions (telegram_id, username, enc_password)
            VALUES (?, ?, ?)
            ON CONFLICT(telegram_id) DO UPDATE SET
                username=excluded.username,
                enc_password=excluded.enc_password,
                updated_at=CURRENT_TIMESTAMP
        """, (telegram_id, username, enc_password))
        await db.commit()


async def get_credentials(telegram_id: int) -> tuple[str, str] | None:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT username, enc_password FROM user_sessions WHERE telegram_id = ?",
            (telegram_id,)
        ) as cursor:
            row = await cursor.fetchone()
    if row is None:
        return None
    username, enc_password = row
    password = _fernet.decrypt(enc_password).decode()
    return username, password


async def delete_credentials(telegram_id: int) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM user_sessions WHERE telegram_id = ?", (telegram_id,))
        await db.execute("DELETE FROM user_state WHERE telegram_id = ?", (telegram_id,))
        await db.commit()


async def is_authenticated(telegram_id: int) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT 1 FROM user_sessions WHERE telegram_id = ?", (telegram_id,)
        ) as cursor:
            return await cursor.fetchone() is not None


async def set_user_state(telegram_id: int, data: dict) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO user_state (telegram_id, state_data)
            VALUES (?, ?)
            ON CONFLICT(telegram_id) DO UPDATE SET state_data=excluded.state_data
        """, (telegram_id, json.dumps(data, ensure_ascii=False)))
        await db.commit()


async def get_user_state(telegram_id: int) -> dict:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT state_data FROM user_state WHERE telegram_id = ?", (telegram_id,)
        ) as cursor:
            row = await cursor.fetchone()
    return json.loads(row[0]) if row else {}
