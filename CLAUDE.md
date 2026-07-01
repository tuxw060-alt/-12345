# CLAUDE.md — 帐无忧项目配置

## 项目概况

帐无忧 (AccountWorryFree) — 代理记账 AI 助手。
- **后端**: Python 3.12 + FastAPI + SQLAlchemy (async) + SQLite
- **前端**: React 18 + TypeScript + Vite + Ant Design 5 + Zustand + React Query
- **AI**: DeepSeek Vision API（发票 OCR 识别）
- **导出**: openpyxl → 金蝶帐无忧 Excel

## 常用命令

| 操作 | 命令 |
|------|------|
| 启动后端 | `cd backend && uvicorn app.main:app --reload --port 8000` |
| 启动前端 | `cd frontend && pnpm dev` |
| 前端构建 | `cd frontend && pnpm build` |
| 安装后端依赖 | `cd backend && pip install -r requirements.txt` |
| 安装前端依赖 | `cd frontend && pnpm install` |
| API 文档 | http://localhost:8000/docs |
| 前端页面 | http://localhost:5173 |

## 项目结构

```
backend/app/
  main.py           # FastAPI 入口 + SPA 静态文件服务
  config.py         # 环境变量配置
  database.py       # 异步 SQLAlchemy 引擎
  models/           # 5张表: client, invoice, account_subject, matching_rule, journal_entry
  schemas/          # Pydantic 请求/响应模型
  routers/          # API 路由层
  services/         # 业务逻辑 (ai_service, entry_generator, export_service, client_service, matching_service, subject_service)
frontend/src/
  pages/            # 7个页面组件
  components/       # 共用组件
  api/              # Axios API 调用层
  hooks/            # Zustand store + React Query hooks
  types/            # TypeScript 类型定义
```

---

# /run-app

启动整个应用（后端 + 前端），两个进程同时运行。

**执行步骤：**
1. 先启动后端：`cd backend && python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload`（后台运行）
2. 再启动前端：`cd frontend && pnpm dev`（后台运行）
3. 等待 3 秒后检查 `curl -s http://127.0.0.1:8000/api/v1/health`
4. 检查 `curl -s -o /dev/null -w "%{http_code}" http://localhost:5173`
5. 报告两个端口的状态

---

# /code-review

对当前未提交的改动进行多维度代码审查。

**执行步骤：**
1. 用 `git diff` 获取所有未提交改动
2. 如未提交改动为空，用 `git diff HEAD~1` 审查最近一次提交
3. 按以下维度逐一审查：
   - **Bug 风险**: 空值处理、边界条件、异步竞态、异常吞没
   - **安全性**: SQL 注入、XSS、敏感信息泄露、命令注入
   - **性能**: N+1 查询、不必要的重渲染、大循环中的 I/O
   - **可维护性**: 命名清晰度、函数长度、重复代码、耦合度
4. 每个发现标注：文件路径、行号、严重程度 🔴🟡🟢、改进建议
5. 最后给出总体评分（1-10）和一句话总结

---

# /fix

系统性修复一个 bug，包含完整流程。

**执行步骤：**
1. 让用户描述 bug 现象（或从上下文获取）
2. 定位相关代码文件
3. 分析根因（不要只看表面）
4. 提出修复方案（如果有多个方案，简要对比）
5. 实施修复
6. 检查修复是否引入新问题（副作用分析）
7. 如果应用在跑，验证修复效果

---

# /feature

结构化开发一个新功能，分阶段推进。

**执行步骤：**
1. **需求澄清**: 确认功能边界、输入输出、交互细节
2. **影响分析**: 列出需要修改的文件清单（按层：模型→服务→路由→前端页面→API调用）
3. **设计输出**: 如果是新 API，给出请求/响应 JSON 示例
4. **逐步实现**: 按依赖顺序实现（后端先行→前端跟进）
5. **自检**: 检查代码风格一致性、错误处理、边界情况
6. **验证**: 如果应用在跑，用 curl 测试 API 或用浏览器验证

---

# /api

快速开发一个新的 API 端点。

**执行步骤：**
1. 确认端点：方法 + 路径 + 功能描述
2. 如果需要新模型/字段 → 先在 `backend/app/models/` 添加
3. 在 `backend/app/schemas/` 添加 Pydantic 模型
4. 在 `backend/app/services/` 添加业务逻辑
5. 在 `backend/app/routers/` 添加路由
6. 在 `backend/app/main.py` 注册路由
7. 给出 curl 测试命令

---

# /commit

分析当前改动，生成规范提交信息并提交。

**执行步骤：**
1. 运行 `git diff --stat` 和 `git diff` 查看改动
2. 总结改动内容
3. 按 Conventional Commits 格式生成提交信息：
   ```
   <type>(<scope>): <描述>
   
   <详细说明>
   ```
   type: feat / fix / refactor / chore / docs / style / perf
4. 让用户确认提交信息
5. 用户确认后执行 `git add -A && git commit -m "..."`

---

# /db

数据库相关操作助手。

**执行步骤：**
1. 理解用户需求（查数据/改模型/迁移/重置）
2. 模型文件在 `backend/app/models/`
3. 数据库配置在 `backend/app/database.py` 和 `backend/app/config.py`
4. 如需修改表结构 → 修改对应 model 文件 → 删除 SQLite 文件重新启动（开发阶段）
5. 如需查询数据 → 写 Python 脚本或直接用 sqlite3 命令
6. SQLite 文件通常在 `backend/` 目录下

---

# /refactor

重构指定代码，保持行为不变的前提下提升代码质量。

**执行步骤：**
1. 读取目标文件
2. 识别改进点：重复代码、过长函数、深层嵌套、魔法数字、不清晰命名
3. 给出重构方案
4. 逐步实施，每次一个小的改动
5. 每步改动后确保语法正确
6. 最终对比改动前后代码行数和复杂度变化

---

# /test

为现有代码编写测试。

**执行步骤：**
1. 确定测试对象（函数/API端点/组件）
2. 检查是否已有测试框架配置（pytest / vitest）
3. 分析边界条件：正常输入、空值、异常输入、并发情况
4. 编写测试用例，覆盖：
   - Happy path
   - Edge cases
   - Error handling
5. 运行测试验证通过

---

# /ai-prompt

调试或优化 AI Prompt 模板。

**执行步骤：**
1. Prompt 模板位于 `backend/app/prompts/` 目录
2. 读取相关 prompt 文件
3. 分析当前 prompt 的问题（输出不准确/格式错误/遗漏信息）
4. 参考 DeepSeek API 最佳实践优化 prompt
5. 保持 JSON 输出格式约束
6. 建议用真实发票测试新 prompt

---

# /export

处理金蝶帐无忧 Excel 导出相关问题。

**执行步骤：**
1. 导出逻辑在 `backend/app/services/export_service.py`
2. 导出路由在 `backend/app/routers/export_routes.py`
3. 金蝶格式要求：特定列顺序、科目代码格式、借贷符号
4. 修改导出逻辑后，用真实数据生成一份 Excel 验证

---

# /dep

检查项目依赖并给出更新建议。

**执行步骤：**
1. 后端：`cd backend && pip list --outdated`
2. 前端：`cd frontend && pnpm outdated`
3. 标注有安全漏洞的依赖（如有工具可用）
4. 给出升级建议，区分安全更新和功能更新
