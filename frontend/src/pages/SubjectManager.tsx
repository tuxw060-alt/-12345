import { useEffect, useState } from 'react'
import {
  Card, Table, Tabs, Tag, Typography, Input, Button, Space, message,
  Popconfirm, Modal, Form, Select,
} from 'antd'
import { PlusOutlined, DeleteOutlined, SearchOutlined } from '@ant-design/icons'
import api from '../api/client'
import {
  listSubjects,
  listMatchingRules,
  createMatchingRule,
  deleteMatchingRule,
  testMatchingRule,
} from '../api/subjects'
import type { AccountSubject, MatchingRule } from '../types/invoice'

export default function SubjectManager() {
  const [subjects, setSubjects] = useState<AccountSubject[]>([])
  const [rules, setRules] = useState<MatchingRule[]>([])
  const [search, setSearch] = useState('')
  const [ruleModalOpen, setRuleModalOpen] = useState(false)
  const [ruleForm] = Form.useForm()

  const fetchData = () => {
    listSubjects({ limit: 500 }).then((r) => setSubjects(r.items))
    listMatchingRules().then((r) => setRules(r.items))
  }

  useEffect(() => { fetchData() }, [])

  const handleAddRule = async () => {
    try {
      const values = await ruleForm.validateFields()
      await createMatchingRule(values)
      message.success('规则已添加')
      setRuleModalOpen(false)
      ruleForm.resetFields()
      fetchData()
    } catch (err: any) {
      message.error(`添加失败: ${err.message}`)
    }
  }

  const handleDeleteRule = async (id: string) => {
    await deleteMatchingRule(id)
    message.success('规则已删除')
    fetchData()
  }

  const handleDeleteSubject = async (code: string, name: string) => {
    try {
      await api.delete(`/subjects/${code}`)
      message.success(`已停用科目 ${name}`)
      fetchData()
    } catch {
      message.error('删除失败')
    }
  }

  const categoryColor: Record<string, string> = {
    '资产': 'blue', '负债': 'orange', '权益': 'purple',
    '成本': 'red', '损益': 'green',
  }

  const subjectColumns = [
    { title: '科目代码', dataIndex: 'code', key: 'code', width: 120 },
    {
      title: '科目名称', dataIndex: 'full_name', key: 'name',
      render: (v: string, r: AccountSubject) => (
        <span style={{ paddingLeft: (r.level - 1) * 16 }}>{v || r.name}</span>
      ),
    },
    {
      title: '类别', dataIndex: 'category', key: 'category', width: 80,
      render: (v: string) => <Tag color={categoryColor[v] || 'default'}>{v}</Tag>,
    },
    {
      title: '方向', dataIndex: 'direction', key: 'direction', width: 70,
      render: (v: string) => v === 'debit' ? '借方' : '贷方',
    },
    {
      title: '末级', dataIndex: 'is_leaf', key: 'leaf', width: 60,
      render: (v: boolean) => v ? <Tag color="green">是</Tag> : <Tag>否</Tag>,
    },
    {
      title: '操作', key: 'action', width: 60,
      render: (_: any, r: AccountSubject) => (
        <Popconfirm title={`停用 ${r.name}?`} onConfirm={() => handleDeleteSubject(r.code, r.name)}>
          <Button type="link" size="small" danger icon={<DeleteOutlined />} />
        </Popconfirm>
      ),
    },
  ]

  const filteredSubjects = search
    ? subjects.filter((s) =>
        s.code.includes(search) ||
        s.name.includes(search) ||
        (s.full_name || '').includes(search)
      )
    : subjects

  const ruleColumns = [
    { title: '关键词', dataIndex: 'keywords', key: 'kw', ellipsis: true },
    { title: '科目代码', dataIndex: 'subject_code', key: 'code', width: 120 },
    { title: '科目名称', dataIndex: 'subject_name', key: 'name' },
    { title: '优先级', dataIndex: 'priority', key: 'pri', width: 70 },
    {
      title: '操作', key: 'action', width: 60,
      render: (_: any, r: MatchingRule) => (
        <Popconfirm title="删除此规则?" onConfirm={() => handleDeleteRule(r.id)}>
          <Button type="link" danger size="small" icon={<DeleteOutlined />} />
        </Popconfirm>
      ),
    },
  ]

  return (
    <div>
      <Typography.Title level={4}>科目与规则管理</Typography.Title>

      <Tabs defaultActiveKey="subjects" items={[
        {
          key: 'subjects',
          label: '会计科目',
          children: (
            <Card>
              <Space style={{ marginBottom: 16 }}>
                <Input
                  prefix={<SearchOutlined />}
                  placeholder="搜索科目代码或名称..."
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  style={{ width: 300 }}
                  allowClear
                />
                <Tag>{filteredSubjects.length} 个科目</Tag>
              </Space>
              <Table
                columns={subjectColumns}
                dataSource={filteredSubjects}
                rowKey="code"
                size="small"
                pagination={false}
                scroll={{ y: 500 }}
              />
            </Card>
          ),
        },
        {
          key: 'rules',
          label: '匹配规则',
          children: (
            <Card>
              <Space style={{ marginBottom: 16 }}>
                <Button type="primary" icon={<PlusOutlined />} onClick={() => setRuleModalOpen(true)}>
                  添加规则
                </Button>
                <Typography.Text type="secondary">
                  当发票内容匹配关键词时，自动推荐对应的会计科目
                </Typography.Text>
              </Space>
              <Table
                columns={ruleColumns}
                dataSource={rules}
                rowKey="id"
                size="small"
                pagination={false}
              />
            </Card>
          ),
        },
      ]} />

      <Modal
        title="添加匹配规则"
        open={ruleModalOpen}
        onOk={handleAddRule}
        onCancel={() => setRuleModalOpen(false)}
      >
        <Form form={ruleForm} layout="vertical">
          <Form.Item name="keywords" label="关键词 (用 | 分隔)"
            rules={[{ required: true, message: '请输入关键词' }]}>
            <Input placeholder="例如: 餐饮|餐费|宴请|招待" />
          </Form.Item>
          <Form.Item name="subject_code" label="科目代码"
            rules={[{ required: true, message: '请输入科目代码' }]}>
            <Input placeholder="例如: 5602.05" />
          </Form.Item>
          <Form.Item name="subject_name" label="科目名称">
            <Input placeholder="例如: 管理费用-业务招待费" />
          </Form.Item>
          <Form.Item name="priority" label="优先级" initialValue={0}>
            <Select
              options={[5, 6, 7, 8, 9, 10].map((p) => ({ value: p, label: `${p}` }))}
            />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}
