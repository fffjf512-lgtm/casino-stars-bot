import aiosqlite
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "casino.db")


async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                balance INTEGER DEFAULT 0,
                total_won INTEGER DEFAULT 0,
                total_lost INTEGER DEFAULT 0,
                games_played INTEGER DEFAULT 0
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                type TEXT,
                amount INTEGER,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """)
        await db.commit()


async def get_user(user_id: int, username: str = None):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        row = await cursor.fetchone()
        if row is None:
            await db.execute(
                "INSERT INTO users (user_id, username, balance) VALUES (?, ?, 0)",
                (user_id, username)
            )
            await db.commit()
            return {"user_id": user_id, "username": username, "balance": 0,
                    "total_won": 0, "total_lost": 0, "games_played": 0}
        return {"user_id": row[0], "username": row[1], "balance": row[2],
                "total_won": row[3], "total_lost": row[4], "games_played": row[5]}


async def update_balance(user_id: int, amount: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET balance = balance + ? WHERE user_id = ?",
            (amount, user_id)
        )
        await db.commit()


async def add_transaction(user_id: int, tx_type: str, amount: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO transactions (user_id, type, amount) VALUES (?, ?, ?)",
            (user_id, tx_type, amount)
        )
        await db.commit()


async def update_stats(user_id: int, won: int, lost: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """UPDATE users SET 
                total_won = total_won + ?, 
                total_lost = total_lost + ?,
                games_played = games_played + 1
            WHERE user_id = ?""",
            (won, lost, user_id)
        )
        await db.commit()


async def get_balance(user_id: int) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
        row = await cursor.fetchone()
        return row[0] if row else 0


async def get_leaderboard():
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT username, balance FROM users ORDER BY balance DESC LIMIT 10"
        )
        return await cursor.fetchall()
