import { useEffect, useState } from 'react'
import {
  Button,
  Card,
  Form,
  Input,
  message,
  Modal,
  Popconfirm,
  Select,
  Space,
  Table,
  Tabs,
  Tag,
  Typography,
  Upload,
} from 'antd'
import {
  DeleteOutlined,
  PlusOutlined,
  SearchOutlined,
  UploadOutlined,
} from '@ant-design/icons'
import api from '../api/client'
import {
  createMatchingRule,
  deleteMatchingRule,
  importLegacySubjects,
  listMatchingRules,
  listSubjects,
} from '../api/subjects'
import { useAppStore } from '../hooks/useAppStore'
import type { AccountSubject, MatchingRule } from '../types/invoice'

export default function SubjectManager() {
  const currentClient = useAppStore((state) => state.currentClient)
  const [subjects, setSubjects] = useState<AccountSubject[]>([])
  const [rules, setRules] = useState<MatchingRule[]>([])
  const [search, setSearch] = useState('')
  const [ruleModalOpen, setRuleModalOpen] = useState(false)
  const [importing, setImporting] = useState(false)
  const [ruleForm] = Form.useForm()

  const fetchData = () => {
    listSubjects({ client_id: currentClient?.id, limit: 1000 }).then((r) => setSubjects(r.items))
    listMatchingRules(currentClient?.id ? { client_id: currentClient.id } : undefined).then((r) => setRules(r.items))
  }

  useEffect(() => { fetchData() }, [currentClient?.id])

  const handleImportLegacy = async (file: File) => {
    if (!currentClient?.id) {
      message.error('请先选择客户，再导入该账套的往来科目')
      return Upload.LIST_IGNORE
    }
    setImporting(true)
    try {
      const result = await importLegacySubjects(file, currentClient.id)
      const conflictText = result.conflicts.length ? `，冲突 ${result.conflicts.length} 条` : ''
      const warningText = result.warnings.length ? `，跳过 ${result.warnings.length} 行异常数据` : ''
      message.success(
        `导入 ${result.parent_code || ''} ${result.parent_name || ''}：新增 ${result.inserted} 条，更新 ${result.updated} 条${conflictText}${warningText}`,
        6,
      )
      fetchData()
    } catch (err: any) {
      message.error(err.response?.data?.detail || `导入失败: ${err.message}`)
    } finally {
      setImporting(false)
    }
    return Upload.LIST_IGNORE
  }

  const handleAddRule = async () => {
    try {
      const values = await ruleForm.validateFields()
      await createMatchingRule({ ...values, client_id: currentClient?.id || null })
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
    资产: 'blue',
    负债: 'orange',
    权益: 'purple',
    成本: 'red',
    损益: 'green',
  }

  const filteredSubjects = search
    ? subjects.filter((subject) =>
        subject.code.includes(search)
        || subject.name.includes(search)
        || (subject.full_name || '').includes(search)
      )
    : subjects

  const subjectColumns = [
    { title: '科目编码', dataIndex: 'code', key: 'code', width: 130 },
    {
      title: '科目名称',
      dataIndex: 'name',
      key: 'name',
      render: (_: string, record: AccountSubject) => {
        const displayName = record.full_name || record.name
        return (
          <span style={{ paddingLeft: Math.max(record.level - 1, 0) * 18 }}>
            {!record.is_leaf ? <strong>{displayName}</strong> : displayName}
          </span>
        )
      },
    },
    {
      title: '父级',
      key: 'parent',
      width: 170,
      render: (_: unknown, record: AccountSubject) =>
        record.parent_code ? `${record.parent_code} ${record.parent_account_name || ''}` : '-',
    },
    {
      title: '类别',
      dataIndex: 'category',
      key: 'category',
      width: 90,
      render: (value: string) => <Tag color={categoryColor[value] || 'default'}>{value}</Tag>,
    },
    {
      title: '方向',
      dataIndex: 'direction',
      key: 'direction',
      width: 80,
      render: (value: string) => value === 'debit' ? '借方' : '贷方',
    },
    {
      title: '来源',
      dataIndex: 'created_from',
      key: 'created_from',
      width: 110,
      render: (value: string | null) => value === 'legacy_import' ? <Tag color="cyan">老账套</Tag> : <Tag>系统</Tag>,
    },
    {
      title: '末级',
      dataIndex: 'is_leaf',
      key: 'leaf',
      width: 80,
      render: (value: boolean) => value ? <Tag color="green">是</Tag> : <Tag>否</Tag>,
    },
    {
      title: '操作',
      key: 'action',
      width: 70,
      render: (_: unknown, record: AccountSubject) => (
        <Popconfirm title={`停用 ${record.name}?`} onConfirm={() => handleDeleteSubject(record.code, record.name)}>
          <Button type="link" size="small" danger icon={<DeleteOutlined />} />
        </Popconfirm>
      ),
    },
  ]

  const ruleColumns = [
    { title: '关键词', dataIndex: 'keywords', key: 'kw', ellipsis: true },
    { title: '科目编码', dataIndex: 'subject_code', key: 'code', width: 120 },
    { title: '科目名称', dataIndex: 'subject_name', key: 'name' },
    { title: '优先级', dataIndex: 'priority', key: 'pri', width: 80 },
    {
      title: '操作',
      key: 'action',
      width: 70,
      render: (_: unknown, record: MatchingRule) => (
        <Popconfirm title="删除此规则?" onConfirm={() => handleDeleteRule(record.id)}>
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
              <Space style={{ marginBottom: 16 }} wrap>
                <Input
                  prefix={<SearchOutlined />}
                  placeholder="搜索科目编码或名称"
                  value={search}
                  onChange={(event) => setSearch(event.target.value)}
                  style={{ width: 300 }}
                  allowClear
                />
                <Upload
                  accept=".xls,.xlsx"
                  showUploadList={false}
                  beforeUpload={(file) => handleImportLegacy(file)}
                >
                  <Button icon={<UploadOutlined />} loading={importing}>
                    导入老账套往来明细
                  </Button>
                </Upload>
                <Tag>{filteredSubjects.length} 个科目</Tag>
              </Space>
              <Table
                columns={subjectColumns}
                dataSource={filteredSubjects}
                rowKey={(record) => `${record.client_id || 'global'}-${record.code}`}
                size="small"
                pagination={false}
                scroll={{ y: 520 }}
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
                  发票或流水内容命中关键词时，自动推荐对应科目。
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
          <Form.Item
            name="keywords"
            label="关键词（用 | 分隔）"
            rules={[{ required: true, message: '请输入关键词' }]}
          >
            <Input placeholder="例如: 餐饮|餐费|宴请|招待" />
          </Form.Item>
          <Form.Item
            name="subject_code"
            label="科目编码"
            rules={[{ required: true, message: '请输入科目编码' }]}
          >
            <Input placeholder="例如: 5602.05" />
          </Form.Item>
          <Form.Item name="subject_name" label="科目名称">
            <Input placeholder="例如: 管理费用-业务招待费" />
          </Form.Item>
          <Form.Item name="priority" label="优先级" initialValue={5}>
            <Select options={[5, 6, 7, 8, 9, 10].map((value) => ({ value, label: `${value}` }))} />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}
