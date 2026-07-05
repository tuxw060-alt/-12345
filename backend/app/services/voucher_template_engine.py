"""
Voucher Template Engine — 规则匹配引擎 + 模板CRUD服务

核心工作流:
  上传发票/银行流水 → 识别票据类型 → 识别业务类型
  → 匹配分录模板 → 按模板生成凭证草稿 → 人工确认
"""

import re
import uuid
from datetime import date, datetime
from typing import Any

from loguru import logger
from sqlalchemy import func, select, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.voucher_template import DocumentType, VoucherTemplate, VoucherTemplateLine
from app.models.account_subject import AccountSubject
from app.schemas.journal_entry import EntryCreate, EntryLineCreate
from app.schemas.voucher_template import (
    AmountData, PreviewLine, GenerateDraftResponse,
    DocumentTypeCreate, DocumentTypeUpdate,
)


# ── Business Type Keywords ──────────────────────────────────────

BUSINESS_TYPE_KEYWORDS: list[tuple[str, list[str]]] = [
    ("手续费", ["手续费", "网银服务费", "账户管理费", "电子汇划费", "短信费", "工本费"]),
    ("利息收入", ["利息", "结息", "存款利息"]),
    ("利息支出", ["利息支出", "贷款利息", "融资利息"]),
    ("福利费", ["福利费", "团建", "聚餐"]),
    ("运杂费", ["运费", "物流", "快递", "运输"]),
    ("办公用品", ["办公用品", "文具", "耗材", "打印"]),
    ("业务招待费", ["餐饮", "招待", "宴请", "餐费"]),
    ("交通费", ["加油", "停车", "过路", "ETC", "打车", "交通"]),
    ("差旅费", ["差旅", "住宿", "酒店", "机票", "火车票"]),
    ("水电费", ["水电费", "电费", "水费", "物业"]),
    ("服务费", ["软件", "平台", "技术服务", "SaaS", "服务费", "咨询", "审计", "律师"]),
    ("租赁费", ["租金", "房租", "租赁"]),
    ("通讯费", ["通讯", "电话费", "网费", "宽带"]),
    ("维修费", ["维修", "修理", "维护"]),
    ("往来款", ["还款", "借款", "归还", "往来款", "往来"]),
    ("工资薪酬", ["工资", "薪酬", "代发", "奖金"]),
    ("税费缴纳", ["税", "税费", "国库", "缴税"]),
    ("社保公积金", ["社保", "养老", "医保", "公积金"]),
    ("采购商品", ["采购", "进货", "购买"]),
    ("销售收入", ["销售", "收入", "货款"]),
    ("银行收款", ["收款", "汇入", "转入"]),
    ("银行付款", ["付款", "汇出", "转出", "支付"]),
    ("劳务成本", ["劳务", "外包", "人工"]),
]


def identify_business_type(text: str | None) -> tuple[str | None, float]:
    """从文本中识别业务类型。返回(业务类型, 置信度)"""
    if not text:
        return None, 0.0
    text_lower = text.lower()
    for biz_type, keywords in BUSINESS_TYPE_KEYWORDS:
        for kw in keywords:
            if kw in text_lower:
                return biz_type, 0.8
    return None, 0.0


# Parent-level往来科目 — 不能直接用于凭证
PARENT_RECEIVABLE_CODES = {"1122", "1123", "1221", "2202", "2203", "2241"}


# ── DocumentType CRUD ───────────────────────────────────────────

