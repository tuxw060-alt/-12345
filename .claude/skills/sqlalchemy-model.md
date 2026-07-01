---
name: sqlalchemy-model
description: 创建或修改 SQLAlchemy 数据模型的规范。当用户在 backend/app/models/ 下操作时自动加载。
allowed-tools: [Read, Write, Edit, Bash, Glob, Grep]
---

# SQLAlchemy 模型规范

## 技术栈

- SQLAlchemy 2.0+ (async)
- SQLite 数据库
- UUID 作为主键

## 模型模板

```python
"""模型描述"""
import uuid
from datetime import datetime
from sqlalchemy import String, Text, Float, Integer, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class Xxx(Base):
    __tablename__ = "xxx"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(200), nullable=False, comment="名称")
    # 关联外键示例
    client_id: Mapped[str] = mapped_column(String(36), ForeignKey("clients.id"), nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    # 关系
    client: Mapped["Client"] = relationship(back_populates="xxx_list")
```

## 字段类型速查

| Python 类型 | SQLAlchemy 类型 | 说明 |
|------------|----------------|------|
| `str` | `String(N)` / `Text` | 短文本 / 长文本 |
| `float` | `Float` / `Numeric(p,s)` | 浮点 / 精确小数 |
| `int` | `Integer` | 整数 |
| `bool` | `Boolean` | 布尔 |
| `datetime` | `DateTime` | 日期时间 |
| `date` | `Date` | 日期 |
| `Decimal` | `Numeric(10,2)` | 金额用这个 |

## 规范

1. 主键统一用 `String(36)` + UUID
2. 每个模型必须包含 `created_at` 和 `updated_at`
3. 金额字段用 `Numeric`，不要用 `Float`（精度问题）
4. 外键必须显式声明 `ForeignKey`
5. 适当添加 `comment` 注释
6. 修改模型后，删除 SQLite 文件让应用重新建表（开发阶段）
7. 别忘了在 `backend/app/models/__init__.py` 中导出新模型
