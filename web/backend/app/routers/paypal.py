"""
PayPal 支付 API
"""
import os
import json
from datetime import datetime
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
import httpx

router = APIRouter(prefix="/api/paypal", tags=["PayPal 支付"])

# PayPal 配置
PAYPAL_CLIENT_ID = os.getenv("PAYPAL_CLIENT_ID", "")
PAYPAL_CLIENT_SECRET = os.getenv("PAYPAL_CLIENT_SECRET", "")
PAYPAL_MODE = os.getenv("PAYPAL_MODE", "sandbox")  # sandbox 或 live

PAYPAL_BASE_URL = "https://api-m.sandbox.paypal.com" if PAYPAL_MODE == "sandbox" else "https://api-m.paypal.com"

# 产品定价（美分）
PRODUCT_PRICES = {
    "50_credits": 990,   # $9.9 = 990美分
    "monthly_200": 1990,  # $19.9 = 1990美分
}


class CreateOrderRequest(BaseModel):
    product_id: str  # "50_credits" 或 "monthly_200"
    user_id: int
    lang: str = "en"


class CaptureOrderRequest(BaseModel):
    order_id: str
    user_id: int
    lang: str = "en"


async def get_access_token() -> str:
    """获取 PayPal Access Token"""
    if not PAYPAL_CLIENT_ID or not PAYPAL_CLIENT_SECRET:
        raise HTTPException(status_code=500, detail="PayPal 未配置")
    
    auth_url = f"{PAYPAL_BASE_URL}/v1/oauth2/token"
    auth_data = "grant_type=client_credentials"
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            auth_url,
            auth=(PAYPAL_CLIENT_ID, PAYPAL_CLIENT_SECRET),
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            data=auth_data,
            timeout=30.0,
        )
    
    if response.status_code != 200:
        raise HTTPException(status_code=500, detail=f"PayPal 认证失败: {response.text}")
    
    return response.json()["access_token"]


def get_product_details(product_id: str) -> dict:
    """获取产品详情"""
    products = {
        "50_credits": {
            "name": "50 Credits (Permanent)",
            "name_zh": "50积分（永久）",
            "description": "50 permanent credits for AI divination",
            "price": 990,  # $9.90
        },
        "monthly_200": {
            "name": "Monthly 200 Credits",
            "name_zh": "月卡200积分",
            "description": "200 credits per month subscription",
            "price": 1990,  # $19.90
        },
    }
    
    if product_id not in products:
        raise HTTPException(status_code=400, detail=f"未知产品: {product_id}")
    
    return products[product_id]


@router.post("/create-order")
async def create_order(req: CreateOrderRequest):
    """创建 PayPal 订单"""
    try:
        access_token = await get_access_token()
        product = get_product_details(req.product_id)
        
        # PayPal 订单结构
        order_payload = {
            "intent": "CAPTURE",
            "purchase_units": [{
                "amount": {
                    "currency_code": "USD",
                    "value": f"{product['price'] / 100:.2f}",
                },
                "description": product["name"],
                "custom_id": f"{req.user_id}_{req.product_id}",
            }],
            "application_context": {
                "return_url": f"https://i-chingstudio.cc/pricing?payment=success",
                "cancel_url": f"https://i-chingstudio.cc/pricing?payment=cancelled",
                "brand_name": "I Ching Divination",
                "landing_page": "BILLING",
                "user_action": "PAY_NOW",
            },
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{PAYPAL_BASE_URL}/v2/checkout/orders",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json",
                },
                json=order_payload,
                timeout=30.0,
            )
        
        if response.status_code != 201:
            raise HTTPException(status_code=500, detail=f"PayPal 创建订单失败: {response.text}")
        
        order_data = response.json()
        return {
            "order_id": order_data["id"],
            "approval_url": next(
                (link["href"] for link in order_data["links"] if link["rel"] == "approve"),
                None
            ),
            "status": order_data["status"],
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"创建订单失败: {str(e)}")


