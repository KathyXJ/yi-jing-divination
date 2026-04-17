"""
积分/用量系统 API 路由
"""
import os
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from ..database import (
    get_db, get_user_by_id, get_user_by_email, update_user_credits,
    add_credits_transaction, get_user_transactions,
    get_all_active_products, get_product_by_id,
    create_order, update_order_status, get_order_by_id
)

router = APIRouter(prefix="/api/credits", tags=["积分系统"])

# 积分消耗配置
AI_INTERPRET_COST = 3  # AI解读每次消耗积分


def get_current_user_id(request: Request) -> Optional[int]:
    """从请求中获取当前用户ID（通过 Authorization header 或 session）"""
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return None
    token = auth_header.split(" ", 1)[1]

    # 验证 JWT token 获取 user_id
    from ..routers.auth import verify_jwt_token
    payload = verify_jwt_token(token)
    if not payload:
        return None
    return int(payload["sub"])


class BalanceResponse(BaseModel):
    credits: int  # 总积分
    welcome_bonus_credits: int = 0  # Welcome Bonus 剩余
    welcome_bonus_expires_at: Optional[str] = None  # Welcome Bonus 到期时间
    monthly_subscription_credits: int = 0  # 月卡剩余
    monthly_subscription_expires_at: Optional[str] = None  # 月卡到期时间
    standard_pack_credits: int = 0  # 标准包剩余
    has_permanent_credits: bool = False  # 是否有永久积分
    # 显示用字段
    welcome_bonus_name: str = "Welcome Bonus"
    welcome_bonus_name_zh: str = "注册赠送"
    monthly_name: str = "Monthly Subscription"
    monthly_name_zh: str = "月度订阅"
    standard_name: str = "Standard Pack"
    standard_name_zh: str = "标准积分包"
    welcome_remaining_days: Optional[int] = None  # Welcome Bonus 剩余天数
    monthly_remaining_days: Optional[int] = None  # 月卡剩余天数


class DeductRequest(BaseModel):
    amount: int = AI_INTERPRET_COST


class DeductResponse(BaseModel):
    success: bool
    credits_used: int
    remaining_credits: int
    message: str


class GrantRequest(BaseModel):
    user_id: int
    amount: int
    description: str


class GrantResponse(BaseModel):
    success: bool
    credits_granted: int
    new_balance: int


class TransactionResponse(BaseModel):
    id: int
    type: str
    amount: int
    balance_after: int
    description: Optional[str]
    created_at: str


class ProductResponse(BaseModel):
    id: int
    name: str
    name_en: str
    credits: int
    price_cents: int
    type: str
    valid_days: Optional[int]
    description: Optional[str]
    description_en: Optional[str]


def check_subscription_active(expires_at: Optional[str]) -> bool:
    """检查订阅是否有效"""
    if not expires_at:
        return False
    try:
        exp_date = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
        return datetime.utcnow() < exp_date
    except Exception:
        return False


@router.get("/balance", response_model=BalanceResponse)
async def get_balance(request: Request):
    """查询当前用户积分余额"""
    user_id = get_current_user_id(request)
    if not user_id:
        raise HTTPException(status_code=401, detail="未登录或token无效")

    async with get_db() as db:
        user = await get_user_by_id(db, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="用户不存在")

        # 计算 Welcome Bonus 剩余天数
        welcome_remaining_days = None
        if user.get("welcome_bonus_expires_at"):
            expires = datetime.fromisoformat(user["welcome_bonus_expires_at"])
            remaining = (expires - datetime.utcnow()).days
            welcome_remaining_days = max(0, remaining)
        
        # 计算 Monthly Subscription 剩余天数
        monthly_remaining_days = None
        if user.get("monthly_subscription_expires_at"):
            expires = datetime.fromisoformat(user["monthly_subscription_expires_at"])
            remaining = (expires - datetime.utcnow()).days
            monthly_remaining_days = max(0, remaining)
        
        return BalanceResponse(
            credits=user["credits"],
            welcome_bonus_credits=user.get("welcome_bonus_credits", 0),
            welcome_bonus_expires_at=user.get("welcome_bonus_expires_at"),
            monthly_subscription_credits=user.get("monthly_subscription_credits", 0),
            monthly_subscription_expires_at=user.get("monthly_subscription_expires_at"),
            standard_pack_credits=user.get("standard_pack_credits", 0),
            has_permanent_credits=bool(user.get("has_permanent_credits")),
            welcome_remaining_days=welcome_remaining_days,
            monthly_remaining_days=monthly_remaining_days,
        )


@router.post("/deduct", response_model=DeductResponse)
async def deduct_credits(request: Request, body: DeductRequest):
    """扣减积分（AI解读时调用）"""
    user_id = get_current_user_id(request)
    if not user_id:
        raise HTTPException(status_code=401, detail="未登录或token无效")

    amount = body.amount
    if amount <= 0:
        raise HTTPException(status_code=400, detail="扣减积分必须大于0")

    async with get_db() as db:
        user = await get_user_by_id(db, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="用户不存在")

        # 检查总积分是否足够
        if user["credits"] < amount:
            raise HTTPException(
                status_code=402,
                detail=f"积分不足，需要{amount}积分，当前剩余{user['credits']}积分"
            )

        # 使用优先级扣除函数
        from ..database import deduct_credits_by_priority
        result = await deduct_credits_by_priority(db, user_id, amount)
        
        if not result["success"]:
            raise HTTPException(status_code=402, detail="积分不足")
        
        # 记录流水
        await add_credits_transaction(
            db, user_id, "deduct", -amount, result["total_remaining"],
            f"AI解读消耗{amount}积分"
        )

        return DeductResponse(
            success=True,
            credits_used=amount,
            remaining_credits=result["total_remaining"],
            message=f"消耗{amount}积分，剩余{result['total_remaining']}积分"
        )


