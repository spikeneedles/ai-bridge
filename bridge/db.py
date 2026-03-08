import aiosqlite
import json
from typing import Optional
from bridge.models import Message, Task
from bridge.config import DB_PATH


async def init_db():
    """Create tables if not exist."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id TEXT PRIMARY KEY,
                channel TEXT,
                sender TEXT,
                content TEXT,
                timestamp REAL,
                metadata TEXT
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id TEXT PRIMARY KEY,
                title TEXT,
                description TEXT,
                created_by TEXT,
                assigned_to TEXT,
                status TEXT,
                result TEXT,
                created_at REAL,
                updated_at REAL,
                priority INTEGER,
                tags TEXT
            )
        """)
        await db.execute("CREATE INDEX IF NOT EXISTS idx_messages_channel ON messages(channel)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_messages_timestamp ON messages(timestamp)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status)")
        await db.commit()


async def save_message(msg: Message) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR REPLACE INTO messages (id, channel, sender, content, timestamp, metadata) VALUES (?,?,?,?,?,?)",
            (msg.id, msg.channel, msg.sender, msg.content, msg.timestamp, json.dumps(msg.metadata))
        )
        await db.commit()


async def get_messages(channel: str = None, limit: int = 100) -> list[Message]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        if channel and channel != "all":
            cursor = await db.execute(
                "SELECT * FROM messages WHERE channel = ? ORDER BY timestamp DESC LIMIT ?",
                (channel, limit)
            )
        else:
            cursor = await db.execute(
                "SELECT * FROM messages ORDER BY timestamp DESC LIMIT ?",
                (limit,)
            )
        rows = await cursor.fetchall()
        return [
            Message(
                id=row["id"],
                channel=row["channel"],
                sender=row["sender"],
                content=row["content"],
                timestamp=row["timestamp"],
                metadata=json.loads(row["metadata"] or "{}")
            )
            for row in reversed(rows)
        ]


async def save_task(task: Task) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """INSERT OR REPLACE INTO tasks
               (id, title, description, created_by, assigned_to, status, result,
                created_at, updated_at, priority, tags)
               VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (
                task.id, task.title, task.description, task.created_by,
                task.assigned_to, task.status, task.result,
                task.created_at, task.updated_at, task.priority,
                json.dumps(task.tags)
            )
        )
        await db.commit()


async def update_task(task: Task) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """UPDATE tasks SET
               title=?, description=?, created_by=?, assigned_to=?, status=?,
               result=?, updated_at=?, priority=?, tags=?
               WHERE id=?""",
            (
                task.title, task.description, task.created_by, task.assigned_to,
                task.status, task.result, task.updated_at, task.priority,
                json.dumps(task.tags), task.id
            )
        )
        await db.commit()


async def get_tasks(status: str = None) -> list[Task]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        if status:
            cursor = await db.execute(
                "SELECT * FROM tasks WHERE status = ? ORDER BY priority DESC, created_at ASC",
                (status,)
            )
        else:
            cursor = await db.execute(
                "SELECT * FROM tasks ORDER BY priority DESC, created_at ASC"
            )
        rows = await cursor.fetchall()
        return [_row_to_task(row) for row in rows]


async def get_task(task_id: str) -> Optional[Task]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
        row = await cursor.fetchone()
        if row is None:
            return None
        return _row_to_task(row)


async def count_messages() -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT COUNT(*) FROM messages")
        row = await cursor.fetchone()
        return row[0] if row else 0


async def count_tasks() -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT COUNT(*) FROM tasks")
        row = await cursor.fetchone()
        return row[0] if row else 0


async def get_channels() -> list[str]:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT DISTINCT channel FROM messages ORDER BY channel")
        rows = await cursor.fetchall()
        return [row[0] for row in rows]


async def clear_all() -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM messages")
        await db.execute("DELETE FROM tasks")
        await db.commit()


def _row_to_task(row) -> Task:
    return Task(
        id=row["id"],
        title=row["title"],
        description=row["description"],
        created_by=row["created_by"],
        assigned_to=row["assigned_to"],
        status=row["status"],
        result=row["result"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        priority=row["priority"],
        tags=json.loads(row["tags"] or "[]")
    )
