import secrets

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from insight_engine.api.deps import (
    get_current_user,
    hash_password,
    hash_token,
    verify_password,
)
from insight_engine.api.schemas import (
    LoginRequest,
    LoginResponse,
    UserCreateRequest,
    UserResponse,
    UserUpdateRequest,
)
from insight_engine.database import get_session
from insight_engine.domain.models import User

router = APIRouter(tags=["users"])


def _user_response(user: User) -> UserResponse:
    # alerts_enabled is None on a freshly built object until the DB default
    # applies; treat unset as enabled.
    return UserResponse(
        id=user.id,
        email=user.email,
        name=user.name,
        alerts_enabled=True if user.alerts_enabled is None else user.alerts_enabled,
    )


@router.post("/users", response_model=UserResponse, status_code=201)
async def register_user(
    request: UserCreateRequest,
    session: AsyncSession = Depends(get_session),
):
    """Register a new user. Obtain a bearer token via POST /login."""
    email = request.email.lower()
    result = await session.execute(select(User).where(User.email == email))
    if result.scalar_one_or_none() is not None:
        raise HTTPException(status_code=409, detail="Email already registered")

    user = User(
        email=email,
        name=request.name,
        password_hash=hash_password(request.password),
    )
    session.add(user)
    await session.commit()

    return _user_response(user)


@router.post("/login", response_model=LoginResponse)
async def login(
    request: LoginRequest,
    session: AsyncSession = Depends(get_session),
):
    """Verify credentials and issue a bearer token (rotates any previous one)."""
    result = await session.execute(
        select(User).where(User.email == request.email.lower())
    )
    user = result.scalar_one_or_none()

    if (
        user is None
        or user.password_hash is None
        or not verify_password(request.password, user.password_hash)
    ):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token = secrets.token_urlsafe(32)
    user.api_token_hash = hash_token(token)
    await session.commit()

    return LoginResponse(token=token)


@router.get("/users/me", response_model=UserResponse)
async def get_me(user: User = Depends(get_current_user)):
    """Return the authenticated user."""
    return _user_response(user)


@router.patch("/users/me", response_model=UserResponse)
async def update_me(
    request: UserUpdateRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Update the authenticated user's email, name, or password."""
    if request.email is not None:
        email = request.email.lower()
        if email != user.email:
            result = await session.execute(select(User).where(User.email == email))
            if result.scalar_one_or_none() is not None:
                raise HTTPException(status_code=409, detail="Email already registered")
            user.email = email

    if request.name is not None:
        user.name = request.name

    if request.alerts_enabled is not None:
        user.alerts_enabled = request.alerts_enabled

    if request.password is not None:
        if request.current_password is None or not verify_password(
            request.current_password, user.password_hash or ""
        ):
            raise HTTPException(
                status_code=401,
                detail="Changing the password requires the correct current password",
            )
        user.password_hash = hash_password(request.password)
        # Force re-login after a password change
        user.api_token_hash = None

    await session.commit()
    return _user_response(user)


@router.delete("/users/me", status_code=204)
async def delete_me(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Delete the authenticated user and, via cascade, their portfolio, positions, and insights."""
    await session.delete(user)
    await session.commit()
