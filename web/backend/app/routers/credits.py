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
    credits: int
    subscription_type: Optional[str]
    subscription_expires_at: Optional[str]
    is_subscription_active: bool


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

        is_active = check_subscription_active(user.get("subscription_expires_at"))

        return BalanceResponse(
            credits=user["credits"],
            subscription_type=user.get("subscription_type"),
            subscription_expires_at=user.get("subscription_expires_at"),
            is_subscription_active=is_active
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

        current_credits = user["credits"]
        is_subscription_active = check_subscription_active(user.get("subscription_expires_at"))

        # 计算可用积分（余额 + 订阅月额度）
        monthly_credits = 0
        if is_subscription_active:
            monthly_credits = 200  # 月度订阅每月200积分

        # 简单处理：优先扣订阅额度，再扣余额
        # TODO: 需要更精确的月度额度追踪（每月1日重置）

        available = current_credits + monthly_credits
        if available < amount:
            raise HTTPException(
                status_code=402,
                detail=f"积分不足，需要{amount}积分，当前剩余{current_credits}积分（订阅额度{monthly_credits}）"
            )

        # 扣减逻辑：先扣余额，余额不够再扣订阅额度
        if current_credits >= amount:
            new_credits = current_credits - amount
            await update_user_credits(db, user_id, new_credits)
            await add_credits_transaction(
                db, user_id, "deduct", -amount, new_credits,
                f"AI解读消耗{amount}积分"
            )
            remaining = new_credits
        else:
            # 扣订阅额度
            from_sub = amount - current_credits
            new_credits = 0
            await update_user_credits(db, user_id, new_credits)
            await add_credits_transaction(
                db, user_id, "deduct", -current_credits, new_credits,
                f"AI解读消耗{from_sub}积分（订阅额度）"
            )
            remaining = 0

        return DeductResponse(
            success=True,
            credits_used=amount,
            remaining_credits=remaining,
            message=f"消耗{amount}积分，剩余{remaining}积分"
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
