"""
Google OAuth 认证路由
"""
import os
import secrets
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from google.oauth2.credentials import Credentials
from jose import JWTError, jwt

from ..database import get_db, get_user_by_google_id, get_user_by_email, create_user, update_user
from ..models import User, Token

router = APIRouter(prefix="/auth", tags=["认证"])

# ===== 配置 =====
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
# Google OAuth Redirect URI（回调地址）
GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI", "https://yi-jing-divination-4h6y.onrender.com/auth/google/callback")
# JWT 配置
JWT_SECRET = os.getenv("JWT_SECRET", "your-super-secret-key-change-in-production")
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24 * 7  # 7天

# Google OAuth 范围
GOOGLE_SCOPE = [
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
]

# 内存存储 state（生产环境建议用 Redis）
oauth_state_store = {}


def create_jwt_token(user_id: int, email: str) -> str:
    """创建 JWT token"""
    expire = datetime.utcnow() + timedelta(hours=JWT_EXPIRATION_HOURS)
    payload = {
        "sub": str(user_id),
        "email": email,
        "exp": expire,
        "iat": datetime.utcnow(),
    }
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return token


def verify_jwt_token(token: str) -> Optional[dict]:
    """验证 JWT token"""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except JWTError:
        return None


def get_google_oauth_url(state: str) -> str:
    """获取 Google OAuth 授权 URL"""
    from google_auth_oauthlib.flow import Flow
    
    client_config = {
        "web": {
            "client_id": GOOGLE_CLIENT_ID,
            "client_secret": GOOGLE_CLIENT_SECRET,
            "redirect_uris": [GOOGLE_REDIRECT_URI],
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
        }
    }
    
    flow = Flow.from_client_config(client_config, scopes=GOOGLE_SCOPE)
    flow.redirect_uri = GOOGLE_REDIRECT_URI
    
    auth_url, _ = flow.authorization_url(
        access_type="offline",
        prompt="consent",
        state=state,
        include_granted_scopes="true",
    )
    return auth_url


def exchange_code_for_tokens(code: str) -> dict:
    """用 authorization code 换取 access token"""
    from google_auth_oauthlib.flow import Flow
    
    client_config = {
        "web": {
            "client_id": GOOGLE_CLIENT_ID,
            "client_secret": GOOGLE_CLIENT_SECRET,
            "redirect_uris": [GOOGLE_REDIRECT_URI],
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
        }
    }
    
    flow = Flow.from_client_config(client_config, scopes=GOOGLE_SCOPE)
    flow.redirect_uri = GOOGLE_REDIRECT_URI
    flow.fetch_token(code=code)
    
    # 从 credentials 对象中提取需要的字段
    creds = flow.credentials
    return {
        "access_token": creds.token,
        "refresh_token": getattr(creds, 'refresh_token', None),
        "id_token": getattr(creds, 'id_token', None),
        "token_type": getattr(creds, 'token_type', 'Bearer'),
    }


def get_google_user_info(access_token: str) -> dict:
    """获取 Google 用户信息"""
    import requests
    user_info_response = requests.get(
        "https://www.googleapis.com/oauth2/v2/userinfo",
        headers={"Authorization": f"Bearer {access_token}"}
    )
    user_info_response.raise_for_status()
    return user_info_response.json()


class LoginResponse(BaseModel):
    """登录成功响应"""
    token: str
    user: dict
    redirect_url: str


@router.get("/google")
async def google_login():
    """跳转到 Google 登录页面"""
    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
        raise HTTPException(
            status_code=500,
            detail="Google OAuth 未配置，请联系管理员"
        )
    
    # 生成 state 参数防止 CSRF
    state = secrets.token_urlsafe(32)
    
    # 清理过期的 state（保留最近10分钟内的）
    cutoff = datetime.utcnow() - timedelta(minutes=10)
    for old_state in list(oauth_state_store.keys()):
        state_data = oauth_state_store.get(old_state, {})
        created_str = state_data.get("created_at", "")
        if created_str:
            try:
                created = datetime.fromisoformat(created_str)
                if created < cutoff:
                    del oauth_state_store[old_state]
            except Exception:
                pass
    
    oauth_state_store[state] = {"created_at": datetime.utcnow().isoformat()}
    
    auth_url = get_google_oauth_url(state)
    return RedirectResponse(url=auth_url)


