"""快记帐 — 代理记账 AI 助手"""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Depends
from fastapi.responses import FileResponse

from app.config import settings
from app.database import init_db
from app.auth import require_auth

FRONTEND_DIR = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    from sqlalchemy import text
    from app.database import async_session

    # Seed subjects + rules (first run only)
    async with async_session() as s:
        r = await s.execute(text("SELECT COUNT(*) FROM account_subjects"))
        if r.scalar() == 0:
            import json as _json, uuid as _uid
            from app.models import AccountSubject, MatchingRule

            sf = Path(__file__).resolve().parent.parent / "assets" / "subjects" / "standard_subjects.json"
            if sf.exists():
                data = _json.loads(sf.read_text(encoding="utf-8"))
                for subj in data["subjects"]:
                    s.add(AccountSubject(id=str(_uid.uuid4()), code=subj["code"],
                        name=subj["name"], full_name=subj.get("full_name") or subj["name"],
                        level=subj["level"], parent_code=subj.get("parent_code"),
                        category=subj["category"], direction=subj["direction"],
                        is_leaf=subj.get("is_leaf", True)))
                await s.flush()

            rf = Path(__file__).resolve().parent.parent / "assets" / "subjects" / "matching_rules.json"
            if rf.exists():
                data = _json.loads(rf.read_text(encoding="utf-8"))
                for rule in data["rules"]:
                    s.add(MatchingRule(id=str(_uid.uuid4()), keywords=rule["keywords"],
                        subject_code=rule["subject_code"], priority=rule.get("priority", 0)))
                await s.flush()
            await s.commit()

    # Seed templates (every startup if empty)
    async with async_session() as s2:
        r2 = await s2.execute(text("SELECT COUNT(*) FROM entry_templates"))
        if r2.scalar() == 0:
            import uuid as _uid2
            from app.models import EntryTemplate, EntryTemplateLine

            TPL = [
                ("计提本月工资", "记", "计提{month}工资",
                    [(1,"5602.01","管理费用-工资","debit"),(2,"2211.01","应付职工薪酬-工资","credit")]),
                ("支付社保", "付", "缴纳{month}社保费",
                    [(1,"5602.17","管理费用-社保费","debit"),(2,"2211.02","应付职工薪酬-社保","debit"),(3,"1002","银行存款","credit")]),
                ("支付公积金", "付", "缴纳{month}住房公积金",
                    [(1,"5602.18","管理费用-公积金","debit"),(2,"2211.03","应付职工薪酬-公积金","debit"),(3,"1002","银行存款","credit")]),
                ("支付办公室房租", "付", "支付{month}办公室租金",
                    [(1,"5602.08","管理费用-租赁费","debit"),(2,"1002","银行存款","credit")]),
                ("计提本月折旧", "记", "计提{month}固定资产折旧",
                    [(1,"5602.13","管理费用-折旧费","debit"),(2,"1602","累计折旧","credit")]),
                ("银行扣手续费", "付", "银行{month}账户管理费及手续费",
                    [(1,"5603.02","财务费用-手续费","debit"),(2,"1002","银行存款","credit")]),
                ("收到主营业务收入", "收", "收到{month}服务费收入",
                    [(1,"1002","银行存款","debit"),(2,"5001","主营业务收入","credit")]),
            ]
            for name, vtype, summary, lines in TPL:
                tpl = EntryTemplate(id=str(_uid2.uuid4()), name=name, summary_template=summary, voucher_type=vtype)
                s2.add(tpl)
                for ln, code, aname, direction in lines:
                    s2.add(EntryTemplateLine(id=str(_uid2.uuid4()), template_id=tpl.id,
                        line_number=ln, account_code=code, account_name=aname,
                        direction=direction, amount_source="manual"))
                await s2.flush()
            await s2.commit()

    # Seed document types + voucher templates (every startup if empty)
    async with async_session() as s3:
        r3 = await s3.execute(text("SELECT COUNT(*) FROM document_types"))
        if r3.scalar() == 0:
            import uuid as _uid3
            from app.models.voucher_template import DocumentType, VoucherTemplate, VoucherTemplateLine

            # ── Preset Document Types ──
            PRESET_DOC_TYPES = [
                ("1001", "销售发票", "销售增值税发票"),
                ("2001", "采购发票", "采购增值税普通发票"),
                ("2002", "采购发票", "采购增值税专用发票"),
                ("4001", "费用票据", "费用票据"),
                ("3001", "银行票据", "银行票据"),
            ]
            dt_map: dict[str, str] = {}  # code -> id
            for code, category, name in PRESET_DOC_TYPES:
                dt_id = str(_uid3.uuid4())
                dt_map[code] = dt_id
                s3.add(DocumentType(id=dt_id, code=code, category=category, name=name,
                                    is_system=True, is_enabled=True))
            await s3.flush()

            # ── Preset Voucher Templates ──
            # Helper to create template + lines
            def _add_tpl(doc_code: str, settlement: str, biz_type: str, summary: str,
                         lines: list[dict], priority: int = 0):
                tpl_id = str(_uid3.uuid4())
                dt_id = dt_map.get(doc_code)
                s3.add(VoucherTemplate(
                    id=tpl_id, document_type_id=dt_id,
                    document_name=next((n for c, _, n in PRESET_DOC_TYPES if c == doc_code), ""),
                    settlement_method=settlement, business_type=biz_type,
                    summary_template=summary, priority=priority, created_from="system",
                ))
                for ld in lines:
                    s3.add(VoucherTemplateLine(
                        id=str(_uid3.uuid4()), template_id=tpl_id,
                        line_no=ld["ln"], debit_credit=ld["dc"],
                        account_code=ld["code"], account_name=ld["name"],
                        amount_source=ld.get("src", "totalAmount"),
                        require_sub_account=ld.get("req_sub", False),
                        sub_account_match_mode=ld.get("sub_mode", "none"),
                    ))

            # 1. 销售增值税发票
            _add_tpl("1001", "往来结算", "销售收入", "销售收入", [
                {"ln":1,"dc":"debit","code":"1122","name":"应收账款","src":"totalAmount","req_sub":True,"sub_mode":"customer"},
                {"ln":2,"dc":"credit","code":"5001","name":"主营业务收入","src":"amount"},
                {"ln":3,"dc":"credit","code":"22210102","name":"应交税费-应交增值税-销项税额","src":"taxAmount"},
            ], priority=10)

            # 2. 采购增值税专用发票
            _add_tpl("2002", "往来结算", "采购商品", "采购商品", [
                {"ln":1,"dc":"debit","code":"1405","name":"库存商品","src":"amount"},
                {"ln":2,"dc":"debit","code":"22210101","name":"应交税费-应交增值税-进项税额","src":"taxAmount"},
                {"ln":3,"dc":"credit","code":"2202","name":"应付账款","src":"totalAmount","req_sub":True,"sub_mode":"supplier"},
            ], priority=10)

            # 3. 采购增值税普通发票
            _add_tpl("2001", "往来结算", "采购商品", "采购商品", [
                {"ln":1,"dc":"debit","code":"1405","name":"库存商品","src":"totalAmount"},
                {"ln":2,"dc":"credit","code":"2202","name":"应付账款","src":"totalAmount","req_sub":True,"sub_mode":"supplier"},
            ], priority=10)

            # 4. 费用票据-福利费-往来结算
            _add_tpl("4001", "往来结算", "福利费", "福利费", [
                {"ln":1,"dc":"debit","code":"5602.07","name":"管理费用-福利费","src":"totalAmount"},
                {"ln":2,"dc":"credit","code":"2202","name":"应付账款","src":"totalAmount","req_sub":True,"sub_mode":"supplier"},
            ], priority=5)

            # 5. 费用票据-运杂费-往来结算
            _add_tpl("4001", "往来结算", "运杂费", "运杂费", [
                {"ln":1,"dc":"debit","code":"5602.15","name":"管理费用-快递物流费","src":"totalAmount"},
                {"ln":2,"dc":"credit","code":"2202","name":"应付账款","src":"totalAmount","req_sub":True,"sub_mode":"supplier"},
            ], priority=5)

            # 6. 费用票据-服务费-往来结算
            _add_tpl("4001", "往来结算", "服务费", "服务费", [
                {"ln":1,"dc":"debit","code":"5602.11","name":"管理费用-软件服务费","src":"totalAmount"},
                {"ln":2,"dc":"credit","code":"2202","name":"应付账款","src":"totalAmount","req_sub":True,"sub_mode":"supplier"},
            ], priority=5)

            # 7. 费用票据-办公用品-现金
            _add_tpl("4001", "现金", "办公用品", "办公用品", [
                {"ln":1,"dc":"debit","code":"5602.02","name":"管理费用-办公费","src":"totalAmount"},
                {"ln":2,"dc":"credit","code":"1001","name":"库存现金","src":"totalAmount"},
            ], priority=5)

            # 8. 银行票据-银行收款
            _add_tpl("3001", "银行", "银行收款", "银行收款", [
                {"ln":1,"dc":"debit","code":"100201","name":"银行存款-基本户","src":"incomeAmount"},
                {"ln":2,"dc":"credit","code":"PENDING","name":"待匹配往来科目","src":"incomeAmount","req_sub":True,"sub_mode":"counterparty"},
            ], priority=10)

            # 9. 银行票据-银行付款
            _add_tpl("3001", "银行", "银行付款", "银行付款", [
                {"ln":1,"dc":"debit","code":"PENDING","name":"待匹配往来科目","src":"expenseAmount","req_sub":True,"sub_mode":"counterparty"},
                {"ln":2,"dc":"credit","code":"100201","name":"银行存款-基本户","src":"expenseAmount"},
            ], priority=10)

            # 10. 银行手续费
            _add_tpl("3001", "银行", "手续费", "手续费", [
                {"ln":1,"dc":"debit","code":"560301","name":"财务费用-手续费","src":"expenseAmount"},
                {"ln":2,"dc":"credit","code":"100201","name":"银行存款-基本户","src":"expenseAmount"},
            ], priority=15)

            # 11. 银行利息收入
            _add_tpl("3001", "银行", "利息收入", "利息", [
                {"ln":1,"dc":"debit","code":"100201","name":"银行存款-基本户","src":"incomeAmount"},
                {"ln":2,"dc":"credit","code":"560302","name":"财务费用-利息收入","src":"incomeAmount"},
            ], priority=12)

            await s3.commit()
    yield


