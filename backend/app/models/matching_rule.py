"""MatchingRule (匹配规则) model — keyword-to-subject mapping for auto-categorization."""

import uuid
from datetime import datetime
from sqlalchemy import String, Integer, Boolean, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class MatchingRule(Base):
    __tablename__ = "matching_rules"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    client_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("clients.id"), nullable=True,
        comment="NULL=全局规则, 有值=该客户专属规则"
    )
    keywords: Mapped[str] = mapped_column(
        String(500), nullable=False,
        comment="关键词列表, 用 | 分隔, e.g. '餐饮|招待|宴请'"
    )
    subject_code: Mapped[str] = mapped_column(String(20), nullable=False, comment="目标科目代码")
    subject_name: Mapped[str | None] = mapped_column(String(100), nullable=True, comment="目标科目名称(冗余)")
    priority: Mapped[int] = mapped_column(Integer, default=0, comment="优先级, 越大越优先")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())

    def __repr__(self) -> str:
        return f"<Rule {self.keywords[:30]} -> {self.subject_code}>"
