"""Document voucher template CRUD, seeding, matching, and draft generation."""

import re
import uuid
from dataclasses import dataclass
from datetime import date
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.document_voucher import (
    DocumentType,
    DocumentVoucherTemplate,
    DocumentVoucherTemplateLine,
)
from app.schemas.document_voucher import (
    AMOUNT_SOURCES,
    DEBIT_CREDITS,
    SETTLEMENT_METHODS,
    SUB_ACCOUNT_MATCH_MODES,
    DocumentTypeCreate,
    DocumentTypeUpdate,
    TemplateLineCreate,
    TemplatePreviewRequest,
    TemplateRecommendation,
    VoucherTemplateCreate,
    VoucherTemplateUpdate,
)
from app.schemas.journal_entry import EntryCreate, EntryLineCreate
from app.services.subject_service import (
    CURRENT_PARENT_CODES,
    find_legacy_sub_account_by_counterparty,
    legacy_subject_line_fields,
)


MATCHED_CURRENT_ACCOUNT = "__MATCHED_CURRENT__"
PENDING_ACCOUNT_CODE = "PENDING"
PENDING_ACCOUNT_NAME = "待选择科目"
BANK_ACCOUNT_CODE = "100201"
BANK_ACCOUNT_NAME = "银行存款_基本户"
BANK_ACCOUNT_FULL_NAME = "银行存款_基本户"
BANK_ACCOUNT_AUX_NAME = "基本户"


DEFAULT_DOCUMENT_TYPES = [
    ("1001", "销售发票", "销售增值税发票"),
    ("2001", "采购发票", "采购增值税普通发票"),
    ("2002", "采购发票", "采购增值税专用发票"),
    ("4001", "费用票据", "费用票据"),
    ("3001", "银行票据", "银行票据"),
]


@dataclass(frozen=True)
class DefaultLine:
    debit_credit: str
    account_code: str
    account_name: str
    amount_source: str
    require_sub_account: bool = False
    match_mode: str = "none"
    account_full_name: str | None = None
    parent_account_code: str | None = None


DEFAULT_TEMPLATES = [
    ("销售增值税发票", "往来结算", "销售收入", "销售收入", 10, [
        DefaultLine("debit", "1122", "应收账款", "totalAmount", True, "customer"),
        DefaultLine("credit", "5001", "主营业务收入", "amount"),
        DefaultLine("credit", "22210102", "应交税费_应交增值税_销项税额", "taxAmount"),
    ]),
    ("采购增值税专用发票", "往来结算", "采购商品", "采购商品", 20, [
        DefaultLine("debit", "1405", "库存商品", "amount"),
        DefaultLine("debit", "22210101", "应交税费_应交增值税_进项税额", "taxAmount"),
        DefaultLine("credit", "2202", "应付账款", "totalAmount", True, "supplier"),
    ]),
    ("采购增值税普通发票", "往来结算", "采购商品", "采购商品", 30, [
        DefaultLine("debit", "1405", "库存商品", "totalAmount"),
        DefaultLine("credit", "2202", "应付账款", "totalAmount", True, "supplier"),
    ]),
    ("费用票据", "往来结算", "福利费", "福利费", 40, [
        DefaultLine("debit", "560201", "管理费用_福利费", "totalAmount"),
        DefaultLine("credit", "2202", "应付账款", "totalAmount", True, "supplier"),
    ]),
    ("费用票据", "往来结算", "运杂费", "运杂费", 41, [
        DefaultLine("debit", "560202", "管理费用_运杂费", "totalAmount"),
        DefaultLine("credit", "2202", "应付账款", "totalAmount", True, "supplier"),
    ]),
    ("费用票据", "往来结算", "服务费", "服务费", 42, [
        DefaultLine("debit", "560203", "管理费用_服务费", "totalAmount"),
        DefaultLine("credit", "2202", "应付账款", "totalAmount", True, "supplier"),
    ]),
    ("费用票据", "现金", "办公用品", "办公用品", 43, [
        DefaultLine("debit", "560204", "管理费用_办公用品费", "totalAmount"),
        DefaultLine("credit", "1001", "库存现金", "totalAmount"),
    ]),
    ("银行票据", "银行", "银行收款", "银行收款", 50, [
        DefaultLine("debit", BANK_ACCOUNT_CODE, BANK_ACCOUNT_NAME, "incomeAmount", False, "bank_account", BANK_ACCOUNT_FULL_NAME),
        DefaultLine("credit", MATCHED_CURRENT_ACCOUNT, PENDING_ACCOUNT_NAME, "incomeAmount", True, "counterparty"),
    ]),
    ("银行票据", "银行", "银行付款", "银行付款", 51, [
        DefaultLine("debit", MATCHED_CURRENT_ACCOUNT, PENDING_ACCOUNT_NAME, "expenseAmount", True, "counterparty"),
        DefaultLine("credit", BANK_ACCOUNT_CODE, BANK_ACCOUNT_NAME, "expenseAmount", False, "bank_account", BANK_ACCOUNT_FULL_NAME),
    ]),
    ("银行票据", "银行", "手续费", "手续费", 52, [
        DefaultLine("debit", "560301", "财务费用_手续费", "expenseAmount"),
        DefaultLine("credit", BANK_ACCOUNT_CODE, BANK_ACCOUNT_NAME, "expenseAmount", False, "bank_account", BANK_ACCOUNT_FULL_NAME),
    ]),
    ("银行票据", "银行", "利息收入", "利息", 53, [
        DefaultLine("debit", BANK_ACCOUNT_CODE, BANK_ACCOUNT_NAME, "incomeAmount", False, "bank_account", BANK_ACCOUNT_FULL_NAME),
        DefaultLine("credit", "560302", "财务费用_利息收入", "incomeAmount"),
    ]),
]


