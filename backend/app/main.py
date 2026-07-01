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
