import { useEffect, useMemo, useState } from 'react'
import {
  Button,
  Form,
  Input,
  InputNumber,
  Modal,
  Popconfirm,
  Select,
  Space,
  Switch,
  Table,
  Tabs,
  Tag,
  Typography,
  message,
} from 'antd'
import { CopyOutlined, DeleteOutlined, EditOutlined, PlusOutlined, ReloadOutlined } from '@ant-design/icons'
import {
  amountSources,
  copyVoucherTemplate,
  createDocumentType,
  createVoucherTemplate,
  deleteDocumentType,
  deleteVoucherTemplate,
  listDocumentTypes,
  listVoucherTemplates,
  restoreDocumentTypeDefaults,
  settlementMethods,
  subAccountModes,
  updateDocumentType,
  updateVoucherTemplate,
  type DocumentType,
  type VoucherTemplate,
  type VoucherTemplateLine,
} from '../api/documentVouchers'
import { useAppStore } from '../hooks/useAppStore'

const businessTypes = [
  '销售收入', '采购商品', '福利费', '运杂费', '服务费', '劳务成本',
  '办公用品', '业务招待费', '交通费', '利息', '利息收入', '手续费',
  '税费缴纳', '还款', '往来款', '银行收款', '银行付款',
]

const blankLine = (lineNo: number): VoucherTemplateLine => ({
  line_no: lineNo,
  debit_credit: lineNo === 1 ? 'debit' : 'credit',
  account_code: '',
  account_name: '',
  account_full_name: '',
  parent_account_code: '',
  amount_source: 'totalAmount',
  require_sub_account: false,
  sub_account_match_mode: 'none',
  allow_manual_edit: true,
})

function linesText(lines: VoucherTemplateLine[]) {
  return (
    <Space direction="vertical" size={2}>
      {lines.map((line) => (
        <span key={line.line_no}>
          <Tag color={line.debit_credit === 'debit' ? 'blue' : 'orange'}>
            {line.debit_credit === 'debit' ? '借' : '贷'}
          </Tag>
          {line.account_full_name || line.account_name || line.account_code}
          <Typography.Text type="secondary"> {amountSources.find((s) => s.value === line.amount_source)?.label || line.amount_source}</Typography.Text>
        </span>
      ))}
    </Space>
  )
}