def _scope(company_id: str | None):
    return DocumentType.company_id == company_id if company_id else DocumentType.company_id == None


async def seed_default_document_voucher_config(db: AsyncSession) -> None:
    existing_by_name: dict[str, DocumentType] = {}
    result = await db.execute(select(DocumentType).where(DocumentType.company_id == None))
    for item in result.scalars().all():
        existing_by_name[item.name] = item

    for code, category, name in DEFAULT_DOCUMENT_TYPES:
        doc = existing_by_name.get(name)
        if doc:
            doc.code = doc.code or code
            doc.category = doc.category or category
            doc.is_system = True
            doc.is_enabled = True
            continue
        doc = DocumentType(
            id=str(uuid.uuid4()),
            company_id=None,
            code=code,
            category=category,
            name=name,
            is_system=True,
            is_enabled=True,
        )
        db.add(doc)
        existing_by_name[name] = doc
    await db.flush()

    existing_templates = await db.execute(
        select(DocumentVoucherTemplate).where(DocumentVoucherTemplate.company_id == None)
    )
    existing_keys = {
        (t.document_name, t.settlement_method, t.business_type)
        for t in existing_templates.scalars().all()
    }
    for document_name, settlement, business, summary, priority, lines in DEFAULT_TEMPLATES:
        key = (document_name, settlement, business)
        if key in existing_keys:
            continue
        doc = existing_by_name.get(document_name)
        if not doc:
            continue
        tpl = DocumentVoucherTemplate(
            id=str(uuid.uuid4()),
            company_id=None,
            document_type_id=doc.id,
            document_name=document_name,
            settlement_method=settlement,
            business_type=business,
            summary_template=summary,
            is_enabled=True,
            priority=priority,
            created_from="system",
        )
        db.add(tpl)
        await db.flush()
        for index, line in enumerate(lines, start=1):
            db.add(
                DocumentVoucherTemplateLine(
                    id=str(uuid.uuid4()),
                    template_id=tpl.id,
                    line_no=index,
                    debit_credit=line.debit_credit,
                    account_code=line.account_code,
                    account_name=line.account_name,
                    account_full_name=line.account_full_name or line.account_name,
                    parent_account_code=line.parent_account_code,
                    amount_source=line.amount_source,
                    require_sub_account=line.require_sub_account,
                    sub_account_match_mode=line.match_mode,
                    allow_manual_edit=True,
                )
            )
    await db.flush()


async def list_document_types(db: AsyncSession, company_id: str | None = None) -> tuple[list[DocumentType], int]:
    stmt = select(DocumentType).where(
        (DocumentType.company_id == None) | (DocumentType.company_id == company_id)
        if company_id else DocumentType.company_id == None
    )
    total = (await db.execute(select(func.count()).select_from(stmt.subquery()))).scalar() or 0
    result = await db.execute(stmt.order_by(DocumentType.code))
    return list(result.scalars().all()), total


async def create_document_type(db: AsyncSession, data: DocumentTypeCreate) -> DocumentType:
    await _assert_document_type_unique(db, code=data.code, name=data.name, company_id=data.company_id)
    doc = DocumentType(id=str(uuid.uuid4()), is_system=False, **data.model_dump())
    db.add(doc)
    await db.flush()
    return doc


