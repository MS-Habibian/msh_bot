from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from database.models import User, UsageLog
from config import INITIAL_GIFT_BYTES, INITIAL_GIFT_REQUESTS


async def get_or_create_user(
    session: AsyncSession, telegram_id: int, username: str
) -> User:
    result = await session.execute(select(User).where(User.telegram_id == telegram_id))
    user = result.scalar_one_or_none()
    if not user:
        user = User(telegram_id=telegram_id, username=username)
        session.add(user)
        await session.flush()

        # Initial Gift Log
        gift_log = UsageLog(
            user_id=user.id,
            change_bytes=int(INITIAL_GIFT_BYTES),
            change_requests=int(INITIAL_GIFT_REQUESTS),
            io=1,  # 1 makes it an addition
            action="initial_registration_gift",
        )
        session.add(gift_log)
        
    return user


async def get_user_balance(session: AsyncSession, user_id: int) -> tuple[int, int]:
    """Calculates the current balance dynamically: SUM(change * io)"""
    result = await session.execute(
        select(
            func.coalesce(func.sum(UsageLog.change_bytes * UsageLog.io), 0),
            func.coalesce(func.sum(UsageLog.change_requests * UsageLog.io), 0),
        ).where(UsageLog.user_id == user_id)
    )
    row = result.first()
    if row:
        return int(row[0]), int(row[1])
    return 0, 0