app = FastAPI(
    title="快记帐 - 代理记账AI助手",
    version="0.2.0",
    lifespan=lifespan,
    dependencies=[Depends(require_auth)],
)

# Routers
from app.routers import (
    clients, subjects, matching_rules, invoices, entries,
    export_routes, reports, auth, templates, tax, bank, bank_statements,
    voucher_templates,
)
app.include_router(auth.router)
app.include_router(clients.router)
app.include_router(subjects.router)
app.include_router(matching_rules.router)
app.include_router(invoices.router)
app.include_router(bank_statements.router)
app.include_router(entries.router)
app.include_router(export_routes.router)
app.include_router(reports.router)
app.include_router(templates.router)
app.include_router(tax.router)
app.include_router(bank.router)
app.include_router(voucher_templates.router)


@app.get("/api/v1/health")
async def health():
    return {"status": "ok", "app": "快记帐", "version": "0.2.0"}


# Static files + SPA
@app.get("/{full_path:path}")
async def serve_spa(full_path: str):
    fp = FRONTEND_DIR / full_path
    if full_path and fp.exists() and fp.is_file():
        return FileResponse(fp)
    if full_path.startswith("uploads/"):
        up = Path(settings.upload_dir) / full_path.replace("uploads/", "")
        if up.exists():
            return FileResponse(up)
    index = FRONTEND_DIR / "index.html"
    return FileResponse(index) if index.exists() else {"detail": "Frontend not built"}