async def update_document_type(db: AsyncSession, doc: DocumentType, data: DocumentTypeUpdate) -> DocumentType:
    values = data.model_dump(exclude_unset=True)
    if "code" in values or "name" in values:
        await _assert_document_type_unique(
            db,
            code=values.get("code", doc.code),
            name=values.get("name", doc.name),
            company_id=doc.company_id,
            exclude_id=doc.id,
        )
    for field, value in values.items():
        setattr(doc, field, value)
    await db.flush()
    return doc


async def delete_document_type(db: AsyncSession, doc: DocumentType) -> None:
    if doc.is_system:
        doc.is_enabled = False
        await db.flush()
        return
    used = (await db.execute(
        select(func.count()).select_from(DocumentVoucherTemplate).where(
            DocumentVoucherTemplate.document_type_id == doc.id
        )
    )).scalar() or 0
    if used:
        raise ValueError("该票据已被分录模板引用，请先停用或删除相关模板")
    await db.delete(doc)
    await db.flush()


async def restore_default_document_types(db: AsyncSession) -> None:
    await seed_default_document_voucher_config(db)


async def _assert_document_type_unique(
    db: AsyncSession,
    *,
    code: str,
    name: str,
    company_id: str | None,
    exclude_id: str | None = None,
) -> None:
    stmt = select(DocumentType).where(_scope(company_id), (DocumentType.code == code) | (DocumentType.name == name))
    if exclude_id:
        stmt = stmt.where(DocumentType.id != exclude_id)
    existing = (await db.execute(stmt)).scalar_one_or_none()
    if existing:
        raise ValueError("票据编码或票据名称已存在")


async def get_document_type(db: AsyncSession, doc_id: str) -> DocumentType | None:
    return await db.get(DocumentType, doc_id)


def _validate_line(line: TemplateLineCreate) -> None:
    if line.debit_credit not in DEBIT_CREDITS:
        raise ValueError("借贷方向只能是 debit 或 credit")
    if line.amount_source not in AMOUNT_SOURCES:
        raise ValueError(f"不支持的金额来源: {line.amount_source}")
    if line.sub_account_match_mode not in SUB_ACCOUNT_MATCH_MODES:
        raise ValueError(f"不支持的明细匹配方式: {line.sub_account_match_mode}")


async def list_templates(
    db: AsyncSession,
    *,
    company_id: str | None = None,
    document_type_id: str | None = None,
    enabled_only: bool = False,
) -> tuple[list[DocumentVoucherTemplate], int]:
    stmt = select(DocumentVoucherTemplate).options(selectinload(DocumentVoucherTemplate.lines))
    if company_id:
        stmt = stmt.where((DocumentVoucherTemplate.company_id == None) | (DocumentVoucherTemplate.company_id == company_id))
    else:
        stmt = stmt.where(DocumentVoucherTemplate.company_id == None)
    if document_type_id:
        stmt = stmt.where(DocumentVoucherTemplate.document_type_id == document_type_id)
    if enabled_only:
        stmt = stmt.where(DocumentVoucherTemplate.is_enabled == True)
    total = (await db.execute(select(func.count()).select_from(stmt.subquery()))).scalar() or 0
    result = await db.execute(stmt.order_by(DocumentVoucherTemplate.priority, DocumentVoucherTemplate.created_at))
    return list(result.unique().scalars().all()), total


async def get_template(db: AsyncSession, template_id: str) -> DocumentVoucherTemplate | None:
    result = await db.execute(
        select(DocumentVoucherTemplate)
        .options(selectinload(DocumentVoucherTemplate.lines))
        .where(DocumentVoucherTemplate.id == template_id)
    )
    return result.unique().scalar_one_or_none()


async def create_template(db: AsyncSession, data: VoucherTemplateCreate) -> DocumentVoucherTemplate:
    _validate_template_payload(data)
    doc = await get_document_type(db, data.document_type_id)
    if not doc:
        raise ValueError("票据类型不存在")
    tpl = DocumentVoucherTemplate(id=str(uuid.uuid4()), **data.model_dump(exclude={"lines"}))
    db.add(tpl)
    await db.flush()
    for line in sorted(data.lines, key=lambda item: item.line_no):
        db.add(DocumentVoucherTemplateLine(id=str(uuid.uuid4()), template_id=tpl.id, **line.model_dump()))
    await db.flush()
    return await get_template(db, tpl.id)


