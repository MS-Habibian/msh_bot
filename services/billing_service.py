from sqlalchemy.ext.asyncio import AsyncSession
from database.models import User, UsageLog

class QuotaExceededError(Exception):
    pass

class BillingManager:
    def __init__(self, session: AsyncSession, user: User, current_bytes: int, current_requests: int):
        self.session = session
        self.user = user
        self.current_bytes = current_bytes
        self.current_requests = current_requests

    def charge(self, cost_bytes: int = 0, cost_requests: int = 0, action: str = "unknown_charge"):
        if self.current_bytes < cost_bytes or self.current_requests < cost_requests:
            raise QuotaExceededError(
                f"Insufficient quota. Needed: {cost_bytes} bytes, {cost_requests} reqs. "
                f"Have: {self.current_bytes} bytes, {self.current_requests} reqs."
            )

        # Update the in-memory balance for subsequent charges in the same request
        self.current_bytes -= cost_bytes
        self.current_requests -= cost_requests

        # Create the log record
        log = UsageLog(
            user_id=self.user.id,
            change_bytes=cost_bytes,       
            change_requests=cost_requests, 
            io=-1, # -1 makes it a deduction
            action=action
        )
        
        self.session.add(log)