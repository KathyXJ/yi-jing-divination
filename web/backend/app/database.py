"""
SQLite 数据库连接与初始化
"""
import aiosqlite
import os
from datetime import datetime, timedelta
from typing import Optional
from contextlib import asynccontextmanager

DATABASE_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "users.db")

# 确保 data 目录存在
os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)


async def init_db():
    """初始化数据库表"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        # 启用 WAL 模式确保写入持久化
        await db.execute("PRAGMA journal_mode=WAL")
        await db.execute("PRAGMA synchronous=NORMAL")
        await db.execute("""

            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                google_id TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                name TEXT,
                avatar_url TEXT,
                credits INTEGER DEFAULT 0,
                welcome_bonus_credits INTEGER DEFAULT 0,
                welcome_bonus_expires_at TIMESTAMP DEFAULT NULL,
                monthly_subscription_credits INTEGER DEFAULT 0,
                monthly_subscription_expires_at TIMESTAMP DEFAULT NULL,
                standard_pack_credits INTEGER DEFAULT 0,
                has_permanent_credits INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 确保新增字段存在（旧数据库可能没有）
        for col, col_type in [
            ("credits", "INTEGER DEFAULT 0"),
            ("welcome_bonus_credits", "INTEGER DEFAULT 0"),
            ("welcome_bonus_expires_at", "TIMESTAMP DEFAULT NULL"),
            ("monthly_subscription_credits", "INTEGER DEFAULT 0"),
            ("monthly_subscription_expires_at", "TIMESTAMP DEFAULT NULL"),
            ("standard_pack_credits", "INTEGER DEFAULT 0"),
            ("has_permanent_credits", "INTEGER DEFAULT 0"),
        ]:
            try:
                await db.execute(f"ALTER TABLE users ADD COLUMN {col} {col_type}")
            except Exception:
                pass

        # 积分变动流水表
        await db.execute("""
            CREATE TABLE IF NOT EXISTS credits_transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                type TEXT NOT NULL,
                amount INTEGER NOT NULL,
                balance_after INTEGER NOT NULL,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)

        # 产品/套餐表
        await db.execute("""
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                name_en TEXT NOT NULL,
                credits INTEGER NOT NULL,
                price_cents INTEGER NOT NULL,
                type TEXT NOT NULL,
                valid_days INTEGER DEFAULT NULL,
                description TEXT,
                description_en TEXT,
                is_active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 订单表
        await db.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                product_id INTEGER NOT NULL,
                amount_cents INTEGER NOT NULL,
                currency TEXT DEFAULT 'USD',
                status TEXT DEFAULT 'pending',
                payment_provider TEXT DEFAULT NULL,
                provider_transaction_id TEXT DEFAULT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id),
                FOREIGN KEY (product_id) REFERENCES products(id)
            )
        """)

        await db.commit()

        # 数据库迁移：确保新列存在（旧数据库 schema 升级）
        try:
            await db.execute("ALTER TABLE products ADD COLUMN valid_days INTEGER DEFAULT NULL")
        except Exception:
            pass  # 列已存在
        try:
            await db.execute("ALTER TABLE products ADD COLUMN is_active INTEGER DEFAULT 1")
        except Exception:
            pass  # 列已存在
        await db.commit()

        # 初始化产品数据
        await init_products(db)


async def init_products(db: aiosqlite.Connection):
    """初始化定价产品"""
    products = [
        {
            "name": "注册赠送",
            "name_en": "Welcome Bonus",
            "credits": 3,
            "price_cents": 0,
            "type": "free",
            "valid_days": 7,
            "description": "新用户注册赠送3积分，7天内有效",
            "description_en": "New users get 3 free credits, valid for 7 days",
        },
        {
            "name": "标准积分包",
            "name_en": "Standard Pack",
            "credits": 50,
            "price_cents": 990,
            "type": "one_time",
            "valid_days": None,
            "description": "50积分，永久有效",
            "description_en": "50 credits, forever valid",
        },
        {
            "name": "月度订阅",
            "name_en": "Monthly Subscription",
            "credits": 200,
            "price_cents": 1990,
            "type": "subscription",
            "valid_days": 30,
            "description": "200积分/月，按月续费",
            "description_en": "200 credits/month, auto-renewal",
        },
    ]

    for p in products:
        cursor = await db.execute(
            "SELECT id FROM products WHERE name = ?", (p["name"],)
        )
        row = await cursor.fetchone()
        if not row:
            await db.execute("""
                INSERT INTO products (name, name_en, credits, price_cents, type, valid_days, description, description_en)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (p["name"], p["name_en"], p["credits"], p["price_cents"], p["type"], p["valid_days"], p["description"], p["description_en"]))

    await db.commit()


