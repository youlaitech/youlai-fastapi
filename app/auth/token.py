"""Token 管理器 — JWT / Redis 双模式。"""

import time
import uuid
from abc import ABC, abstractmethod
from typing import Any

import jwt
from loguru import logger

from app.config import settings
from app.auth.schemas import AuthenticationToken, SysUserDetails


class TokenManager(ABC):
    """Token 管理器抽象基类。"""

    @abstractmethod
    async def generate_token(self, user: SysUserDetails) -> AuthenticationToken:
        """签发令牌。"""
        ...

    @abstractmethod
    async def parse_token(self, token: str) -> SysUserDetails | None:
        """解析令牌返回用户详情。"""
        ...

    @abstractmethod
    async def validate_token(self, token: str) -> bool:
        """校验令牌有效性。"""
        ...

    @abstractmethod
    async def refresh_token(self, refresh_token: str) -> AuthenticationToken | None:
        """刷新令牌。"""
        ...

    @abstractmethod
    async def invalidate_token(self, token: str) -> None:
        """使令牌失效。"""
        ...

    @abstractmethod
    async def invalidate_user_sessions(self, user_id: int) -> None:
        """踢人 — 使指定用户所有令牌失效。"""
        ...


# =====================================================================
# JWT 实现
# =====================================================================

class JwtTokenManager(TokenManager):
    """JWT Token 管理器。"""

    def __init__(self, redis=None):
        self._redis = redis  # 存放 tokenVersion
        self._secret = settings.JWT_SECRET_KEY
        self._access_ttl = settings.ACCESS_TOKEN_TTL
        self._refresh_ttl = settings.REFRESH_TOKEN_TTL

    @staticmethod
    def _user_claims(user: SysUserDetails) -> dict[str, Any]:
        return {
            "userId": user.userId,
            "username": user.username,
            "deptId": user.deptId,
            "dataScopes": user.dataScopes,
            "roles": list(user.roles),
            "isRoot": user.isRoot,
        }

    @staticmethod
    def _claims_to_user(claims: dict[str, Any]) -> SysUserDetails:
        return SysUserDetails(
            userId=claims.get("userId"),
            username=claims.get("username"),
            deptId=claims.get("deptId"),
            dataScopes=claims.get("dataScopes", []),
            roles=set(claims.get("roles", [])),
            isRoot=claims.get("isRoot", False),
            enabled=True,
        )

    async def _get_token_version(self, user_id: int) -> str:
        """从 Redis 获取用户 token 版本号（踢人时校验）。"""
        if self._redis is None:
            return "1"
        return await self._redis.get(f"token:version:{user_id}") or "1"

    async def generate_token(self, user: SysUserDetails) -> AuthenticationToken:
        now = int(time.time())
        token_version = await self._get_token_version(user.userId)

        access_payload = {
            **self._user_claims(user),
            "sub": str(user.userId),
            "iat": now,
            "exp": now + self._access_ttl,
            "tokenVersion": token_version,
            "type": "access",
        }
        refresh_payload = {
            "userId": user.userId,
            "sub": str(user.userId),
            "iat": now,
            "exp": now + self._refresh_ttl,
            "tokenVersion": token_version,
            "type": "refresh",
        }

        access_token = jwt.encode(access_payload, self._secret, algorithm="HS256")
        refresh_token = jwt.encode(refresh_payload, self._secret, algorithm="HS256")
        return AuthenticationToken(
            accessToken=access_token,
            refreshToken=refresh_token,
            expiresIn=self._access_ttl,
        )

    async def parse_token(self, token: str) -> SysUserDetails | None:
        try:
            claims = jwt.decode(token, self._secret, algorithms=["HS256"])
            if claims.get("type") != "access":
                return None
            token_version = await self._get_token_version(claims.get("userId", 0))
            if claims.get("tokenVersion") != token_version:
                return None
            return self._claims_to_user(claims)
        except jwt.ExpiredSignatureError:
            logger.debug("JWT token expired")
            return None
        except jwt.InvalidTokenError as e:
            logger.debug(f"Invalid JWT token: {e}")
            return None

    async def validate_token(self, token: str) -> bool:
        return await self.parse_token(token) is not None

    async def refresh_token(self, refresh_token: str) -> AuthenticationToken | None:
        try:
            claims = jwt.decode(refresh_token, self._secret, algorithms=["HS256"])
            if claims.get("type") != "refresh":
                return None
            token_version = await self._get_token_version(claims.get("userId", 0))
            if claims.get("tokenVersion") != token_version:
                return None
            user = SysUserDetails(
                userId=claims["userId"],
                username=claims.get("username", ""),
                roles=set(claims.get("roles", [])),
            )
            return await self.generate_token(user)
        except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
            return None

    async def invalidate_token(self, token: str) -> None:
        # JWT 本身无法撤销，通过 token version 实现踢人
        try:
            claims = jwt.decode(token, self._secret, algorithms=["HS256"], options={"verify_exp": False})
            user_id = claims.get("userId")
            if user_id and self._redis:
                await self._redis.incr(f"token:version:{user_id}")
        except jwt.InvalidTokenError:
            pass

    async def invalidate_user_sessions(self, user_id: int) -> None:
        if self._redis:
            await self._redis.incr(f"token:version:{user_id}")
            logger.info(f"User {user_id} all sessions invalidated")


