"""
SQLite 数据库连接与初始化
"""
import aiosqlite
import os
from datetime import datetime
from typing import Optional
from contextlib import asynccontextmanager

DATABASE_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "users.db")

# 确保 data 目录存在
os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)


async def init_db():
    """初始化数据库表"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                google_id TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                name TEXT,
                avatar_url TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        # 确保 updated_at 字段存在（旧数据库可能没有）
        try:
            await db.execute("""
                ALTER TABLE users ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            """)
        except Exception:
            pass  # 字段已存在
        await db.commit()


async def get_db():
    """获取数据库连接（异步上下文管理器）"""
    db = await aiosqlite.connect(DATABASE_PATH)
    db.row_factory = aiosqlite.Row
    try:
        yield db
    finally:
        await db.close()


async def get_user_by_google_id(db: aiosqlite.Connection, google_id: str) -> Optional[dict]:
    """通过 Google ID 查询用户"""
    cursor = await db.execute(
        "SELECT * FROM users WHERE google_id = ?", (google_id,)
    )
    row = await cursor.fetchone()
    return dict(row) if row else None


async def get_user_by_email(db: aiosqlite.Connection, email: str) -> Optional[dict]:
    """通过邮箱查询用户"""
    cursor = await db.execute(
        "SELECT * FROM users WHERE email = ?", (email,)
    )
    row = await cursor.fetchone()
    return dict(row) if row else None


async def create_user(db: aiosqlite.Connection, google_id: str, email: str, name: str = None, avatar_url: str = None) -> dict:
    """创建新用户"""
    now = datetime.utcnow().isoformat()
    cursor = await db.execute(
        """INSERT INTO users (google_id, email, name, avatar_url, created_at, updated_at)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (google_id, email, name, avatar_url, now, now)
    )
    await db.commit()
    user_id = cursor.lastrowid
    return {
        "id": user_id,
        "google_id": google_id,
        "email": email,
        "name": name,
        "avatar_url": avatar_url,
        "created_at": now,
        "updated_at": now
    }


async def update_user(db: aiosqlite.Connection, user_id: int, name: str = None, avatar_url: str = None) -> Optional[dict]:
    """更新用户信息"""
    now = datetime.utcnow().isoformat()
    updates = []
    params = []
    if name is not None:
        updates.append("name = ?")
        params.append(name)
    if avatar_url is not None:
        updates.append("avatar_url = ?")
        params.append(avatar_url)
    updates.append("updated_at = ?")
    params.append(now)
    params.append(user_id)
    
    await db.execute(
        f"UPDATE users SET {', '.join(updates)} WHERE id = ?",
        params
    )
    await db.commit()
    
    cursor = await db.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    row = await cursor.fetchone()
    return dict(row) if row else None
