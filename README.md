# 📒 快记帐 — 代理记账 AI 助手

拍照上传发票 → AI 自动识别 → 一键生成记账凭证 → 导出金蝶快记帐可导入的 Excel。

## 功能

- 📸 **发票拍照识别**：调用 DeepSeek Vision API，自动提取发票号码、日期、金额、税额、销售方等关键信息
- 🧠 **智能科目匹配**：AI 根据发票内容自动推荐最合适的会计科目
- 📝 **自动分录生成**：根据发票类型和客户纳税人身份，自动生成借贷分录
- 📊 **金蝶导出**：生成金蝶快记帐"凭证引入"功能的 Excel 文件，一键导入

## 技术栈

| 层 | 技术 |
|---|---|
| 后端 | Python FastAPI + SQLAlchemy + SQLite |
| AI | DeepSeek Vision API |
| 前端 | React 18 + Vite + Ant Design 5 |
| Excel | openpyxl |

## 快速开始

### 1. 安装 Python 依赖

```bash
cd backend
pip install -r requirements.txt
cp .env.example .env
# 编辑 .env 文件，填入你的 DEEPSEEK_API_KEY
```

### 2. 启动后端

```bash
cd backend
uvicorn app.main:app --reload --port 8000
```

首次启动会自动创建数据库并预置会计科目表和匹配规则。
API 文档: http://localhost:8000/docs

### 3. 安装前端依赖

```bash
cd frontend
pnpm install
```

### 4. 启动前端

```bash
cd frontend
pnpm dev
```

打开 http://localhost:5173

### 5. 使用流程

1. **添加客户**：在"客户管理"中添加代理记账的企业
2. **上传发票**：在"上传发票"中拍照或拖入发票图片
3. **审核结果**：检查 AI 识别结果，必要时手动修正
4. **生成凭证**：点击"一键生成记账凭证"
5. **确认导出**：在凭证编辑器中确认借贷平衡后，导出 Excel
6. **导入金蝶**：在金蝶快记帐中 → 查凭证 → 更多 → 导入凭证 → 选择文件

## 项目结构

```
ge/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI 入口
│   │   ├── config.py            # 配置
│   │   ├── database.py          # 数据库连接
│   │   ├── models/              # SQLAlchemy 模型 (5张表)
│   │   ├── schemas/             # Pydantic 请求/响应
│   │   ├── routers/             # API 路由
│   │   ├── services/            # 业务逻辑
│   │   │   ├── ai_service.py    # DeepSeek API 封装
│   │   │   ├── entry_generator.py  # 凭证生成
│   │   │   └── export_service.py   # 金蝶导出
│   │   └── prompts/             # AI Prompt 模板
│   └── assets/subjects/         # 科目表 + 匹配规则
├── frontend/
│   └── src/
│       ├── pages/               # 7 个页面
│       ├── components/          # 共用组件
│       └── api/                 # API 调用
└── scripts/                     # 工具脚本
```
