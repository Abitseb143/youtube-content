"""FastAPI dependencies: DB session, current user from Clerk JWT."""

from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends, Header
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from faceless.api.errors import UnauthorizedError
from faceless.auth.clerk import ClerkClaims, InvalidToken, verify_clerk_token
from faceless.db.base import get_db_session
from faceless.db.models import User


async def db_session_dep() -> AsyncIterator[AsyncSession]:
    async for s in get_db_session():
        yield s


DbSession = Annotated[AsyncSession, Depends(db_session_dep)]


async def _claims_from_header(authorization: str | None) -> ClerkClaims:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise UnauthorizedError("Missing bearer token.")
    token = authorization.split(" ", 1)[1].strip()
    try:
        return await verify_clerk_token(token)
    except InvalidToken as e:
        raise UnauthorizedError(f"Invalid token: {e}") from e


async def current_user(
    db: DbSession,
    authorization: Annotated[str | None, Header()] = None,
) -> User:
    """Resolve (or auto-create) the User row for a verified Clerk session."""
    claims = await _claims_from_header(authorization)

    result = await db.execute(select(User).where(User.clerk_user_id == claims.sub))
    user = result.scalar_one_or_none()

    if user is None:
        user = User(
            clerk_user_id=claims.sub,
            email=claims.email or f"{claims.sub}@unknown.local",
            credit_balance=0,
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)

    return user


CurrentUser = Annotated[User, Depends(current_user)]
