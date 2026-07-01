"""Client (客户/账套) model — each client represents a company being served."""

import uuid
from datetime import datetime
from sqlalchemy import String, Boolean, Text, DateTime, Enum, func
from sqlalchemy.dialects.sqlite import CHAR as UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Client(Base):
    __tablename__ = "clients"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False, comment="企业名称")
    tax_id: Mapped[str | None] = mapped_column(String(20), nullable=True, comment="纳税人识别号")
    tax_type: Mapped[str] = mapped_column(
        String(20), default="small", comment="纳税人类型: general(一般纳税人) / small(小规模)"
    )
    contact_person: Mapped[str | None] = mapped_column(String(50), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, onupdate=func.now())

    # Relationships
    invoices = relationship("Invoice", back_populates="client", lazy="dynamic")
    journal_entries = relationship("JournalEntry", back_populates="client", lazy="dynamic")

    def __repr__(self) -> str:
        return f"<Client {self.name}>"
