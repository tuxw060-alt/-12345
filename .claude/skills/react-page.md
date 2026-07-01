---
name: react-page
description: 创建 React 页面组件的模板和规范。当用户在 frontend/src/pages/ 下新增页面时自动加载。
allowed-tools: [Read, Write, Edit, Bash, Glob, Grep]
---

# React 页面开发规范

## 技术栈

- React 18 + TypeScript
- Ant Design 5 组件库
- Zustand 全局状态管理
- React Query (TanStack) 服务端数据管理
- React Router DOM v6 路由
- Axios HTTP 请求

## 页面模板

```tsx
import { useState } from 'react'
import { Card, Table, Button, Space, Modal, message } from 'antd'
import { PlusOutlined, EditOutlined, DeleteOutlined } from '@ant-design/icons'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { fetchXxxList, deleteXxx } from '../api/xxx'
import type { XxxItem } from '../types/xxx'

export default function XxxPage() {
  const queryClient = useQueryClient()
  const [selectedRow, setSelectedRow] = useState<XxxItem | null>(null)
  const [modalOpen, setModalOpen] = useState(false)

  const { data, isLoading } = useQuery({
    queryKey: ['xxx'],
    queryFn: fetchXxxList,
  })

  const deleteMutation = useMutation({
    mutationFn: deleteXxx,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['xxx'] })
      message.success('删除成功')
    },
  })

  const columns = [
    { title: '名称', dataIndex: 'name', key: 'name' },
    // ...更多列
    {
      title: '操作',
      key: 'actions',
      render: (_: unknown, record: XxxItem) => (
        <Space>
          <Button icon={<EditOutlined />} onClick={() => { setSelectedRow(record); setModalOpen(true) }}>
            编辑
          </Button>
          <Button danger icon={<DeleteOutlined />} onClick={() => deleteMutation.mutate(record.id)}>
            删除
          </Button>
        </Space>
      ),
    },
  ]

  return (
    <Card title="页面标题" extra={<Button type="primary" icon={<PlusOutlined />}>新增</Button>}>
      <Table dataSource={data} columns={columns} loading={isLoading} rowKey="id" />
      <Modal open={modalOpen} onCancel={() => setModalOpen(false)} title="编辑">
        {/* 表单 */}
      </Modal>
    </Card>
  )
}
```

## 规范

1. **API 调用**: 统一在 `frontend/src/api/` 下封装，页面组件不直接写 axios
2. **类型定义**: 在 `frontend/src/types/` 下定义接口类型
3. **服务端数据**: 用 React Query，不要手动 useEffect + useState
4. **UI 状态**: 用 Zustand store（跨页面共享）或本地 useState（页面内）
5. **表格操作**: 统一用 Ant Design Table 的 columns render
6. **错误处理**: API 层统一拦截，页面层用 mutation 的 onError
7. **路由**: 在 App.tsx 中添加 `<Route>` 和侧边导航项
