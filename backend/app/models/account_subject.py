"""Account subject model."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class AccountSubject(Base):
    __tablename__ = "account_subjects"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    client_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("clients.id"),
        nullable=True,
        comment="NULL means system default subject; otherwise client-specific.",
    )

    code: Mapped[str] = mapped_column(String(20), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    full_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    level: Mapped[int] = mapped_column(Integer, default=1)
    parent_code: Mapped[str | None] = mapped_column(String(20), nullable=True)
    parent_account_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    category: Mapped[str] = mapped_column(String(20), nullable=False)
    direction: Mapped[str] = mapped_column(String(10), default="debit")
    is_leaf: Mapped[bool] = mapped_column(Boolean, default=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_from: Mapped[str | None] = mapped_column(String(40), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, onupdate=func.now())

    def __repr__(self) -> str:
        return f"<Subject {self.code} {self.name}>"