async def update_template(
    db: AsyncSession,
    tpl: DocumentVoucherTemplate,
    data: VoucherTemplateUpdate,
) -> DocumentVoucherTemplate:
    values = data.model_dump(exclude_unset=True, exclude={"lines"})
    if "settlement_method" in values and values["settlement_method"] not in SETTLEMENT_METHODS:
        raise ValueError("结算方式无效")
    if "document_type_id" in values and not await get_document_type(db, values["document_type_id"]):
        raise ValueError("票据类型不存在")
    for field, value in values.items():
        setattr(tpl, field, value)
    if data.lines is not None:
        for line in data.lines:
            _validate_line(line)
        for old in list(tpl.lines):
            await db.delete(old)
        await db.flush()
        for line in sorted(data.lines, key=lambda item: item.line_no):
            db.add(DocumentVoucherTemplateLine(id=str(uuid.uuid4()), template_id=tpl.id, **line.model_dump()))
    await db.flush()
    return await get_template(db, tpl.id)


async def delete_template(db: AsyncSession, tpl: DocumentVoucherTemplate) -> None:
    await db.delete(tpl)
    await db.flush()


async def copy_template(db: AsyncSession, tpl: DocumentVoucherTemplate) -> DocumentVoucherTemplate:
    clone = DocumentVoucherTemplate(
        id=str(uuid.uuid4()),
        company_id=tpl.company_id,
        document_type_id=tpl.document_type_id,
        document_name=f"{tpl.document_name} 副本",
        settlement_method=tpl.settlement_method,
        business_type=tpl.business_type,
        summary_template=tpl.summary_template,
        is_enabled=False,
        priority=tpl.priority + 1,
        created_from="copy",
    )
    db.add(clone)
    await db.flush()
    for line in tpl.lines:
        db.add(
            DocumentVoucherTemplateLine(
                id=str(uuid.uuid4()),
                template_id=clone.id,
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
            )
        )
    await db.flush()
    return await get_template(db, clone.id)


def _validate_template_payload(data: VoucherTemplateCreate) -> None:
    if data.settlement_method not in SETTLEMENT_METHODS:
        raise ValueError("结算方式无效")
    for line in data.lines:
        _validate_line(line)
    debit = {line.amount_source for line in data.lines if line.debit_credit == "debit"}
    credit = {line.amount_source for line in data.lines if line.debit_credit == "credit"}
    if not debit or not credit:
        raise ValueError("模板必须至少包含一借一贷")


def identify_business_type(text: str | None, *, is_income: bool | None = None) -> str:
    value = re.sub(r"\s+", "", text or "")
    rules = [
        (("手续费", "网银服务费", "账户管理费", "短信费"), "手续费"),
        (("利息", "结息"), "利息收入" if is_income else "利息"),
        (("福利费",), "福利费"),
        (("运费", "物流", "快递"), "运杂费"),
        (("办公用品", "文具", "耗材"), "办公用品"),
        (("水电费", "电费", "水费"), "水电费"),
        (("还款", "往来款", "借款", "归还"), "往来款"),
        (("服务费", "咨询", "技术服务"), "服务费"),
        (("销售", "货款", "收入"), "销售收入"),
        (("采购", "商品", "材料"), "采购商品"),
    ]
    for keywords, business_type in rules:
        if any(keyword in value for keyword in keywords):
            return business_type
    if is_income is True:
        return "银行收款"
    if is_income is False:
        return "银行付款"
    return "待选择"


async def recommend_template(
    db: AsyncSession,
    request: TemplatePreviewRequest,
) -> TemplateRecommendation:
    business_type = request.business_type or identify_business_type(
        " ".join(filter(None, [request.summary, request.counterparty_name])),
        is_income=True if request.income_amount else False if request.expense_amount else None,
    )
    settlement = request.settlement_method or ("银行" if request.income_amount or request.expense_amount else "往来结算")
    template = await find_template(
        db,
        company_id=request.client_id,
        template_id=request.template_id,
        document_type_id=request.document_type_id,
        document_name=request.document_name,
        settlement_method=settlement,
        business_type=business_type,
    )
    return TemplateRecommendation(
        template_id=template.id if template else None,
        document_type_id=template.document_type_id if template else request.document_type_id,
        document_name=template.document_name if template else request.document_name,
        settlement_method=template.settlement_method if template else settlement,
        business_type=business_type,
        confidence=95 if template else 40,
        reason="模板精确匹配" if template else "未匹配到启用模板，请手动选择",
    )


