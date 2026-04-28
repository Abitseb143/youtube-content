import uuid

import pytest
from sqlalchemy import select

from faceless.db.models import User


@pytest.mark.asyncio
async def test_can_insert_and_select_user(db_session):
    user = User(
        id=uuid.uuid4(),
        email="alice@example.com",
        clerk_user_id="user_alice",
        credit_balance=0,
    )
    db_session.add(user)
    await db_session.flush()

    result = await db_session.execute(select(User).where(User.email == "alice@example.com"))
    found = result.scalar_one()
    assert found.id == user.id
    assert found.credit_balance == 0
