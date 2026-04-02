from functools import wraps
import logging
from services.user_service import get_or_create_user, get_user_balance
from sqlalchemy.ext.asyncio import AsyncSession

# from database.session import async_session_maker # Assuming you have this defined
from database.session import asyncSessionMaker

# from services.user import get_or_create_user, get_user_balance
from services.billing_service import BillingManager, QuotaExceededError

logger = logging.getLogger(__name__)


def transactional_handler():
    def decorator(handler_func):
        @wraps(handler_func)
        async def wrapper(update, context, *args, **kwargs):
            # Extract basic user info from Telegram update
            tg_user = update.effective_user
            if not tg_user:
                return

            async with asyncSessionMaker() as session:
                try:
                    # 1. Get user (and apply gift if new)
                    user = await get_or_create_user(
                        session, tg_user.id, tg_user.username
                    )

                    # 2. Get current real database balance
                    current_bytes, current_requests = await get_user_balance(
                        session, user.id
                    )

                    # 3. Initialize the Billing Manager for this transaction
                    billing = BillingManager(
                        session, user, current_bytes, current_requests
                    )

                    # 4. Execute the handler, injecting the session, user, and billing manager
                    await handler_func(
                        update,
                        context,
                        session=session,
                        user=user,
                        billing=billing,
                        *args,
                        **kwargs,
                    )

                    # 5. IF EVERYTHING SUCCEEDS, COMMIT ALL CHANGES TO THE DB
                    await session.commit()

                except QuotaExceededError as e:
                    # If billing.charge() failed, rollback any partial changes (like a new user registration)
                    await session.rollback()
                    await update.effective_message.reply_text(f"🚫 {str(e)}")

                except Exception as e:
                    # IF ANYTHING FAILS (Network drop, file missing, code error), ROLLBACK!
                    # None of the billing.charge() calls will be saved to the database.
                    await session.rollback()
                    logger.error(
                        f"Error in handler {handler_func.__name__}: {e}", exc_info=True
                    )
                    await update.effective_message.reply_text(
                        "⚠️ An internal error occurred. You have not been charged."
                    )

        return wrapper

    return decorator