async def find_template(
    db: AsyncSession,
    *,
    company_id: str | None,
    template_id: str | None = None,
    document_type_id: str | None = None,
    document_name: str | None = None,
    settlement_method: str | None = None,
    business_type: str | None = None,
) -> DocumentVoucherTemplate | None:
    if template_id:
        template = await get_template(db, template_id)
        return template if template and template.is_enabled else None
    stmt = (
        select(DocumentVoucherTemplate)
        .options(selectinload(DocumentVoucherTemplate.lines))
        .where(DocumentVoucherTemplate.is_enabled == True)
    )
    if company_id:
        stmt = stmt.where((DocumentVoucherTemplate.company_id == None) | (DocumentVoucherTemplate.company_id == company_id))
    else:
        stmt = stmt.where(DocumentVoucherTemplate.company_id == None)
    if document_type_id:
        stmt = stmt.where(DocumentVoucherTemplate.document_type_id == document_type_id)
    if document_name:
        stmt = stmt.where(DocumentVoucherTemplate.document_name == document_name)
    if settlement_method:
        stmt = stmt.where(DocumentVoucherTemplate.settlement_method == settlement_method)
    if business_type:
        stmt = stmt.where(DocumentVoucherTemplate.business_type == business_type)
    stmt = stmt.order_by(DocumentVoucherTemplate.company_id.desc(), DocumentVoucherTemplate.priority)
    result = await db.execute(stmt)
    return result.unique().scalars().first()


def _amount_from_source(source: str, document: dict[str, Any]) -> float:
    mapping = {
        "totalAmount": document.get("total_amount") or document.get("totalAmount"),
        "amount": document.get("amount"),
        "taxAmount": document.get("tax_amount") or document.get("taxAmount"),
        "incomeAmount": document.get("income_amount") or document.get("incomeAmount"),
        "expenseAmount": document.get("expense_amount") or document.get("expenseAmount"),
        "balance": document.get("balance"),
        "manual": 0,
        "zero": 0,
    }
    try:
        return round(float(mapping.get(source) or 0), 2)
    except (TypeError, ValueError):
        return 0


def _render_summary(template: str, document: dict[str, Any]) -> str:
    summary = template or document.get("summary") or "凭证草稿"
    values = {
        "counterpartyName": document.get("counterparty_name") or document.get("counterparty") or "",
        "documentName": document.get("document_name") or "",
        "businessType": document.get("business_type") or "",
    }
    for key, value in values.items():
        summary = summary.replace("{" + key + "}", str(value))
    return summary[:500]


async def generate_voucher_draft_from_document(
    db: AsyncSession,
    *,
    client_id: str,
    document: dict[str, Any],
    voucher_date: date | None = None,
    voucher_type: str = "记",
) -> EntryCreate:
    recommendation = await recommend_template(
        db,
        TemplatePreviewRequest(
            client_id=client_id,
            template_id=document.get("template_id"),
            document_type_id=document.get("document_type_id"),
            document_name=document.get("document_name"),
            settlement_method=document.get("settlement_method"),
            business_type=document.get("business_type"),
            summary=document.get("summary"),
            counterparty_name=document.get("counterparty_name") or document.get("counterparty"),
            total_amount=document.get("total_amount"),
            amount=document.get("amount"),
            tax_amount=document.get("tax_amount"),
            income_amount=document.get("income_amount"),
            expense_amount=document.get("expense_amount"),
            balance=document.get("balance"),
        )
    )
    template = await find_template(db, company_id=client_id, template_id=recommendation.template_id)
    if not template:
        raise ValueError("未匹配到启用的票据分录模板，请先选择模板")
    document["business_type"] = recommendation.business_type
    document["settlement_method"] = recommendation.settlement_method
    document["document_name"] = template.document_name
    summary = _render_summary(document.get("summary_override") or template.summary_template, document)

    lines: list[EntryLineCreate] = []
    for template_line in template.lines:
        amount = _amount_from_source(template_line.amount_source, document)
        account_fields = await _line_account_fields(db, client_id, template_line, document)
        lines.append(
            EntryLineCreate(
                line_number=template_line.line_no,
                account_code=account_fields["account_code"],
                account_name=account_fields["account_name"],
                direction=template_line.debit_credit,
                amount=amount,
                summary_detail=summary,
                account_full_name=account_fields.get("account_full_name"),
                parent_account_code=account_fields.get("parent_account_code"),
                parent_account_name=account_fields.get("parent_account_name"),
                auxiliary_type=account_fields.get("auxiliary_type"),
                auxiliary_code=account_fields.get("auxiliary_code"),
                auxiliary_name=account_fields.get("auxiliary_name"),
                counterparty_name=document.get("counterparty_name") or document.get("counterparty"),
                counterparty_account=document.get("counterparty_account") or document.get("account_number"),
                source_type=document.get("source_type"),
                source_document_id=document.get("source_document_id"),
                source_row_id=document.get("source_row_id"),
                manual_account_override=bool(account_fields.get("manual_account_override")),
                account_selection_source=account_fields.get("account_selection_source") or "auto",
            )
        )
    return EntryCreate(
        client_id=client_id,
        source_invoice_id=document.get("source_invoice_id"),
        voucher_date=voucher_date or document.get("voucher_date") or date.today(),
        voucher_type=voucher_type,
        summary=summary,
        lines=lines,
    )