@router.post("/capture-order")
async def capture_order(req: CaptureOrderRequest):
    """捕获 PayPal 订单（完成支付）"""
    try:
        access_token = await get_access_token()
        
        async with httpx.AsyncClient() as client:
            # 获取订单详情
            response = await client.get(
                f"{PAYPAL_BASE_URL}/v2/checkout/orders/{req.order_id}",
                headers={"Authorization": f"Bearer {access_token}"},
                timeout=30.0,
            )
        
        if response.status_code != 200:
            raise HTTPException(status_code=400, detail=f"订单不存在: {response.text}")
        
        order_data = response.json()
        
        # 检查订单状态（COMPLETED 表示已自动捕获，APPROVED 表示待捕获）
        if order_data["status"] not in ("APPROVED", "COMPLETED"):
            raise HTTPException(status_code=400, detail=f"订单未批准: {order_data['status']}")
        
        # 捕获订单
        async with httpx.AsyncClient() as client:
            capture_response = await client.post(
                f"{PAYPAL_BASE_URL}/v2/checkout/orders/{req.order_id}/capture",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json",
                },
                timeout=30.0,
            )
        
        if capture_response.status_code != 201:
            raise HTTPException(status_code=500, detail=f"支付捕获失败: {capture_response.text}")
        
        capture_data = capture_response.json()
        
        # 解析 custom_id 获取 user_id 和 product_id
        # custom_id 格式: "user_id_productid" 例如 "12_50_credits"
        # 使用第一个下划线分割: user_id=12, product_id="50_credits"
        custom_id = capture_data["purchase_units"][0]["payments"]["captures"][0]["custom_id"]
        parts = custom_id.split("_", 1)
        user_id = int(parts[0])
        product_id = parts[1]
        
        # 给用户加积分
        from ..database import (
            add_standard_pack_credits, add_monthly_subscription_credits,
            add_credits_transaction, get_db, get_user_by_id
        )
        
        credits_amount = 50 if product_id == "50_credits" else 200
        is_monthly = product_id == "monthly_200"
        is_permanent = product_id == "50_credits"
        
        async with get_db() as db:
            user = await get_user_by_id(db, user_id)
            if not user:
                raise HTTPException(status_code=404, detail="用户不存在")
            
            # 如果是月度订阅，检查是否已有有效的月度订阅
            if is_monthly and user.get("monthly_subscription_credits", 0) > 0:
                monthly_expires = user.get("monthly_subscription_expires_at")
                if monthly_expires and datetime.fromisoformat(monthly_expires) > datetime.utcnow():
                    raise HTTPException(status_code=400, detail="已有有效的月度订阅，无法重复购买")
            
            # 根据产品类型添加积分
            if is_permanent:
                # Standard Pack: 添加到标准包（可累计）
                new_balance = await add_standard_pack_credits(db, user_id, credits_amount)
                desc_en = f"PayPal purchase Standard Pack +{credits_amount} credits"
                desc_zh = f"PayPal购买标准积分包 +{credits_amount}积分"
            elif is_monthly:
                # Monthly Subscription: 设置月度订阅（不累计，覆盖）
                from datetime import timedelta
                expires_at = (datetime.utcnow() + timedelta(days=30)).isoformat()
                new_balance = await add_monthly_subscription_credits(db, user_id, credits_amount, expires_at)
                desc_en = f"PayPal purchase Monthly Subscription +{credits_amount} credits"
                desc_zh = f"PayPal购买月度订阅 +{credits_amount}积分"
            
            description = desc_en if req.lang == "en" else desc_zh
            
            await add_credits_transaction(
                db, user_id, "purchase", credits_amount, new_balance,
                description
            )
        
        return {
            "status": "COMPLETED",
            "credits_added": credits_amount,
            "capture_id": capture_data["purchase_units"][0]["payments"]["captures"][0]["id"],
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"支付处理失败: {str(e)}")


@router.get("/products")
async def list_products():
    """获取可购买的产品列表"""
    return {
        "products": [
            {
                "id": "50_credits",
                "name": "50 Credits (Permanent)",
                "name_zh": "50积分（永久）",
                "description": "Permanent credits for AI divination",
                "price": 9.90,
                "currency": "USD",
                "credits": 50,
            },
            {
                "id": "monthly_200",
                "name": "Monthly 200 Credits",
                "name_zh": "月卡200积分",
                "description": "200 credits per month",
                "price": 19.90,
                "currency": "USD",
                "credits": 200,
                "is_subscription": True,
            },
        ]
    }