@router.get("/google/callback")
async def google_callback(request: Request, code: Optional[str] = None, state: Optional[str] = None, error: Optional[str] = None):
    """Google OAuth 回调处理"""
    # 检查错误
    if error:
        raise HTTPException(status_code=400, detail=f"Google 授权失败: {error}")
    
    if not code:
        raise HTTPException(status_code=400, detail="缺少 authorization code")
    
    # 验证 state
    if state not in oauth_state_store:
        raise HTTPException(status_code=400, detail="无效的 state 参数")
    
    # 清理 state
    del oauth_state_store[state]
    
    try:
        # 换取 access token
        tokens = exchange_code_for_tokens(code)
        access_token = tokens["access_token"]
        
        # 获取用户信息
        user_info = get_google_user_info(access_token)
        
        google_id = user_info.get("id")
        email = user_info.get("email")
        name = user_info.get("name")
        avatar_url = user_info.get("picture")
        
        if not google_id or not email:
            raise HTTPException(status_code=400, detail="无法获取用户信息")
        
        # 异步获取数据库连接
        import aiosqlite
        db_path = os.path.join(os.path.dirname(__file__), "..", "..", "data", "users.db")
        async with aiosqlite.connect(db_path) as db:
            db.row_factory = aiosqlite.Row
            
            # 查找或创建用户
            user = await get_user_by_google_id(db, google_id)
            
            if user is None:
                # 新用户，先检查邮箱是否已存在
                existing_user = await get_user_by_email(db, email)
                if existing_user:
                    # 邮箱已存在，关联 Google ID
                    user = await update_user(db, existing_user["id"], name, avatar_url)
                    # 更新 google_id
                    await db.execute(
                        "UPDATE users SET google_id = ? WHERE id = ?",
                        (google_id, existing_user["id"])
                    )
                    await db.commit()
                    user = await get_user_by_google_id(db, google_id)
                else:
                    # 创建新用户
                    user = await create_user(db, google_id, email, name, avatar_url)
            else:
                # 老用户，更新信息
                user = await update_user(db, user["id"], name, avatar_url)
            
            # 生成 JWT token
            jwt_token = create_jwt_token(user["id"], user["email"])
            
            # 重定向到前端 callback 页面，带上 token
            frontend_callback_url = os.getenv(
                "FRONTEND_CALLBACK_URL",
                "https://i-chingstudio.cc/auth/callback"
            )
            redirect_url = f"{frontend_callback_url}?token={jwt_token}"
            return RedirectResponse(url=redirect_url)
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"登录处理失败: {str(e)}")


@router.get("/me")
async def get_current_user(request: Request):
    """获取当前登录用户信息（需携带 token）"""
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="未携带 token")
    
    token = auth_header.split(" ", 1)[1]
    payload = verify_jwt_token(token)
    
    if not payload:
        raise HTTPException(status_code=401, detail="无效或已过期的 token")
    
    user_id = int(payload["sub"])
    email = payload["email"]
    
    # 获取用户信息
    import aiosqlite
    db_path = os.path.join(os.path.dirname(__file__), "..", "..", "data", "users.db")
    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        row = await cursor.fetchone()
        
        if not row:
            raise HTTPException(status_code=404, detail="用户不存在")
        
        user = dict(row)
        return {
            "id": user["id"],
            "email": user["email"],
            "name": user["name"],
            "avatar_url": user["avatar_url"],
        }


@router.post("/logout")
async def logout(request: Request):
    """登出（前端删除 token 即可，这里只是占位）"""
    return {"message": "已登出"}
