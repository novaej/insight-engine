import hashlib
import hmac
import os

from fastapi import Depends, Header, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from insight_engine.database import get_session
from insight_engine.domain.models import Portfolio, User

PBKDF2_ITERATIONS = 600_000

DEFAULT_USER_PROFILE = {"risk": "moderate", "horizon": "long", "goal": "growth"}


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode(), salt, PBKDF2_ITERATIONS
    )
    return f"pbkdf2${PBKDF2_ITERATIONS}${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        scheme, iterations, salt_hex, hash_hex = stored.split("$")
        if scheme != "pbkdf2":
            return False
        digest = hashlib.pbkdf2_hmac(
            "sha256", password.encode(), bytes.fromhex(salt_hex), int(iterations)
        )
        return hmac.compare_digest(digest.hex(), hash_hex)
    except (ValueError, AttributeError):
        return False


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


async def get_current_user(
    authorization: str | None = Header(None),
    session: AsyncSession = Depends(get_session),
) -> User:
    """Resolve the calling user from a bearer token (obtained via POST /login)."""
    if authorization is None:
        raise HTTPException(status_code=401, detail="Not authenticated")

    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(status_code=401, detail="Invalid Authorization header")

    result = await session.execute(
        select(User).where(User.api_token_hash == hash_token(token))
    )
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return user


async def get_user_portfolio(
    user: User, session: AsyncSession, create: bool = False
) -> Portfolio | None:
    """Fetch the user's portfolio, optionally creating an empty one."""
    result = await session.execute(
        select(Portfolio).where(Portfolio.user_id == user.id)
    )
    portfolio = result.scalar_one_or_none()
    if portfolio is None and create:
        portfolio = Portfolio(user_id=user.id, user_profile=dict(DEFAULT_USER_PROFILE))
        session.add(portfolio)
        await session.flush()
    return portfolio