# =====================================================================
# Redis-Token 实现
# =====================================================================

class RedisTokenManager(TokenManager):
    """Redis Token 管理器。"""

    def __init__(self, redis):
        self._redis = redis
        self._access_ttl = settings.ACCESS_TOKEN_TTL
        self._refresh_ttl = settings.REFRESH_TOKEN_TTL

    async def generate_token(self, user: SysUserDetails) -> AuthenticationToken:
        access_token = uuid.uuid4().hex
        refresh_token = uuid.uuid4().hex

        user_data = user.model_dump(exclude={"password"})
        # user_id → tokens 映射（踢人时遍历）
        token_set_key = f"token:user_tokens:{user.userId}"
        await self._redis.sadd(token_set_key, access_token)
        # 集合过期时间比 access_token 多留 1 小时，使踢人遍历时 token 仍在此集合内
        await self._redis.expire(token_set_key, self._access_ttl + 3600)

        await self._redis.setex(
            f"token:access:{access_token}", self._access_ttl, user.username
        )
        await self._redis.setex(
            f"token:refresh:{refresh_token}", self._refresh_ttl, str(user.userId)
        )
        await self._redis.setex(
            f"token:user_info:{access_token}", self._access_ttl,
            (await self._encode(user_data)),
        )
        return AuthenticationToken(
            accessToken=access_token,
            refreshToken=refresh_token,
            expiresIn=self._access_ttl,
        )

    async def parse_token(self, token: str) -> SysUserDetails | None:
        cached = await self._redis.get(f"token:user_info:{token}")
        if cached is None:
            return None
        try:
            data = await self._decode(cached)
            return SysUserDetails(**data)
        except Exception:
            return None

    async def validate_token(self, token: str) -> bool:
        raw = await self._redis.get(f"token:access:{token}")
        return raw is not None

    async def refresh_token(self, refresh_token: str) -> AuthenticationToken | None:
        user_id = await self._redis.get(f"token:refresh:{refresh_token}")
        if user_id is None:
            return None
        await self._redis.delete(f"token:refresh:{refresh_token}")
        user = SysUserDetails(userId=int(user_id))
        return await self.generate_token(user)

    async def invalidate_token(self, token: str) -> None:
        await self._redis.delete(f"token:access:{token}")
        await self._redis.delete(f"token:user_info:{token}")

    async def invalidate_user_sessions(self, user_id: int) -> None:
        token_set_key = f"token:user_tokens:{user_id}"
        tokens = await self._redis.smembers(token_set_key)
        for t in tokens:
            await self._redis.delete(f"token:access:{t}")
            await self._redis.delete(f"token:user_info:{t}")
        await self._redis.delete(token_set_key)
        logger.info(f"User {user_id} all sessions invalidated")

    @staticmethod
    async def _encode(data: dict) -> str:
        import orjson
        return orjson.dumps(data).decode()

    @staticmethod
    async def _decode(raw: str) -> dict:
        import orjson
        return orjson.loads(raw)


# =====================================================================
# 工厂函数
# =====================================================================

import asyncio

_token_manager: TokenManager | None = None
_token_manager_lock = asyncio.Lock()


async def get_token_manager() -> TokenManager:
    """获取 TokenManager 实例 — 根据 SESSION_TYPE 配置选择 JWT 或 Redis 实现。

    使用 asyncio.Lock 防止首次并发请求时重复创建实例。
    """
    global _token_manager
    if _token_manager is None:
        async with _token_manager_lock:
            # double-check
            if _token_manager is None:
                from app.redis import get_redis

                redis_client = await get_redis()
                if settings.SESSION_TYPE == "redis-token":
                    _token_manager = RedisTokenManager(redis_client)
                else:
                    _token_manager = JwtTokenManager(redis_client)
    return _token_manager
