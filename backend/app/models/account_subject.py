"""AccountSubject (会计科目) model — standard chart of accounts."""

import uuid
from datetime import datetime
from sqlalchemy import String, Integer, Boolean, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class AccountSubject(Base):
    __tablename__ = "account_subjects"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    client_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("clients.id"), nullable=True,
        comment="NULL=系统默认科目, 有值=该客户的定制科目"
    )

    code: Mapped[str] = mapped_column(String(20), nullable=False, comment="科目代码, e.g. 5602.04")
    name: Mapped[str] = mapped_column(String(100), nullable=False, comment="科目名称")
    full_name: Mapped[str | None] = mapped_column(
        String(200), nullable=True, comment="科目全称, e.g. 管理费用-办公费"
    )
    level: Mapped[int] = mapped_column(Integer, default=1, comment="科目级别: 1=一级, 2=二级, 3=三级")
    parent_code: Mapped[str | None] = mapped_column(String(20), nullable=True, comment="上级科目代码")
    category: Mapped[str] = mapped_column(
        String(20), nullable=False,
        comment="类别: 资产/负债/权益/成本/损益"
    )
    direction: Mapped[str] = mapped_column(
        String(10), default="debit", comment="默认方向: debit(借方) / credit(贷方)"
    )
    is_leaf: Mapped[bool] = mapped_column(Boolean, default=True, comment="是否末级科目(末级才能做账)")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())

    def __repr__(self) -> str:
        return f"<Subject {self.code} {self.name}>"