@asynccontextmanager
async def get_db():
    """获取数据库连接（异步上下文管理器）"""
    db = await aiosqlite.connect(DATABASE_PATH)
    db.row_factory = aiosqlite.Row
    # 启用 WAL 模式确保写入持久化
    await db.execute("PRAGMA journal_mode=WAL")
    await db.execute("PRAGMA synchronous=NORMAL")
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


async def get_user_by_id(db: aiosqlite.Connection, user_id: int) -> Optional[dict]:
    """通过 ID 查询用户"""
    cursor = await db.execute(
        "SELECT * FROM users WHERE id = ?", (user_id,)
    )
    row = await cursor.fetchone()
    return dict(row) if row else None


async def create_user(db: aiosqlite.Connection, google_id: str, email: str, name: str = None, avatar_url: str = None) -> dict:
    """创建新用户（带注册赠送3积分，7天有效）"""
    from datetime import timedelta
    now = datetime.utcnow().isoformat()
    welcome_bonus_expires = (datetime.utcnow() + timedelta(days=7)).isoformat()
    
    cursor = await db.execute(
        """INSERT INTO users (google_id, email, name, avatar_url, credits, 
           welcome_bonus_credits, welcome_bonus_expires_at, 
           monthly_subscription_credits, monthly_subscription_expires_at,
           standard_pack_credits, has_permanent_credits,
           created_at, updated_at)
           VALUES (?, ?, ?, ?, 3, 3, ?, 0, NULL, 0, 0, ?, ?)""",
        (google_id, email, name, avatar_url, welcome_bonus_expires, now, now)
    )
    await db.commit()
    user_id = cursor.lastrowid
    return {
        "id": user_id,
        "google_id": google_id,
        "email": email,
        "name": name,
        "avatar_url": avatar_url,
        "credits": 3,
        "welcome_bonus_credits": 3,
        "welcome_bonus_expires_at": welcome_bonus_expires,
        "monthly_subscription_credits": 0,
        "monthly_subscription_expires_at": None,
        "standard_pack_credits": 0,
        "has_permanent_credits": 0,
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


async def update_user_credits(db: aiosqlite.Connection, user_id: int, new_credits: int) -> None:
    """更新用户积分余额（替换为新值）"""
    now = datetime.utcnow().isoformat()
    await db.execute(
        "UPDATE users SET credits = ?, updated_at = ? WHERE id = ?",
        (new_credits, now, user_id)
    )
    await db.commit()


async def update_user_subscription(
    db: aiosqlite.Connection,
    user_id: int,
    subscription_type: str,
    expires_at: str
) -> None:
    """更新用户订阅状态"""
    now = datetime.utcnow().isoformat()
    await db.execute(
        "UPDATE users SET subscription_type = ?, subscription_expires_at = ?, updated_at = ? WHERE id = ?",
        (subscription_type, expires_at, now, user_id)
    )
    await db.commit()


async def activate_permanent_credits(db: aiosqlite.Connection, user_id: int) -> None:
    """激活永久积分标志"""
    now = datetime.utcnow().isoformat()
    await db.execute(
        "UPDATE users SET has_permanent_credits = 1, updated_at = ? WHERE id = ?",
        (now, user_id)
    )
    await db.commit()


async def add_standard_pack_credits(db: aiosqlite.Connection, user_id: int, amount: int) -> int:
    """添加标准积分包积分（永久有效）"""
    now = datetime.utcnow().isoformat()
    await db.execute(
        "UPDATE users SET standard_pack_credits = standard_pack_credits + ?, has_permanent_credits = 1, updated_at = ? WHERE id = ?",
        (amount, now, user_id)
    )
    await db.commit()
    # 重新计算总积分
    cursor = await db.execute("SELECT welcome_bonus_credits + monthly_subscription_credits + standard_pack_credits as total FROM users WHERE id = ?", (user_id,))
    row = await cursor.fetchone()
    total = row["total"] if row else amount
    await db.execute("UPDATE users SET credits = ? WHERE id = ?", (total, user_id))
    await db.commit()
    return total


async def add_monthly_subscription_credits(db: aiosqlite.Connection, user_id: int, amount: int, expires_at: str) -> int:
    """添加月度订阅积分"""
    now = datetime.utcnow().isoformat()
    await db.execute(
        "UPDATE users SET monthly_subscription_credits = ?, monthly_subscription_expires_at = ?, updated_at = ? WHERE id = ?",
        (amount, expires_at, now, user_id)
    )
    await db.commit()
    # 重新计算总积分
    cursor = await db.execute("SELECT welcome_bonus_credits + monthly_subscription_credits + standard_pack_credits as total FROM users WHERE id = ?", (user_id,))
    row = await cursor.fetchone()
    total = row["total"] if row else amount
    await db.execute("UPDATE users SET credits = ? WHERE id = ?", (total, user_id))
    await db.commit()
    return total


async def deduct_credits_by_priority(db: aiosqlite.Connection, user_id: int, amount: int) -> dict:
    """
    按优先级扣除积分：Welcome Bonus -> Monthly Subscription -> Standard Pack
    返回扣除结果和剩余各类型积分
    """
    now = datetime.utcnow().isoformat()
    
    # 获取用户当前积分状态
    cursor = await db.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    user = dict(await cursor.fetchone())
    
    welcome = user.get("welcome_bonus_credits", 0)
    monthly = user.get("monthly_subscription_credits", 0)
    standard = user.get("standard_pack_credits", 0)
    
    # 检查并处理 welcome bonus 过期
    welcome_expires = user.get("welcome_bonus_expires_at")
    if welcome_expires and datetime.fromisoformat(welcome_expires) < datetime.utcnow():
        # welcome bonus 过期，余额转入 standard pack
        if welcome > 0:
            standard += welcome
            await db.execute(
                "UPDATE users SET standard_pack_credits = ?, welcome_bonus_credits = 0, welcome_bonus_expires_at = NULL WHERE id = ?",
                (standard, user_id)
            )
            welcome = 0
    
    remaining = amount
    deducted_from = []
    
    # 1. 先扣 Welcome Bonus
    if remaining > 0 and welcome > 0:
        deduct = min(welcome, remaining)
        welcome -= deduct
        remaining -= deduct
        deducted_from.append(("welcome_bonus", deduct))
        await db.execute(
            "UPDATE users SET welcome_bonus_credits = ? WHERE id = ?",
            (welcome, user_id)
        )
    
    # 2. 再扣 Monthly Subscription
    if remaining > 0 and monthly > 0:
        deduct = min(monthly, remaining)
        monthly -= deduct
        remaining -= deduct
        deducted_from.append(("monthly_subscription", deduct))
        await db.execute(
            "UPDATE users SET monthly_subscription_credits = ? WHERE id = ?",
            (monthly, user_id)
        )
    
    # 3. 最后扣 Standard Pack
    if remaining > 0 and standard > 0:
        deduct = min(standard, remaining)
        standard -= deduct
        remaining -= deduct
        deducted_from.append(("standard_pack", deduct))
        await db.execute(
            "UPDATE users SET standard_pack_credits = ? WHERE id = ?",
            (standard, user_id)
        )
    
    # 更新总积分
    total = welcome + monthly + standard
    await db.execute("UPDATE users SET credits = ?, updated_at = ? WHERE id = ?", (total, now, user_id))
    await db.commit()
    
    return {
        "success": remaining == 0,  # 如果还有剩余说明积分不足
        "total_remaining": total,
        "welcome_remaining": welcome,
        "monthly_remaining": monthly,
        "standard_remaining": standard,
        "deducted_from": deducted_from
    }


async def add_credits_transaction(
    db: aiosqlite.Connection,
    user_id: int,
    tx_type: str,
    amount: int,
    balance_after: int,
    description: str = None
) -> int:
    """记录积分变动流水，返回事务ID"""
    now = datetime.utcnow().isoformat()
    cursor = await db.execute("""
        INSERT INTO credits_transactions (user_id, type, amount, balance_after, description, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (user_id, tx_type, amount, balance_after, description, now))
    await db.commit()
    return cursor.lastrowid


async def get_user_transactions(db: aiosqlite.Connection, user_id: int, limit: int = 20) -> list:
    """获取用户积分流水记录"""
    cursor = await db.execute(
        "SELECT * FROM credits_transactions WHERE user_id = ? ORDER BY created_at DESC LIMIT ?",
        (user_id, limit)
    )
    rows = await cursor.fetchall()
    return [dict(row) for row in rows]


async def get_product_by_id(db: aiosqlite.Connection, product_id: int) -> Optional[dict]:
    """通过产品ID查询产品"""
    try:
        cursor = await db.execute(
            "SELECT * FROM products WHERE id = ? AND is_active = 1", (product_id,)
        )
    except Exception:
        cursor = await db.execute(
            "SELECT * FROM products WHERE id = ?", (product_id,)
        )
    row = await cursor.fetchone()
    return dict(row) if row else None


async def get_all_active_products(db: aiosqlite.Connection) -> list:
    """获取所有有效产品"""
    try:
        cursor = await db.execute(
            "SELECT * FROM products WHERE is_active = 1 ORDER BY price_cents ASC"
        )
    except Exception:
        cursor = await db.execute(
            "SELECT * FROM products ORDER BY price_cents ASC"
        )
    rows = await cursor.fetchall()
    return [dict(row) for row in rows]


async def create_order(
    db: aiosqlite.Connection,
    user_id: int,
    product_id: int,
    amount_cents: int,
    currency: str = "USD"
) -> int:
    """创建订单"""
    now = datetime.utcnow().isoformat()
    cursor = await db.execute("""
        INSERT INTO orders (user_id, product_id, amount_cents, currency, status, created_at, updated_at)
        VALUES (?, ?, ?, ?, 'pending', ?, ?)
    """, (user_id, product_id, amount_cents, currency, now, now))
    await db.commit()
    return cursor.lastrowid


async def update_order_status(
    db: aiosqlite.Connection,
    order_id: int,
    status: str,
    provider: str = None,
    provider_tx_id: str = None
) -> None:
    """更新订单状态"""
    now = datetime.utcnow().isoformat()
    await db.execute("""
        UPDATE orders SET status = ?, payment_provider = ?, provider_transaction_id = ?, updated_at = ?
        WHERE id = ?
    """, (status, provider, provider_tx_id, now, order_id))
    await db.commit()


async def get_order_by_id(db: aiosqlite.Connection, order_id: int) -> Optional[dict]:
    """通过订单ID查询订单"""
    cursor = await db.execute(
        "SELECT * FROM orders WHERE id = ?", (order_id,)
    )
    row = await cursor.fetchone()
    return dict(row) if row else None
