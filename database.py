import aiosqlite
from config import DB_PATH

async def init_db():
    # Ensure directory exists if DB_PATH is in a mounted folder
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                character_id TEXT NOT NULL DEFAULT 'asuka',
                custom_name TEXT,
                custom_prompt TEXT
            );
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                character_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_history_user_char 
            ON history(user_id, character_id);
        """)
        await db.commit()

async def get_user_state(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT character_id, custom_name, custom_prompt FROM users WHERE user_id = ?",
            (user_id,)
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                return {
                    "character_id": row[0],
                    "custom_name": row[1],
                    "custom_prompt": row[2]
                }
            # Create default user
            await db.execute(
                "INSERT INTO users (user_id, character_id) VALUES (?, 'asuka')",
                (user_id,)
            )
            await db.commit()
            return {
                "character_id": "asuka",
                "custom_name": None,
                "custom_prompt": None
            }

async def set_user_character(user_id: int, character_id: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO users (user_id, character_id) VALUES (?, ?)
            ON CONFLICT(user_id) DO UPDATE SET character_id = excluded.character_id
        """, (user_id, character_id))
        await db.commit()

async def set_custom_character(user_id: int, name: str, prompt: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO users (user_id, character_id, custom_name, custom_prompt)
            VALUES (?, 'custom', ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET 
                character_id = 'custom',
                custom_name = excluded.custom_name,
                custom_prompt = excluded.custom_prompt
        """, (user_id, name, prompt))
        await db.commit()

async def add_history_message(user_id: int, character_id: str, role: str, content: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO history (user_id, character_id, role, content) VALUES (?, ?, ?, ?)",
            (user_id, character_id, role, content)
        )
        await db.commit()

async def get_history(user_id: int, character_id: str, limit: int = 100):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("""
            SELECT role, content FROM (
                SELECT id, role, content FROM history
                WHERE user_id = ? AND character_id = ?
                ORDER BY id DESC
                LIMIT ?
            ) ORDER BY id ASC
        """, (user_id, character_id, limit)) as cursor:
            rows = await cursor.fetchall()
            return [{"role": row[0], "content": row[1]} for row in rows]

async def clear_character_history(user_id: int, character_id: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "DELETE FROM history WHERE user_id = ? AND character_id = ?",
            (user_id, character_id)
        )
        await db.commit()