async def list_document_types(
    db: AsyncSession, enabled_only: bool = False
) -> list[DocumentType]:
    stmt = select(DocumentType).order_by(DocumentType.code)
    if enabled_only:
        stmt = stmt.where(DocumentType.is_enabled == True)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_document_type(db: AsyncSession, dt_id: str) -> DocumentType | None:
    stmt = select(DocumentType).where(DocumentType.id == dt_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def get_document_type_by_code(db: AsyncSession, code: str) -> DocumentType | None:
    stmt = select(DocumentType).where(DocumentType.code == code)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def create_document_type(
    db: AsyncSession, data: DocumentTypeCreate
) -> DocumentType:
    dt = DocumentType(
        id=str(uuid.uuid4()),
        code=data.code,
        category=data.category,
        name=data.name,
        company_id=data.company_id,
        is_system=data.is_system,
        is_enabled=data.is_enabled,
    )
    db.add(dt)
    await db.flush()
    return dt


async def update_document_type(
    db: AsyncSession, dt: DocumentType, data: DocumentTypeUpdate
) -> DocumentType:
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(dt, field, value)
    dt.updated_at = datetime.now()
    await db.flush()
    return dt


async def delete_document_type(db: AsyncSession, dt: DocumentType) -> None:
    """删除单据类别（检查是否被模板引用）"""
    # Check if any template references this document type
    stmt = select(func.count()).select_from(VoucherTemplate).where(
        VoucherTemplate.document_type_id == dt.id
    )
    result = await db.execute(stmt)
    count = result.scalar() or 0
    if count > 0:
        raise ValueError(f"该单据类别被 {count} 个分录模板引用，无法删除。请先删除或修改相关模板。")
    await db.delete(dt)
    await db.flush()


async def restore_preset_document_types(db: AsyncSession) -> list[DocumentType]:
    """恢复预置单据类型：只补齐缺失的，不覆盖用户自定义"""
    presets = [
        ("1001", "销售发票", "销售增值税发票"),
        ("2001", "采购发票", "采购增值税普通发票"),
        ("2002", "采购发票", "采购增值税专用发票"),
        ("4001", "费用票据", "费用票据"),
        ("3001", "银行票据", "银行票据"),
    ]
    restored = []
    for code, category, name in presets:
        existing = await get_document_type_by_code(db, code)
        if existing:
            continue
        dt = DocumentType(
            id=str(uuid.uuid4()),
            code=code, category=category, name=name,
            is_system=True, is_enabled=True,
        )
        db.add(dt)
        restored.append(dt)
    if restored:
        await db.flush()
    return restored


# ── VoucherTemplate CRUD ────────────────────────────────────────

async def list_templates(
    db: AsyncSession, enabled_only: bool = False
) -> list[VoucherTemplate]:
    stmt = (
        select(VoucherTemplate)
        .options(selectinload(VoucherTemplate.lines))
        .order_by(VoucherTemplate.priority.desc(), VoucherTemplate.document_name)
    )
    if enabled_only:
        stmt = stmt.where(VoucherTemplate.is_enabled == True)
    result = await db.execute(stmt)
    return list(result.unique().scalars().all())


async def get_template(db: AsyncSession, tpl_id: str) -> VoucherTemplate | None:
    stmt = (
        select(VoucherTemplate)
        .options(selectinload(VoucherTemplate.lines))
        .where(VoucherTemplate.id == tpl_id)
    )
    result = await db.execute(stmt)
    return result.unique().scalar_one_or_none()


async def create_template(
    db: AsyncSession,
    document_name: str,
    settlement_method: str,
    business_type: str,
    summary_template: str,
    lines_data: list[dict[str, Any]],
    document_type_id: str | None = None,
    company_id: str | None = None,
    priority: int = 0,
) -> VoucherTemplate:
    tpl = VoucherTemplate(
        id=str(uuid.uuid4()),
        document_type_id=document_type_id,
        document_name=document_name,
        settlement_method=settlement_method,
        business_type=business_type,
        summary_template=summary_template,
        company_id=company_id,
        priority=priority,
        created_from="manual",
    )
    db.add(tpl)
    for ld in lines_data:
        db.add(VoucherTemplateLine(
            id=str(uuid.uuid4()),
            template_id=tpl.id,
            line_no=ld["line_no"],
            debit_credit=ld["debit_credit"],
            account_code=ld["account_code"],
            account_name=ld.get("account_name", ""),
            account_full_name=ld.get("account_full_name"),
            parent_account_code=ld.get("parent_account_code"),
            amount_source=ld.get("amount_source", "totalAmount"),
            require_sub_account=ld.get("require_sub_account", False),
            sub_account_match_mode=ld.get("sub_account_match_mode", "none"),
            allow_manual_edit=ld.get("allow_manual_edit", True),
        ))
    await db.flush()
    return tpl


async def update_template(
    db: AsyncSession, tpl: VoucherTemplate, data: dict[str, Any]
) -> VoucherTemplate:
    """Update template header + replace lines"""
    for field in ("document_name", "settlement_method", "business_type",
                  "summary_template", "is_enabled", "priority", "document_type_id"):
        if field in data and data[field] is not None:
            setattr(tpl, field, data[field])
    tpl.updated_at = datetime.now()

    if "lines" in data and data["lines"] is not None:
        # Delete old lines
        for line in list(tpl.lines):
            await db.delete(line)
        # Add new lines
        for ld in data["lines"]:
            db.add(VoucherTemplateLine(
                id=str(uuid.uuid4()),
                template_id=tpl.id,
                line_no=ld.get("line_no", 1),
                debit_credit=ld.get("debit_credit", "debit"),
                account_code=ld.get("account_code", ""),
                account_name=ld.get("account_name", ""),
                account_full_name=ld.get("account_full_name"),
                parent_account_code=ld.get("parent_account_code"),
                amount_source=ld.get("amount_source", "totalAmount"),
                require_sub_account=ld.get("require_sub_account", False),
                sub_account_match_mode=ld.get("sub_account_match_mode", "none"),
                allow_manual_edit=ld.get("allow_manual_edit", True),
            ))
    await db.flush()
    return tpl


async def copy_template(db: AsyncSession, tpl: VoucherTemplate) -> VoucherTemplate:
    """复制模板（创建副本，可独立编辑）"""
    new_tpl = VoucherTemplate(
        id=str(uuid.uuid4()),
        document_type_id=tpl.document_type_id,
        document_name=tpl.document_name,
        settlement_method=tpl.settlement_method,
        business_type=tpl.business_type,
        summary_template=tpl.summary_template,
        company_id=tpl.company_id,
        priority=tpl.priority,
        created_from="copy",
    )
    db.add(new_tpl)
    for line in tpl.lines:
        db.add(VoucherTemplateLine(
            id=str(uuid.uuid4()),
            template_id=new_tpl.id,
            line_no=line.line_no,
            debit_credit=line.debit_credit,
            account_code=line.account_code,
            account_name=line.account_name,
            account_full_name=line.account_full_name,
            parent_account_code=line.parent_account_code,
            amount_source=line.amount_source,
            require_sub_account=line.require_sub_account,
            sub_account_match_mode=line.sub_account_match_mode,
            allow_manual_edit=line.allow_manual_edit,
        ))
    await db.flush()
    return new_tpl


async def toggle_template(db: AsyncSession, tpl: VoucherTemplate) -> VoucherTemplate:
    tpl.is_enabled = not tpl.is_enabled
    tpl.updated_at = datetime.now()
    await db.flush()
    return tpl


async def delete_template(db: AsyncSession, tpl: VoucherTemplate) -> None:
    await db.delete(tpl)
    await db.flush()


# ── Matching Engine ────────────────────────────────────────────

async def match_templates(
    db: AsyncSession,
    document_type_id: str | None = None,
    document_name: str | None = None,
    settlement_method: str | None = None,
    business_type: str | None = None,
) -> list[VoucherTemplate]:
    """按条件匹配分录模板，优先级排序"""
    stmt = (
        select(VoucherTemplate)
        .options(selectinload(VoucherTemplate.lines))
        .where(VoucherTemplate.is_enabled == True)
    )
    if document_type_id:
        stmt = stmt.where(VoucherTemplate.document_type_id == document_type_id)
    if document_name:
        stmt = stmt.where(VoucherTemplate.document_name == document_name)
    if settlement_method:
        stmt = stmt.where(VoucherTemplate.settlement_method == settlement_method)
    if business_type:
        stmt = stmt.where(VoucherTemplate.business_type == business_type)
    else:
        # Without business_type, match any — still ordered by priority
        pass

    stmt = stmt.order_by(VoucherTemplate.priority.desc())
    result = await db.execute(stmt)
    return list(result.unique().scalars().all())


# ── Sub-Account Matching ────────────────────────────────────────

async def match_sub_account(
    db: AsyncSession,
    parent_code: str,
    counterparty_name: str | None,
) -> AccountSubject | None:
    """在往来科目子级中搜索匹配对方名称的明细科目"""
    if not counterparty_name:
        return None

    # Find all active leaf subjects under the parent code
    stmt = select(AccountSubject).where(
        AccountSubject.is_active == True,
        AccountSubject.is_leaf == True,
        AccountSubject.parent_code == parent_code,
    )
    result = await db.execute(stmt)
    candidates = result.scalars().all()

    # Exact match on name or full_name
    for sub in candidates:
        name_lower = sub.name.lower() if sub.name else ""
        full_lower = sub.full_name.lower() if sub.full_name else ""
        cp_lower = counterparty_name.lower()
        if cp_lower in name_lower or cp_lower in full_lower:
            return sub

    # Try fuzzy: remove common suffixes and try again
    cp_clean = re.sub(r"(公司|有限公司|有限责任|集团|厂|店|中心|部)$", "",
                      counterparty_name.strip())
    if cp_clean and cp_clean != counterparty_name.strip():
        for sub in candidates:
            name_lower = sub.name.lower() if sub.name else ""
            full_lower = sub.full_name.lower() if sub.full_name else ""
            if cp_clean.lower() in name_lower or cp_clean.lower() in full_lower:
                return sub

    return None


async def find_sub_account_for_counterparty(
    db: AsyncSession,
    counterparty_name: str | None,
) -> tuple[AccountSubject | None, str | None]:
    """在 1122/1123/1221/2202/2203/2241 子级中搜索匹配对方名称的明细

    Returns: (matched_subject, parent_scope_code) or (None, None)
    """
    if not counterparty_name:
        return None, None

    for parent_code in PARENT_RECEIVABLE_CODES:
        sub = await match_sub_account(db, parent_code, counterparty_name)
        if sub:
            return sub, parent_code

    return None, None


# ── Draft Generation Engine ─────────────────────────────────────

async def generate_draft_from_template(
    db: AsyncSession,
    template: VoucherTemplate,
    amounts: AmountData,
    client_id: str,
    voucher_date: date | None = None,
    summary_vars: dict[str, str] | None = None,
    counterparty_name: str | None = None,
    source_invoice_id: str | None = None,
) -> GenerateDraftResponse:
    """根据模板 + 金额数据生成凭证草稿预览

    对 require_sub_account=True 的行，自动在往来科目子级中匹配对方名称。
    匹配不到 → 标记 is_pending=True，科目代码设为 "PENDING"。
    """
    summary_vars = summary_vars or {}

    # Resolve amounts
    amt_map = {
        "totalAmount": amounts.total_amount,
        "amount": amounts.amount,
        "taxAmount": amounts.tax_amount,
        "incomeAmount": amounts.income_amount,
        "expenseAmount": amounts.expense_amount,
        "balance": amounts.balance,
        "manual": 0.0,
        "zero": 0.0,
    }

    preview_lines: list[PreviewLine] = []
    warnings: list[str] = []
    errors: list[str] = []
    line_no = 1

    for tpl_line in template.lines:
        # Resolve amount
        amount = amt_map.get(tpl_line.amount_source, 0.0)
        if amount <= 0 and tpl_line.amount_source != "zero":
            amount = 0.0

        account_code = tpl_line.account_code
        account_name = tpl_line.account_name
        matched_sub_code: str | None = None
        matched_sub_name: str | None = None
        is_pending = False
        warning: str | None = None

        # Sub-account matching for receivable/payable lines
        if tpl_line.require_sub_account and counterparty_name:
            sub, parent_scope = await find_sub_account_for_counterparty(
                db, counterparty_name
            )
            if sub:
                account_code = sub.code
                account_name = sub.full_name or sub.name
                matched_sub_code = sub.code
                matched_sub_name = sub.full_name or sub.name
                # Verify sub is under expected parent
                if parent_scope and sub.parent_code != parent_scope:
                    logger.info(
                        f"Matched {sub.code} under {sub.parent_code}, "
                        f"template expects {parent_scope}"
                    )
            else:
                is_pending = True
                account_code = "PENDING"
                account_name = f"待选择科目（{tpl_line.account_name}）"
                warning = (
                    f"第{line_no}行：未匹配到「{counterparty_name}」的往来明细科目，"
                    f"请手动选择 {tpl_line.account_code} 的子级科目"
                )
                warnings.append(warning)
        elif tpl_line.require_sub_account and not counterparty_name:
            is_pending = True
            account_code = "PENDING"
            account_name = f"待选择科目（{tpl_line.account_name}）"
            warning = f"第{line_no}行：缺少对方名称，无法匹配往来明细"
            warnings.append(warning)

        # Check parent-level restriction
        if (not is_pending
                and account_code in PARENT_RECEIVABLE_CODES
                and tpl_line.require_sub_account):
            is_pending = True
            account_code = "PENDING"
            account_name = f"待选择科目（{tpl_line.account_name}）"
            warning = f"第{line_no}行：{tpl_line.account_code} 为父级往来科目，必须选择明细"
            warnings.append(warning)

        preview_lines.append(PreviewLine(
            line_no=line_no,
            debit_credit=tpl_line.debit_credit,
            account_code=account_code,
            account_name=account_name,
            amount_source=tpl_line.amount_source,
            estimated_amount=round(amount, 2),
            require_sub_account=tpl_line.require_sub_account,
            sub_account_match_mode=tpl_line.sub_account_match_mode,
            matched_sub_code=matched_sub_code,
            matched_sub_name=matched_sub_name,
            is_pending=is_pending,
            warning=warning,
        ))
        line_no += 1

    return GenerateDraftResponse(
        entry_id=None,
        status="draft",
        preview_lines=preview_lines,
        warnings=warnings,
        errors=errors,
    )


async def create_draft_entry(
    db: AsyncSession,
    template: VoucherTemplate,
    amounts: AmountData,
    client_id: str,
    voucher_date: date | None = None,
    summary_vars: dict[str, str] | None = None,
    counterparty_name: str | None = None,
    source_invoice_id: str | None = None,
    manual_overrides: dict[int, dict[str, str]] | None = None,
) -> EntryCreate:
    """根据模板生成 EntryCreate（可直接用于创建 JournalEntry）

    manual_overrides: {line_no: {account_code, account_name}} 用户手动选择的科目覆盖
    """
    summary_vars = summary_vars or {}
    manual_overrides = manual_overrides or {}

    # Build summary
    summary = template.summary_template
    for var, val in summary_vars.items():
        summary = summary.replace(f"{{{var}}}", str(val))
    if counterparty_name and "{counterpartyName}" in summary:
        summary = summary.replace("{counterpartyName}", counterparty_name)

    amt_map = {
        "totalAmount": amounts.total_amount,
        "amount": amounts.amount,
        "taxAmount": amounts.tax_amount,
        "incomeAmount": amounts.income_amount,
        "expenseAmount": amounts.expense_amount,
        "balance": amounts.balance,
        "manual": 0.0,
        "zero": 0.0,
    }

    lines: list[EntryLineCreate] = []
    seq = 1

    for tpl_line in template.lines:
        amount = amt_map.get(tpl_line.amount_source, 0.0)
        if amount <= 0 and tpl_line.amount_source != "zero":
            amount = 0.0

        # Check for manual override
        override = manual_overrides.get(tpl_line.line_no)
        if override:
            account_code = override.get("account_code", tpl_line.account_code)
            account_name = override.get("account_name", tpl_line.account_name)
            manual_override = True
        else:
            account_code = tpl_line.account_code
            account_name = tpl_line.account_name
            manual_override = False

            # Sub-account matching
            if tpl_line.require_sub_account and counterparty_name:
                sub, _ = await find_sub_account_for_counterparty(db, counterparty_name)
                if sub:
                    account_code = sub.code
                    account_name = sub.full_name or sub.name
                else:
                    account_code = "PENDING"
                    account_name = f"待选择科目（{tpl_line.account_name}）"

        lines.append(EntryLineCreate(
            line_number=seq,
            account_code=account_code,
            account_name=account_name,
            direction=tpl_line.debit_credit,
            amount=round(amount, 2),
            summary_detail=(
                f"{counterparty_name}" if counterparty_name and tpl_line.require_sub_account
                else tpl_line.account_name
            ),
        ))
        seq += 1

    return EntryCreate(
        client_id=client_id,
        source_invoice_id=source_invoice_id,
        voucher_date=voucher_date or date.today(),
        voucher_type="记",
        summary=summary[:500],
        lines=lines,
    )
