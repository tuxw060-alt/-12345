"""Invoice (发票) model — stores uploaded invoice images and AI-extracted fields."""

import uuid
from datetime import date, datetime
from sqlalchemy import String, Date, Numeric, Boolean, Text, DateTime, ForeignKey, JSON, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Invoice(Base):
    __tablename__ = "invoices"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    client_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("clients.id"), nullable=True, comment="所属客户"
    )

    # File info
    image_path: Mapped[str] = mapped_column(String(500), nullable=False, comment="图片存储路径")
    image_filename: Mapped[str] = mapped_column(String(200), nullable=False, comment="原始文件名")

    # --- AI-extracted fields ---
    invoice_type: Mapped[str | None] = mapped_column(
        String(50), nullable=True, comment="发票类型: 增值税专用发票/增值税普通发票/电子普通发票/全电发票/定额发票"
    )
    invoice_code: Mapped[str | None] = mapped_column(String(20), nullable=True, comment="发票代码")
    invoice_number: Mapped[str | None] = mapped_column(String(20), nullable=True, comment="发票号码")
    invoice_date: Mapped[date | None] = mapped_column(Date, nullable=True, comment="开票日期")
    total_amount: Mapped[float | None] = mapped_column(
        Numeric(14, 2), nullable=True, comment="价税合计(元)"
    )
    amount: Mapped[float | None] = mapped_column(
        Numeric(14, 2), nullable=True, comment="不含税金额(元)"
    )
    tax_amount: Mapped[float | None] = mapped_column(
        Numeric(14, 2), nullable=True, comment="税额(元)"
    )
    vendor_name: Mapped[str | None] = mapped_column(String(200), nullable=True, comment="销售方名称")
    vendor_tax_id: Mapped[str | None] = mapped_column(String(20), nullable=True, comment="销售方税号")
    buyer_name: Mapped[str | None] = mapped_column(String(200), nullable=True, comment="购买方名称")
    buyer_tax_id: Mapped[str | None] = mapped_column(String(20), nullable=True, comment="购买方税号")
    item_name: Mapped[str | None] = mapped_column(
        String(500), nullable=True, comment="货物/服务名称"
    )
    remarks: Mapped[str | None] = mapped_column(String(500), nullable=True, comment="备注")

    # AI suggestion
    suggested_subject_code: Mapped[str | None] = mapped_column(
        String(20), nullable=True, comment="AI推荐的科目代码"
    )
    suggested_subject_name: Mapped[str | None] = mapped_column(
        String(100), nullable=True, comment="AI推荐的科目名称"
    )
    subject_confidence: Mapped[float | None] = mapped_column(
        Numeric(5, 2), nullable=True, comment="科目匹配置信度 0-100"
    )

    # Processing status
    ocr_status: Mapped[str] = mapped_column(
        String(20), default="pending", comment="pending / done / failed"
    )
    ocr_confidence: Mapped[float | None] = mapped_column(
        Numeric(5, 2), nullable=True, comment="整体OCR置信度 0-100"
    )
    ocr_error_msg: Mapped[str | None] = mapped_column(String(500), nullable=True)
    raw_ai_response: Mapped[str | None] = mapped_column(JSON, nullable=True, comment="AI原始返回JSON")
    human_verified: Mapped[bool] = mapped_column(Boolean, default=False, comment="是否人工确认过")

    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())

    # Relationships
    client = relationship("Client", back_populates="invoices")

    def __repr__(self) -> str:
        return f"<Invoice {self.invoice_number or self.id[:8]}>"