@router.post("/grant", response_model=GrantResponse)
async def grant_credits(request: Request, body: GrantRequest):
    """管理员给用户发放积分（注册赠送、补偿等）"""
    # TODO: 添加管理员验证
    async with get_db() as db:
        user = await get_user_by_id(db, body.user_id)
        if not user:
            raise HTTPException(status_code=404, detail="用户不存在")

        new_balance = user["credits"] + body.amount
        await update_user_credits(db, body.user_id, new_balance)
        await add_credits_transaction(
            db, body.user_id, "grant", body.amount, new_balance,
            body.description
        )

        return GrantResponse(
            success=True,
            credits_granted=body.amount,
            new_balance=new_balance
        )


@router.get("/transactions", response_model=list[TransactionResponse])
async def list_transactions(request: Request, limit: int = 20):
    """获取积分变动流水"""
    user_id = get_current_user_id(request)
    if not user_id:
        raise HTTPException(status_code=401, detail="未登录或token无效")

    async with get_db() as db:
        txs = await get_user_transactions(db, user_id, limit)
        return [
            TransactionResponse(
                id=tx["id"],
                type=tx["type"],
                amount=tx["amount"],
                balance_after=tx["balance_after"],
                description=tx.get("description"),
                created_at=tx["created_at"]
            )
            for tx in txs
        ]


@router.get("/products-debug")
async def list_products_debug(request: Request):
    """调试端点：直接返回数据库查询结果和错误"""
    import traceback
    try:
        async with get_db() as db:
            cursor = await db.execute("PRAGMA table_info(products)")
            columns = await cursor.fetchall()
            cursor2 = await db.execute("SELECT * FROM products")
            rows = await cursor2.fetchall()
            return {
                "status": "ok",
                "columns": [dict(r) for r in columns],
                "rows": [dict(row) for row in rows]
            }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "traceback": traceback.format_exc()
        }


@router.get("/grant-debug")
async def grant_debug(request: Request, email: str = "", amount: int = 100):
    """临时调试接口：按email给用户加积分（无需认证）"""
    if not email:
        return {"error": "email required"}
    async with get_db() as db:
        user = await get_user_by_email(db, email)
        if not user:
            return {"error": "user not found", "email": email}
        new_balance = user["credits"] + amount
        await update_user_credits(db, user["id"], new_balance)
        await add_credits_transaction(
            db, user["id"], "grant", amount, new_balance,
            f"测试赠送{amount}积分"
        )
        return {
            "success": True,
            "user_id": user["id"],
            "email": email,
            "amount_granted": amount,
            "new_balance": new_balance
        }


@router.get("/products", response_model=list[ProductResponse])
async def list_products(request: Request):
    """获取所有有效产品列表"""
    try:
        async with get_db() as db:
            products = await get_all_active_products(db)
            return [
                ProductResponse(
                    id=p["id"],
                    name=p["name"],
                    name_en=p["name_en"],
                    credits=p["credits"],
                    price_cents=p["price_cents"],
                    type=p["type"],
                    valid_days=p.get("valid_days"),
                    description=p.get("description"),
                    description_en=p.get("description_en")
                )
                for p in products
            ]
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Database error: {e}")


class OrderCreateResponse(BaseModel):
    order_id: int
    amount_cents: int
    currency: str
    status: str


@router.post("/create-order")
async def create_purchase_order(request: Request, product_id: int):
    """创建购买订单（后续接入PayPal）"""
    user_id = get_current_user_id(request)
    if not user_id:
        raise HTTPException(status_code=401, detail="未登录或token无效")

    async with get_db() as db:
        product = await get_product_by_id(db, product_id)
        if not product:
            raise HTTPException(status_code=404, detail="产品不存在")

        if product["price_cents"] == 0:
            raise HTTPException(status_code=400, detail="免费产品无需下单")

        order_id = await create_order(
            db, user_id, product_id, product["price_cents"], "USD"
        )

        return OrderCreateResponse(
            order_id=order_id,
            amount_cents=product["price_cents"],
            currency="USD",
            status="pending"
        )


@router.get("/order/{order_id}")
async def get_order(request: Request, order_id: int):
    """查询订单状态"""
    user_id = get_current_user_id(request)
    if not user_id:
        raise HTTPException(status_code=401, detail="未登录或token无效")

    async with get_db() as db:
        order = await get_order_by_id(db, order_id)
        if not order:
            raise HTTPException(status_code=404, detail="订单不存在")
        if order["user_id"] != user_id:
            raise HTTPException(status_code=403, detail="无权访问此订单")

        return order


# 临时修复端点：修复产品表中的英文翻译
@router.post("/fix-product-translations")
async def fix_product_translations(request: Request):
    """修复产品表中的 name_en 和 description_en 字段"""
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    async with get_db() as db:
        translations = {
            "注册赠送": {"name_en": "Welcome Bonus", "description_en": "New users get 3 free credits, valid for 7 days"},
            "标准积分包": {"name_en": "Standard Pack", "description_en": "50 credits, forever valid"},
            "月度订阅": {"name_en": "Monthly Subscription", "description_en": "200 credits/month, auto-renewal"},
        }
        for name, trans in translations.items():
            await db.execute(
                "UPDATE products SET name_en = ?, description_en = ? WHERE name = ?",
                (trans["name_en"], trans["description_en"], name)
            )
        await db.commit()
        
        products = await get_all_active_products(db)
        return {"updated": len(translations), "products": [
            {"name": p["name"], "name_en": p.get("name_en"), "description_en": p.get("description_en")}
            for p in products
        ]}