async def _line_account_fields(
    db: AsyncSession,
    client_id: str,
    template_line: DocumentVoucherTemplateLine,
    document: dict[str, Any],
) -> dict[str, Any]:
    selected = document.get("selected_account")
    if (
        selected
        and template_line.account_code == MATCHED_CURRENT_ACCOUNT
        and selected.get("account_code")
    ):
        return {
            "account_code": selected.get("account_code"),
            "account_name": selected.get("account_name") or selected.get("account_full_name") or selected.get("account_code"),
            "account_full_name": selected.get("account_full_name") or selected.get("account_name"),
            "parent_account_code": selected.get("parent_account_code"),
            "parent_account_name": selected.get("parent_account_name"),
            "auxiliary_type": selected.get("auxiliary_type") or "counterparty",
            "auxiliary_code": selected.get("account_code"),
            "auxiliary_name": selected.get("account_name"),
            "manual_account_override": True,
            "account_selection_source": selected.get("source") or "manual",
        }
    if template_line.account_code == BANK_ACCOUNT_CODE:
        return {
            "account_code": BANK_ACCOUNT_CODE,
            "account_name": BANK_ACCOUNT_NAME,
            "account_full_name": BANK_ACCOUNT_FULL_NAME,
            "auxiliary_type": "bank_account",
            "auxiliary_name": BANK_ACCOUNT_AUX_NAME,
        }
    if template_line.require_sub_account or template_line.account_code == MATCHED_CURRENT_ACCOUNT:
        counterparty = document.get("counterparty_name") or document.get("counterparty")
        allowed = _allowed_parent_codes(template_line, bool(document.get("income_amount")))
        matched = await find_legacy_sub_account_by_counterparty(
            db,
            client_id=client_id,
            counterparty_name=counterparty,
            allowed_parent_codes=allowed,
        )
        if matched:
            return legacy_subject_line_fields(matched, is_income=bool(document.get("income_amount")))
        if template_line.account_code != MATCHED_CURRENT_ACCOUNT:
            return {
                "account_code": template_line.account_code,
                "account_name": template_line.account_name,
                "account_full_name": template_line.account_full_name or template_line.account_name,
                "parent_account_code": template_line.parent_account_code,
                "account_selection_source": "template_parent",
            }
        return {
            "account_code": PENDING_ACCOUNT_CODE,
            "account_name": PENDING_ACCOUNT_NAME,
            "account_full_name": PENDING_ACCOUNT_NAME,
            "account_selection_source": "pending",
        }
    return {
        "account_code": template_line.account_code,
        "account_name": template_line.account_name,
        "account_full_name": template_line.account_full_name or template_line.account_name,
        "parent_account_code": template_line.parent_account_code,
        "account_selection_source": "template",
    }


def _allowed_parent_codes(template_line: DocumentVoucherTemplateLine, is_income: bool) -> list[str]:
    code = template_line.parent_account_code or template_line.account_code
    if code in CURRENT_PARENT_CODES:
        preferred = [code]
    elif template_line.sub_account_match_mode == "customer":
        preferred = ["1122", "1123", "1221"]
    elif template_line.sub_account_match_mode == "supplier":
        preferred = ["2202", "2203", "2241"]
    else:
        preferred = ["1122", "1221", "2203", "1123", "2241", "2202"] if is_income else ["2202", "2241", "1221", "1122", "2203", "1123"]
    return list(dict.fromkeys([*preferred, *CURRENT_PARENT_CODES]))
