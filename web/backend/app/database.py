"""
数据库连接与初始化（支持 SQLite 和 PostgreSQL）
"""
import aiosqlite
import asyncpg
import os
import re
from datetime import datetime, timedelta
from typing import Optional, Union, List, Any
from contextlib import asynccontextmanager

# 数据库配置
DATABASE_URL = os.environ.get("DATABASE_URL", "")
DATABASE_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "users.db")

# 判断使用哪种数据库
USE_POSTGRES = DATABASE_URL.startswith("postgresql://")

# 确保 SQLite data 目录存在（本地开发用）
if not USE_POSTGRES:
    os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)


class DatabaseConnection:
    """统一的数据库连接包装器，兼容 SQLite 和 PostgreSQL"""
    
    def __init__(self, conn: Union[aiosqlite.Connection, asyncpg.Connection]):
        self.conn = conn
        self.is_postgres = isinstance(conn, asyncpg.Connection)
    
    def transaction(self):
        """返回事务上下文管理器"""
        if self.is_postgres:
            return self.conn.transaction()
        else:
            return self.conn
    
    async def execute(self, sql: str, *params) -> Any:
        """执行 SQL，自动处理参数占位符"""
        if self.is_postgres:
            # PostgreSQL: 将 ? 转换为 $1, $2, ...
            sql = self._convert_placeholders(sql)
            return await self.conn.execute(sql, *params)
        else:
            # SQLite: 直接使用 ?
            return await self.conn.execute(sql, params)
    
    async def fetchone(self, sql: str, *params) -> Optional[dict]:
        """查询单行，返回字典"""
        if self.is_postgres:
            sql = self._convert_placeholders(sql)
            row = await self.conn.fetchrow(sql, *params)
            return dict(row) if row else None
        else:
            cursor = await self.conn.execute(sql, params)
            row = await cursor.fetchone()
            if row:
                # aiosqlite.Row 可以转换为 dict
                return {key: row[key] for key in row.keys()}
            return None
    
    async def fetchall(self, sql: str, *params) -> List[dict]:
        """查询多行，返回字典列表"""
        if self.is_postgres:
            sql = self._convert_placeholders(sql)
            rows = await self.conn.fetch(sql, *params)
            return [dict(row) for row in rows]
        else:
            cursor = await self.conn.execute(sql, params)
            rows = await cursor.fetchall()
            return [{key: row[key] for key in row.keys()} for row in rows]
    
    async def commit(self):
        """提交事务"""
        if self.is_postgres:
            # PostgreSQL: 每个语句自动提交，不需要显式 commit
            pass
        else:
            await self.conn.commit()
    
    def _convert_placeholders(self, sql: str) -> str:
        """将 SQLite 的 ? 转换为 PostgreSQL 的 $1, $2, ..."""
        if not self.is_postgres:
            return sql
        
        # 替换 ? 为 $1, $2, ...
        counter = [0]
        def replace(match):
            counter[0] += 1
            return f"${counter[0]}"
        
        return re.sub(r'\?', replace, sql)


@asynccontextmanager
async def get_db():
    """获取数据库连接（异步上下文管理器）
    
    优先使用 PostgreSQL（DATABASE_URL 环境变量），
    否则回退到 SQLite（本地开发）
    """
    if USE_POSTGRES:
        # PostgreSQL 模式
        conn = await asyncpg.connect(DATABASE_URL)
        try:
            yield DatabaseConnection(conn)
        finally:
            await conn.close()
    else:
        # SQLite 模式（本地开发）
        db = await aiosqlite.connect(DATABASE_PATH)
        db.row_factory = aiosqlite.Row
        # 启用 WAL 模式确保写入持久化
        await db.execute("PRAGMA journal_mode=WAL")
        await db.execute("PRAGMA synchronous=NORMAL")
        try:
            yield DatabaseConnection(db)
        finally:
            await db.close()


# ==================== 用户相关操作 ====================

