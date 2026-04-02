from datetime import datetime
from sqlalchemy import (
    Integer,
    BigInteger,
    String,
    DateTime,
    ForeignKey,
)
from sqlalchemy.orm import declarative_base, Mapped, mapped_column, relationship


Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(
        BigInteger, unique=True, index=True, nullable=False
    )
    username: Mapped[str] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationship to logs
    usage_logs: Mapped[list["UsageLog"]] = relationship(
        "UsageLog", back_populates="user"
    )


class UsageLog(Base):
    __tablename__ = "usage_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), index=True, nullable=False
    )

    # Absolute amounts (always positive)
    change_bytes: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    change_requests: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Direction: 1 for Add/Gift, -1 for Deduct/Charge
    io: Mapped[int] = mapped_column(Integer, nullable=False)

    action: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user: Mapped["User"] = relationship("User", back_populates="usage_logs")
