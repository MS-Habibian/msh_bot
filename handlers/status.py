from telegram import Update
from telegram.ext import ContextTypes
from database.models import User
from services.billing_service import BillingManager
from services.user_service import get_user_balance
from decorators.transactional_decorator import transactional_handler
from sqlalchemy.ext.asyncio import AsyncSession


@transactional_handler()
async def status_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    session: AsyncSession,
    user: User,
    billing: BillingManager,
):
    remaining_byte, remaining_req = await get_user_balance(session, user_id=user.id)
    await update.message.reply_text(
        f"{update.effective_user.first_name} عزیز\n"
        f"وضعیت اعتبار شما:\n"
        f"📦 حجم باقی‌مانده: {(remaining_byte / (1024 * 1024)):.2f} MB\n"
        f"🔍 تعداد درخواست باقی‌مانده: {remaining_req}"
    )