export default function AccountingSettings() {
  const currentClient = useAppStore((state) => state.currentClient)
  const [documentTypes, setDocumentTypes] = useState<DocumentType[]>([])
  const [templates, setTemplates] = useState<VoucherTemplate[]>([])
  const [docModalOpen, setDocModalOpen] = useState(false)
  const [templateModalOpen, setTemplateModalOpen] = useState(false)
  const [editingDoc, setEditingDoc] = useState<DocumentType | null>(null)
  const [editingTemplate, setEditingTemplate] = useState<VoucherTemplate | null>(null)
  const [loading, setLoading] = useState(false)
  const [docForm] = Form.useForm()
  const [templateForm] = Form.useForm()

  const companyId = currentClient?.id

  const refresh = async () => {
    setLoading(true)
    try {
      const [docs, tpl] = await Promise.all([
        listDocumentTypes(companyId),
        listVoucherTemplates({ company_id: companyId }),
      ])
      setDocumentTypes(docs.items)
      setTemplates(tpl.items)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { refresh() }, [companyId])

  const documentOptions = useMemo(
    () => documentTypes.filter((item) => item.is_enabled).map((item) => ({ value: item.id, label: item.name, item })),
    [documentTypes],
  )

  const openDoc = (record?: DocumentType) => {
    setEditingDoc(record || null)
    docForm.setFieldsValue(record || { code: '', category: '', name: '', is_enabled: true, company_id: null })
    setDocModalOpen(true)
  }

  const saveDoc = async () => {
    const values = await docForm.validateFields()
    try {
      if (editingDoc) await updateDocumentType(editingDoc.id, values)
      else await createDocumentType({ ...values, company_id: null })
      message.success('票据类型已保存')
      setDocModalOpen(false)
      refresh()
    } catch (err: any) {
      message.error(err.response?.data?.detail || err.message)
    }
  }

  const removeDoc = async (record: DocumentType) => {
    try {
      await deleteDocumentType(record.id)
      message.success(record.is_system ? '系统票据已停用' : '票据类型已删除')
      refresh()
    } catch (err: any) {
      message.error(err.response?.data?.detail || err.message)
    }
  }

  const openTemplate = (record?: VoucherTemplate) => {
    setEditingTemplate(record || null)
    templateForm.setFieldsValue(record || {
      document_type_id: documentOptions[0]?.value,
      settlement_method: '往来结算',
      business_type: '销售收入',
      summary_template: '',
      is_enabled: true,
      priority: 100,
      lines: [blankLine(1), blankLine(2)],
    })
    setTemplateModalOpen(true)
  }

  const saveTemplate = async () => {
    const values = await templateForm.validateFields()
    const doc = documentTypes.find((item) => item.id === values.document_type_id)
    const lines = (values.lines || []).map((line: VoucherTemplateLine, index: number) => ({
      ...line,
      line_no: index + 1,
      account_full_name: line.account_full_name || line.account_name,
    }))
    try {
      const payload = { ...values, document_name: doc?.name || values.document_name, company_id: null, lines }
      if (editingTemplate) await updateVoucherTemplate(editingTemplate.id, payload)
      else await createVoucherTemplate(payload)
      message.success('分录模板已保存')
      setTemplateModalOpen(false)
      refresh()
    } catch (err: any) {
      message.error(err.response?.data?.detail || err.message)
    }
  }

  const templateColumns = [
    { title: '序号', dataIndex: 'priority', width: 80 },
    { title: '单据名称', dataIndex: 'document_name', width: 160 },
    { title: '结算方式', dataIndex: 'settlement_method', width: 110 },
    { title: '业务类型', dataIndex: 'business_type', width: 130 },
    { title: '摘要', dataIndex: 'summary_template', width: 180 },
    { title: '分录', dataIndex: 'lines', render: linesText },
    {
      title: '状态',
      dataIndex: 'is_enabled',
      width: 80,
      render: (value: boolean) => <Tag color={value ? 'green' : 'default'}>{value ? '启用' : '停用'}</Tag>,
    },
    {
      title: '操作',
      width: 150,
      render: (_: unknown, record: VoucherTemplate) => (
        <Space size={0}>
          <Button type="link" icon={<EditOutlined />} onClick={() => openTemplate(record)} />
          <Button type="link" icon={<CopyOutlined />} onClick={async () => { await copyVoucherTemplate(record.id); refresh() }} />
          <Popconfirm title="删除该分录模板？" onConfirm={async () => { await deleteVoucherTemplate(record.id); refresh() }}>
            <Button type="link" danger icon={<DeleteOutlined />} />
          </Popconfirm>
        </Space>
      ),
    },
  ]

  return (
    <div>
      <Space style={{ justifyContent: 'space-between', width: '100%', marginBottom: 16 }}>
        <Typography.Title level={4} style={{ margin: 0 }}>会计工作设置</Typography.Title>
        <Space>
          <Button icon={<ReloadOutlined />} onClick={async () => { await restoreDocumentTypeDefaults(); refresh() }}>恢复预置</Button>
          <Button type="primary" icon={<PlusOutlined />} onClick={() => openTemplate()}>新增模板</Button>
        </Space>
      </Space>

      <Tabs items={[
        { key: 'system', label: '会计制度', children: <Typography.Text type="secondary">会计制度参数将在后续版本接入。</Typography.Text> },
        {
          key: 'documents',
          label: '票据设置',
          children: (
            <>
              <Space style={{ marginBottom: 12 }}>
                <Button type="primary" icon={<PlusOutlined />} onClick={() => openDoc()}>新增票据</Button>
              </Space>
              <Table
                className="dense-config-table"
                loading={loading}
                rowKey="id"
                size="small"
                dataSource={documentTypes}
                columns={[
                  { title: '编码', dataIndex: 'code', width: 110 },
                  { title: '单据类别', dataIndex: 'category', width: 160 },
                  { title: '单据名称', dataIndex: 'name' },
                  { title: '来源', dataIndex: 'is_system', width: 90, render: (v: boolean) => <Tag>{v ? '系统' : '自定义'}</Tag> },
                  { title: '状态', dataIndex: 'is_enabled', width: 90, render: (v: boolean) => <Tag color={v ? 'green' : 'default'}>{v ? '启用' : '停用'}</Tag> },
                  {
                    title: '操作',
                    width: 120,
                    render: (_: unknown, record: DocumentType) => (
                      <Space size={0}>
                        <Button type="link" icon={<EditOutlined />} onClick={() => openDoc(record)} />
                        <Popconfirm title={record.is_system ? '系统票据将停用，继续？' : '删除该票据？'} onConfirm={() => removeDoc(record)}>
                          <Button type="link" danger icon={<DeleteOutlined />} />
                        </Popconfirm>
                      </Space>
                    ),
                  },
                ]}
              />
            </>
          ),
        },
        {
          key: 'templates',
          label: '票据分录模板',
          children: <Table className="dense-config-table" loading={loading} rowKey="id" size="small" dataSource={templates} columns={templateColumns} scroll={{ x: 1100 }} />,
        },
        { key: 'cashflow', label: '现金流量项目模板', children: <Typography.Text type="secondary">现金流量项目模板将在后续版本接入。</Typography.Text> },
      ]} />

      <Modal title={editingDoc ? '编辑票据' : '新增票据'} open={docModalOpen} onOk={saveDoc} onCancel={() => setDocModalOpen(false)}>
        <Form form={docForm} layout="vertical">
          <Form.Item name="code" label="编码" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="category" label="单据类别" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="name" label="单据名称" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="is_enabled" label="启用" valuePropName="checked">
            <Switch />
          </Form.Item>
        </Form>
      </Modal>

      <Modal width={980} title={editingTemplate ? '编辑分录模板' : '新增分录模板'} open={templateModalOpen} onOk={saveTemplate} onCancel={() => setTemplateModalOpen(false)}>
        <Form form={templateForm} layout="vertical">
          <Space style={{ width: '100%' }} align="start">
            <Form.Item name="document_type_id" label="单据名称" rules={[{ required: true }]} style={{ width: 180 }}>
              <Select options={documentOptions} />
            </Form.Item>
            <Form.Item name="settlement_method" label="结算方式" rules={[{ required: true }]} style={{ width: 130 }}>
              <Select options={settlementMethods.map((value) => ({ value, label: value }))} />
            </Form.Item>
            <Form.Item name="business_type" label="业务类型" rules={[{ required: true }]} style={{ width: 150 }}>
              <Select showSearch options={businessTypes.map((value) => ({ value, label: value }))} />
            </Form.Item>
            <Form.Item name="summary_template" label="摘要模板" rules={[{ required: true }]} style={{ width: 220 }}>
              <Input />
            </Form.Item>
            <Form.Item name="priority" label="序号" style={{ width: 90 }}>
              <InputNumber min={1} />
            </Form.Item>
            <Form.Item name="is_enabled" label="启用" valuePropName="checked">
              <Switch />
            </Form.Item>
          </Space>

          <Form.List name="lines">
            {(fields, { add, remove }) => (
              <>
                <Table
                  rowKey="key"
                  pagination={false}
                  size="small"
                  dataSource={fields}
                  columns={[
                    { title: '借/贷', width: 90, render: (_: unknown, field: any) => <Form.Item name={[field.name, 'debit_credit']} noStyle><Select options={[{ value: 'debit', label: '借' }, { value: 'credit', label: '贷' }]} /></Form.Item> },
                    { title: '科目编码', width: 130, render: (_: unknown, field: any) => <Form.Item name={[field.name, 'account_code']} noStyle rules={[{ required: true }]}><Input /></Form.Item> },
                    { title: '会计科目', render: (_: unknown, field: any) => <Form.Item name={[field.name, 'account_name']} noStyle rules={[{ required: true }]}><Input /></Form.Item> },
                    { title: '金额来源', width: 130, render: (_: unknown, field: any) => <Form.Item name={[field.name, 'amount_source']} noStyle><Select options={amountSources} /></Form.Item> },
                    { title: '往来明细', width: 100, render: (_: unknown, field: any) => <Form.Item name={[field.name, 'require_sub_account']} valuePropName="checked" noStyle><Switch /></Form.Item> },
                    { title: '匹配方式', width: 140, render: (_: unknown, field: any) => <Form.Item name={[field.name, 'sub_account_match_mode']} noStyle><Select options={subAccountModes} /></Form.Item> },
                    { title: '操作', width: 70, render: (_: unknown, field: any) => <Button type="link" danger icon={<DeleteOutlined />} onClick={() => remove(field.name)} /> },
                  ]}
                />
                <Button style={{ marginTop: 12 }} icon={<PlusOutlined />} onClick={() => add(blankLine(fields.length + 1))}>新增分录行</Button>
              </>
            )}
          </Form.List>
        </Form>
      </Modal>
    </div>
  )
}