async def init_db():
    """初始化数据库表"""
    async with get_db() as db:
        # 用户表
        if USE_POSTGRES:
            # PostgreSQL 语法
            await db.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
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
            
            # 积分变动流水表
            await db.execute("""
                CREATE TABLE IF NOT EXISTS credits_transactions (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL REFERENCES users(id),
                    type TEXT NOT NULL,
                    amount INTEGER NOT NULL,
                    balance_after INTEGER NOT NULL,
                    description TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # PayPal 订单表
            await db.execute("""
                CREATE TABLE IF NOT EXISTS orders (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL REFERENCES users(id),
                    product_id INTEGER NOT NULL,
                    amount_cents INTEGER NOT NULL,
                    currency TEXT NOT NULL,
                    paypal_order_id TEXT,
                    status TEXT DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 产品表
            await db.execute("""
                CREATE TABLE IF NOT EXISTS products (
                    id SERIAL PRIMARY KEY,
                    name TEXT NOT NULL,
                    name_en TEXT,
                    credits INTEGER NOT NULL,
                    price_cents INTEGER NOT NULL,
                    type TEXT NOT NULL,
                    valid_days INTEGER,
                    description TEXT,
                    description_en TEXT,
                    is_active INTEGER DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 清理重复产品（保留 ID 1-3）
            await db.execute("DELETE FROM products WHERE id > 3")
            
            # 插入默认产品（如果不存在）
            await db.execute("""
                INSERT INTO products (id, name, name_en, credits, price_cents, type, valid_days, description, description_en)
                VALUES 
                    (1, '注册赠送', 'Welcome Bonus', 3, 0, 'welcome', 7, '新用户注册赠送3积分，7天有效', 'New users get 3 free credits, valid for 7 days'),
                    (2, '标准积分包', 'Standard Pack', 50, 990, 'standard', NULL, '50积分，永久有效', '50 credits, forever valid'),
                    (3, '月度订阅', 'Monthly Subscription', 200, 1990, 'monthly', 30, '200积分/月，30天有效', '200 credits/month, 30 days valid')
                ON CONFLICT (id) DO NOTHING
            """)
            
        else:
            # SQLite 语法
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
            
            # 积分变动流水表
            await db.execute("""
                CREATE TABLE IF NOT EXISTS credits_transactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    type TEXT NOT NULL,
                    amount INTEGER NOT NULL,
                    balance_after INTEGER NOT NULL,
                    description TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # PayPal 订单表
            await db.execute("""
                CREATE TABLE IF NOT EXISTS orders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    product_id INTEGER NOT NULL,
                    amount_cents INTEGER NOT NULL,
                    currency TEXT NOT NULL,
                    paypal_order_id TEXT,
                    status TEXT DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 产品表
            await db.execute("""
                CREATE TABLE IF NOT EXISTS products (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    name_en TEXT,
                    credits INTEGER NOT NULL,
                    price_cents INTEGER NOT NULL,
                    type TEXT NOT NULL,
                    valid_days INTEGER,
                    description TEXT,
                    description_en TEXT,
                    is_active INTEGER DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 插入默认产品
            await db.execute("""
                INSERT OR IGNORE INTO products (id, name, name_en, credits, price_cents, type, valid_days, description, description_en)
                VALUES 
                    (1, '注册赠送', 'Welcome Bonus', 3, 0, 'welcome', 7, '新用户注册赠送3积分，7天有效', 'New users get 3 free credits, valid for 7 days'),
                    (2, '标准积分包', 'Standard Pack', 50, 990, 'standard', NULL, '50积分，永久有效', '50 credits, forever valid'),
                    (3, '月度订阅', 'Monthly Subscription', 200, 1990, 'monthly', 30, '200积分/月，30天有效', '200 credits/month, 30 days valid')
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
        
        await db.commit()


async def get_user_by_google_id(db: DatabaseConnection, google_id: str) -> Optional[dict]:
    """通过 Google ID 查询用户"""
    return await db.fetchone("SELECT * FROM users WHERE google_id = ?", google_id)


async def get_user_by_email(db: DatabaseConnection, email: str) -> Optional[dict]:
    """通过邮箱查询用户"""
    return await db.fetchone("SELECT * FROM users WHERE email = ?", email)


async def get_user_by_id(db: DatabaseConnection, user_id: int) -> Optional[dict]:
    """通过 ID 查询用户"""
    return await db.fetchone("SELECT * FROM users WHERE id = ?", user_id)


async def create_user(db: DatabaseConnection, google_id: str, email: str, name: str, avatar_url: str = None) -> dict:
    """创建新用户，赠送 Welcome Bonus"""
    now = datetime.utcnow()
    welcome_bonus_expires = datetime.utcnow() + timedelta(days=7)
    
    if USE_POSTGRES:
        # PostgreSQL: 使用 RETURNING
        row = await db.fetchone("""
            INSERT INTO users (google_id, email, name, avatar_url, credits, 
                welcome_bonus_credits, welcome_bonus_expires_at, created_at, updated_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
            RETURNING *
        """, google_id, email, name, avatar_url, 3, 3, welcome_bonus_expires, now, now)
        return row
    else:
        # SQLite
        cursor = await db.execute("""
            INSERT INTO users (google_id, email, name, avatar_url, credits, 
                welcome_bonus_credits, welcome_bonus_expires_at, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, google_id, email, name, avatar_url, 3, 3, welcome_bonus_expires, now, now)
        await db.commit()
        
        # 获取刚创建的用户
        user_id = cursor.lastrowid
        return await get_user_by_id(db, user_id)


async def update_user(db: DatabaseConnection, user_id: int, name: str = None, avatar_url: str = None) -> Optional[dict]:
    """更新用户信息"""
    now = datetime.utcnow()
    updates = []
    params = []
    if name is not None:
        updates.append("name = ?")
        params.append(name)
    if avatar_url is not None:
        updates.append("avatar_url = ?")
        params.append(avatar_url)
    
    if updates:
        updates.append("updated_at = ?")
        params.append(now)
        params.append(user_id)
        
        sql = f"UPDATE users SET {', '.join(updates)} WHERE id = ?"
        await db.execute(sql, *params)
        await db.commit()
    
    return await get_user_by_id(db, user_id)


async def update_user_credits(db: DatabaseConnection, user_id: int, credits: int):
    """更新用户总积分"""
    now = datetime.utcnow()
    await db.execute(
        "UPDATE users SET credits = ?, updated_at = ? WHERE id = ?",
        credits, now, user_id
    )
    await db.commit()


async def get_user_credits(db: DatabaseConnection, user_id: int) -> int:
    """获取用户当前总积分"""
    row = await db.fetchone("SELECT credits FROM users WHERE id = ?", user_id)
    return row["credits"] if row else 0


async def add_standard_pack_credits(db: DatabaseConnection, user_id: int, credits: int) -> int:
    """添加标准积分包积分（永久）"""
    now = datetime.utcnow()
    # 获取当前用户
    user = await get_user_by_id(db, user_id)
    if not user:
        raise ValueError(f"User {user_id} not found")
    
    # 更新标准包积分和永久积分标志
    new_standard = user.get("standard_pack_credits", 0) + credits
    new_total = user["credits"] + credits
    
    await db.execute(
        "UPDATE users SET standard_pack_credits = ?, has_permanent_credits = 1, credits = ?, updated_at = ? WHERE id = ?",
        new_standard, new_total, now, user_id
    )
    await db.commit()
    return new_total


async def add_monthly_subscription_credits(db: DatabaseConnection, user_id: int, credits: int, expires_at) -> int:
    """添加月度订阅积分"""
    now = datetime.utcnow()
    # 获取当前用户
    user = await get_user_by_id(db, user_id)
    if not user:
        raise ValueError(f"User {user_id} not found")
    
    # 更新月度订阅积分和总积分
    new_monthly = credits
    new_total = user["credits"] + credits
    
    await db.execute(
        "UPDATE users SET monthly_subscription_credits = ?, monthly_subscription_expires_at = ?, credits = ?, updated_at = ? WHERE id = ?",
        new_monthly, expires_at, new_total, now, user_id
    )
    await db.commit()
    return new_total


async def deduct_credits_by_priority(db: DatabaseConnection, user_id: int, amount: int) -> dict:
    """
    按优先级扣除积分：Welcome Bonus -> Monthly Subscription -> Standard Pack
    返回扣除结果和剩余各类型积分
    """
    now = datetime.utcnow()  # Use naive datetime for database compatibility
    
    # 获取用户当前积分状态
    user = await get_user_by_id(db, user_id)
    if not user:
        return {"success": False, "error": "User not found"}
    
    welcome = user.get("welcome_bonus_credits", 0) or 0
    monthly = user.get("monthly_subscription_credits", 0) or 0
    standard = user.get("standard_pack_credits", 0) or 0
    
    # 保存原始值用于比较
    original_welcome = welcome
    original_monthly = monthly
    original_standard = standard
    
    # 检查并处理 welcome bonus 过期
    welcome_expires = user.get("welcome_bonus_expires_at")
    if welcome_expires:
        # 支持 datetime 对象或字符串
        if isinstance(welcome_expires, str):
            expires_dt = datetime.fromisoformat(welcome_expires)
        elif isinstance(welcome_expires, datetime):
            expires_dt = welcome_expires
        else:
            expires_dt = None
        
        if expires_dt and expires_dt < datetime.utcnow():
            # welcome bonus 过期，余额转入 standard pack
            if welcome > 0:
                standard += welcome
                await db.execute(
                    "UPDATE users SET standard_pack_credits = ?, welcome_bonus_credits = 0, welcome_bonus_expires_at = NULL WHERE id = ?",
                    standard, user_id
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
            welcome, user_id
        )
    
    # 2. 再扣 Monthly Subscription
    if remaining > 0 and monthly > 0:
        deduct = min(monthly, remaining)
        monthly -= deduct
        remaining -= deduct
        deducted_from.append(("monthly_subscription", deduct))
        await db.execute(
            "UPDATE users SET monthly_subscription_credits = ? WHERE id = ?",
            monthly, user_id
        )
    
    # 3. 最后扣 Standard Pack
    if remaining > 0 and standard > 0:
        deduct = min(standard, remaining)
        standard -= deduct
        remaining -= deduct
        deducted_from.append(("standard_pack", deduct))
        await db.execute(
            "UPDATE users SET standard_pack_credits = ? WHERE id = ?",
            standard, user_id
        )
    
    # 计算总积分
    total = welcome + monthly + standard
    
    # 如果有任何变化，更新用户积分
    if welcome != original_welcome or monthly != original_monthly or standard != original_standard:
        await db.execute(
            "UPDATE users SET welcome_bonus_credits = ?, monthly_subscription_credits = ?, standard_pack_credits = ?, credits = ? WHERE id = ?",
            welcome, monthly, standard, total, user_id
        )
    elif total != user.get("credits", 0):
        # 只有总积分变化，单独更新 credits
        await db.execute(
            "UPDATE users SET credits = ? WHERE id = ?",
            total, user_id
        )
    
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
    db: DatabaseConnection,
    user_id: int,
    tx_type: str,
    amount: int,
    balance_after: int,
    description: str = None
) -> int:
    """记录积分变动流水，返回事务ID"""
    now = datetime.utcnow()
    
    if USE_POSTGRES:
        # PostgreSQL
        row = await db.fetchone("""
            INSERT INTO credits_transactions (user_id, type, amount, balance_after, description, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            RETURNING id
        """, user_id, tx_type, amount, balance_after, description, now)
        return row["id"] if row else None
    else:
        # SQLite
        cursor = await db.execute("""
            INSERT INTO credits_transactions (user_id, type, amount, balance_after, description, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, user_id, tx_type, amount, balance_after, description, now)
        await db.commit()
        return cursor.lastrowid


async def get_user_transactions(db: DatabaseConnection, user_id: int, limit: int = 20) -> list:
    """获取用户积分流水记录"""
    return await db.fetchall(
        "SELECT * FROM credits_transactions WHERE user_id = ? ORDER BY created_at DESC LIMIT ?",
        user_id, limit
    )


# ==================== 产品相关操作 ====================

async def get_all_active_products(db: DatabaseConnection) -> list:
    """获取所有有效产品"""
    return await db.fetchall("SELECT * FROM products WHERE is_active = 1 ORDER BY id")


async def get_product_by_id(db: DatabaseConnection, product_id: int) -> Optional[dict]:
    """通过 ID 获取产品"""
    return await db.fetchone("SELECT * FROM products WHERE id = ? AND is_active = 1", product_id)


# ==================== 订单相关操作 ====================

async def create_order(db: DatabaseConnection, user_id: int, product_id: int, amount_cents: int, currency: str) -> int:
    """创建订单，返回订单ID"""
    now = datetime.utcnow()
    
    if USE_POSTGRES:
        row = await db.fetchone("""
            INSERT INTO orders (user_id, product_id, amount_cents, currency, status, created_at, updated_at)
            VALUES (?, ?, ?, ?, 'pending', ?, ?)
            RETURNING id
        """, user_id, product_id, amount_cents, currency, now, now)
        return row["id"] if row else None
    else:
        cursor = await db.execute("""
            INSERT INTO orders (user_id, product_id, amount_cents, currency, status, created_at, updated_at)
            VALUES (?, ?, ?, ?, 'pending', ?, ?)
        """, user_id, product_id, amount_cents, currency, now, now)
        await db.commit()
        return cursor.lastrowid


async def update_order_status(db: DatabaseConnection, order_id: int, status: str, paypal_order_id: str = None):
    """更新订单状态"""
    now = datetime.utcnow().isoformat()
    if paypal_order_id:
        await db.execute(
            "UPDATE orders SET status = ?, paypal_order_id = ?, updated_at = ? WHERE id = ?",
            status, paypal_order_id, now, order_id
        )
    else:
        await db.execute(
            "UPDATE orders SET status = ?, updated_at = ? WHERE id = ?",
            status, now, order_id
        )
    await db.commit()


async def get_order_by_id(db: DatabaseConnection, order_id: int) -> Optional[dict]:
    """通过 ID 获取订单"""
    return await db.fetchone("SELECT * FROM orders WHERE id = ?", order_id)
