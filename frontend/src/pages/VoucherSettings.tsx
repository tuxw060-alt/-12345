import { useEffect, useState } from 'react'
import {
  Card, Table, Tabs, Tag, Typography, Button, Space, message,
  Popconfirm, Modal, Form, Input, Select, InputNumber, Switch,
  Tooltip, Badge, Descriptions,
} from 'antd'
import {
  PlusOutlined, DeleteOutlined, EditOutlined, CopyOutlined,
  ReloadOutlined, PlayCircleOutlined, PauseCircleOutlined,
  EyeOutlined,
} from '@ant-design/icons'
import {
  getDocumentTypes, createDocumentType, updateDocumentType,
  deleteDocumentType, restorePresetDocumentTypes,
  getVoucherTemplates, createVoucherTemplate, updateVoucherTemplate,
  deleteVoucherTemplate, copyVoucherTemplate, toggleVoucherTemplate,
} from '../api/voucherTemplates'
import { getSubjectTree } from '../api/subjects'
import type {
  DocumentType, VoucherTemplate, VoucherTemplateLine,
  SubjectTreeNode,
} from '../types/invoice'

const SETTLEMENT_OPTIONS = ['往来结算', '现金', '银行', '未结算', '其他']
const BUSINESS_TYPES = [
  '销售收入', '采购商品', '福利费', '运杂费', '服务费',
  '劳务成本', '办公用品', '业务招待费', '交通费', '利息',
  '手续费', '税费缴纳', '还款', '往来款', '银行收款', '银行付款',
  '利息收入', '利息支出', '工资薪酬', '社保公积金', '水电费', '租赁费',
  '通讯费', '维修费', '差旅费',
]
const AMOUNT_SOURCES = [
  { value: 'totalAmount', label: '合计金额(价税合计)' },
  { value: 'amount', label: '金额(不含税)' },
  { value: 'taxAmount', label: '税额' },
  { value: 'incomeAmount', label: '收入金额' },
  { value: 'expenseAmount', label: '支出金额' },
  { value: 'balance', label: '余额' },
  { value: 'manual', label: '手工输入' },
  { value: 'zero', label: '0' },
]
const SUB_MATCH_MODES = [
  { value: 'none', label: '不需要' },
  { value: 'customer', label: '客户' },
  { value: 'supplier', label: '供应商' },
  { value: 'counterparty', label: '对方单位' },
  { value: 'legacy_sub_account', label: '老账套明细' },
  { value: 'bank_account', label: '银行账号' },
]

export default function VoucherSettings() {
  const [activeTab, setActiveTab] = useState('docTypes')

  return (
    <div>
      <Typography.Title level={4} style={{ marginBottom: 16 }}>票据设置</Typography.Title>
      <Tabs activeKey={activeTab} onChange={setActiveTab} items={[
        { key: 'docTypes', label: '单据类别', children: <DocumentTypeTab /> },
        { key: 'templates', label: '票据分录模板', children: <VoucherTemplateTab /> },
      ]} />
    </div>
  )
}

// ═══════════════════════════════════════════════════════════════
// Document Type Tab
// ═══════════════════════════════════════════════════════════════

function DocumentTypeTab() {
  const [items, setItems] = useState<DocumentType[]>([])
  const [loading, setLoading] = useState(true)
  const [modalOpen, setModalOpen] = useState(false)
  const [editing, setEditing] = useState<DocumentType | null>(null)
  const [form] = Form.useForm()

  const fetchData = async () => {
    setLoading(true)
    try {
      setItems(await getDocumentTypes())
    } catch { message.error('加载单据类别失败') }
    finally { setLoading(false) }
  }

  useEffect(() => { fetchData() }, [])

  const handleSave = async () => {
    const values = await form.validateFields()
    try {
      if (editing) {
        await updateDocumentType(editing.id, values)
        message.success('已更新')
      } else {
        await createDocumentType(values)
        message.success('已添加')
      }
      setModalOpen(false)
      form.resetFields()
      fetchData()
    } catch (err: any) {
      message.error(err.response?.data?.detail || err.message || '操作失败')
    }
  }

  const handleDelete = async (dt: DocumentType) => {
    try {
      await deleteDocumentType(dt.id)
      message.success('已删除')
      fetchData()
    } catch (err: any) {
      message.error(err.response?.data?.detail || err.message || '删除失败')
    }
  }

  const handleRestore = async () => {
    try {
      await restorePresetDocumentTypes()
      message.success('已恢复预置单据')
      fetchData()
    } catch { message.error('恢复失败') }
  }

  const columns = [
    { title: '编码', dataIndex: 'code', key: 'code', width: 80 },
    { title: '单据类别', dataIndex: 'category', key: 'category', width: 100 },
    { title: '单据名称', dataIndex: 'name', key: 'name', width: 200 },
    { title: '系统预置', dataIndex: 'is_system', key: 'sys', width: 80,
      render: (v: boolean) => v ? <Tag color="blue">系统</Tag> : <Tag>自定义</Tag> },
    { title: '状态', dataIndex: 'is_enabled', key: 'status', width: 80,
      render: (v: boolean) => <Badge status={v ? 'success' : 'default'} text={v ? '启用' : '停用'} /> },
    { title: '操作', key: 'action', width: 120,
      render: (_: any, r: DocumentType) => (
        <Space size={0}>
          <Button type="link" size="small" icon={<EditOutlined />}
            onClick={() => { setEditing(r); form.setFieldsValue(r); setModalOpen(true) }}>编辑</Button>
          {!r.is_system && (
            <Popconfirm title="确定删除?" onConfirm={() => handleDelete(r)}>
              <Button type="link" size="small" danger icon={<DeleteOutlined />} />
            </Popconfirm>
          )}
        </Space>
      )},
  ]

  return (
    <Card>
      <Space style={{ marginBottom: 16 }}>
        <Button type="primary" icon={<PlusOutlined />}
          onClick={() => { setEditing(null); form.resetFields(); setModalOpen(true) }}>新增</Button>
        <Button icon={<ReloadOutlined />} onClick={handleRestore}>恢复预置</Button>
        <Typography.Text type="secondary">系统预置单据不可删除，只能停用</Typography.Text>
      </Space>
      <Table
        columns={columns} dataSource={items} rowKey="id"
        loading={loading} size="small" pagination={false}
        locale={{ emptyText: '暂无单据类别' }}
      />
      <Modal title={editing ? '编辑单据类别' : '新增单据类别'}
        open={modalOpen} onOk={handleSave} onCancel={() => setModalOpen(false)}
        destroyOnClose>
        <Form form={form} layout="vertical" initialValues={{ is_enabled: true, is_system: false }}>
          <Form.Item name="code" label="编码" rules={[{ required: true, message: '请输入编码' }]}>
            <Input placeholder="e.g. 1001" />
          </Form.Item>
          <Form.Item name="category" label="单据类别" rules={[{ required: true }]}>
            <Select options={['销售发票', '采购发票', '费用票据', '银行票据', '其他'].map(v => ({ value: v, label: v }))} />
          </Form.Item>
          <Form.Item name="name" label="单据名称" rules={[{ required: true }]}>
            <Input placeholder="e.g. 销售增值税发票" />
          </Form.Item>
          <Form.Item name="is_enabled" label="启用" valuePropName="checked">
            <Switch />
          </Form.Item>
        </Form>
      </Modal>
    </Card>
  )
}

// ═══════════════════════════════════════════════════════════════
// Voucher Template Tab
// ═══════════════════════════════════════════════════════════════

function VoucherTemplateTab() {
  const [templates, setTemplates] = useState<VoucherTemplate[]>([])
  const [loading, setLoading] = useState(true)
  const [modalOpen, setModalOpen] = useState(false)
  const [editing, setEditing] = useState<VoucherTemplate | null>(null)
  const [previewOpen, setPreviewOpen] = useState(false)
  const [previewTpl, setPreviewTpl] = useState<VoucherTemplate | null>(null)

  const fetchData = async () => {
    setLoading(true)
    try { setTemplates(await getVoucherTemplates()) }
    catch { message.error('加载模板失败') }
    finally { setLoading(false) }
  }

  useEffect(() => { fetchData() }, [])

  const handleToggle = async (tpl: VoucherTemplate) => {
    try {
      const updated = await toggleVoucherTemplate(tpl.id)
      setTemplates(prev => prev.map(t => t.id === updated.id ? updated : t))
      message.success(updated.is_enabled ? '已启用' : '已停用')
    } catch { message.error('操作失败') }
  }

  const handleCopy = async (tpl: VoucherTemplate) => {
    try {
      await copyVoucherTemplate(tpl.id)
      message.success('已复制')
      fetchData()
    } catch { message.error('复制失败') }
  }

  const handleDelete = async (tpl: VoucherTemplate) => {
    try {
      await deleteVoucherTemplate(tpl.id)
      message.success('已删除')
      fetchData()
    } catch { message.error('删除失败') }
  }

  const renderLines = (lines: VoucherTemplateLine[]) => (
    <div style={{ fontSize: 12, lineHeight: 1.6 }}>
      {lines.map((l) => (
        <div key={l.id} style={{ display: 'flex', gap: 4, alignItems: 'center' }}>
          <Tag color={l.debit_credit === 'debit' ? 'blue' : 'red'}
            style={{ fontSize: 11, lineHeight: '18px', padding: '0 4px', margin: 0, minWidth: 28, textAlign: 'center' }}>
            {l.debit_credit === 'debit' ? '借' : '贷'}
          </Tag>
          <span style={{ fontFamily: 'monospace' }}>{l.account_code}</span>
          <span>{l.account_name}</span>
          <Tag style={{ fontSize: 10, margin: 0 }}>{AMOUNT_SOURCES.find(s => s.value === l.amount_source)?.label || l.amount_source}</Tag>
          {l.require_sub_account && (
            <Tag color="orange" style={{ fontSize: 10, margin: 0 }}>需明细</Tag>
          )}
        </div>
      ))}
    </div>
  )

  const columns = [
    { title: '序号', key: 'idx', width: 50, render: (_: any, __: any, i: number) => i + 1 },
    { title: '单据名称', dataIndex: 'document_name', key: 'doc', width: 140 },
    { title: '结算方式', dataIndex: 'settlement_method', key: 'settlement', width: 90 },
    { title: '业务类型', dataIndex: 'business_type', key: 'biz', width: 100,
      render: (v: string) => <Tag>{v}</Tag> },
    { title: '摘要', dataIndex: 'summary_template', key: 'summary', width: 150, ellipsis: true },
    { title: '分录', dataIndex: 'lines', key: 'lines',
      render: (lines: VoucherTemplateLine[]) => renderLines(lines) },
    { title: '状态', dataIndex: 'is_enabled', key: 'status', width: 60,
      render: (v: boolean) => <Badge status={v ? 'success' : 'default'} /> },
    { title: '操作', key: 'action', width: 200, fixed: 'right' as const,
      render: (_: any, r: VoucherTemplate) => (
        <Space size={0}>
          <Tooltip title="预览"><Button type="link" size="small" icon={<EyeOutlined />}
            onClick={() => { setPreviewTpl(r); setPreviewOpen(true) }} /></Tooltip>
          <Tooltip title="编辑"><Button type="link" size="small" icon={<EditOutlined />}
            onClick={() => { setEditing(r); setModalOpen(true) }} /></Tooltip>
          <Tooltip title="复制"><Button type="link" size="small" icon={<CopyOutlined />}
            onClick={() => handleCopy(r)} /></Tooltip>
          <Tooltip title={r.is_enabled ? '停用' : '启用'}>
            <Button type="link" size="small"
              icon={r.is_enabled ? <PauseCircleOutlined /> : <PlayCircleOutlined />}
              onClick={() => handleToggle(r)} />
          </Tooltip>
          <Popconfirm title="确定删除?" onConfirm={() => handleDelete(r)}>
            <Button type="link" size="small" danger icon={<DeleteOutlined />} />
          </Popconfirm>
        </Space>
      )},
  ]

  return (
    <Card>
      <Space style={{ marginBottom: 16 }}>
        <Button type="primary" icon={<PlusOutlined />}
          onClick={() => { setEditing(null); setModalOpen(true) }}>新增模板</Button>
        <Typography.Text type="secondary">
          共 {templates.length} 个模板（停用的不参与匹配）
        </Typography.Text>
      </Space>
      <Table
        columns={columns} dataSource={templates} rowKey="id"
        loading={loading} size="small" pagination={false}
        scroll={{ x: 1000 }}
        locale={{ emptyText: '暂无分录模板' }}
      />
      <TemplateEditModal
        open={modalOpen}
        template={editing}
        onClose={() => setModalOpen(false)}
        onSaved={fetchData}
      />
      <TemplatePreviewModal
        open={previewOpen}
        template={previewTpl}
        onClose={() => setPreviewOpen(false)}
      />
    </Card>
  )
}

// ═══════════════════════════════════════════════════════════════
// Template Edit Modal
// ═══════════════════════════════════════════════════════════════

function TemplateEditModal({
  open, template, onClose, onSaved,
}: {
  open: boolean; template: VoucherTemplate | null; onClose: () => void; onSaved: () => void;
}) {
  const [docTypes, setDocTypes] = useState<DocumentType[]>([])
  const [subjects, setSubjects] = useState<SubjectTreeNode[]>([])
  const [saving, setSaving] = useState(false)
  const [form] = Form.useForm()

  useEffect(() => {
    if (open) {
      getDocumentTypes(true).then(setDocTypes).catch(() => {})
      getSubjectTree().then(setSubjects).catch(() => {})
    }
  }, [open])

  useEffect(() => {
    if (template && open) {
      form.setFieldsValue({
        document_type_id: template.document_type_id,
        document_name: template.document_name,
        settlement_method: template.settlement_method,
        business_type: template.business_type,
        summary_template: template.summary_template,
        priority: template.priority,
        is_enabled: template.is_enabled,
        lines: template.lines.map(l => ({
          line_no: l.line_no,
          debit_credit: l.debit_credit,
          account_code: l.account_code,
          account_name: l.account_name,
          account_full_name: l.account_full_name,
          parent_account_code: l.parent_account_code,
          amount_source: l.amount_source,
          require_sub_account: l.require_sub_account,
          sub_account_match_mode: l.sub_account_match_mode,
          allow_manual_edit: l.allow_manual_edit,
        })),
      })
    } else if (open) {
      form.resetFields()
      form.setFieldsValue({
        settlement_method: '往来结算',
        priority: 0,
        is_enabled: true,
        lines: [
          { line_no: 1, debit_credit: 'debit', account_code: '', account_name: '',
            amount_source: 'totalAmount', require_sub_account: false,
            sub_account_match_mode: 'none', allow_manual_edit: true },
          { line_no: 2, debit_credit: 'credit', account_code: '', account_name: '',
            amount_source: 'totalAmount', require_sub_account: false,
            sub_account_match_mode: 'none', allow_manual_edit: true },
        ],
      })
    }
  }, [template, open, form])

  const flattenSubjects = (nodes: SubjectTreeNode[]): { value: string; label: string }[] => {
    let result: { value: string; label: string }[] = []
    for (const n of nodes) {
      result.push({ value: n.code, label: n.full_name || `${n.code} ${n.name}` })
      if (n.children?.length) result = result.concat(flattenSubjects(n.children))
    }
    return result
  }

  const subjectOptions = flattenSubjects(subjects)

  const handleSave = async () => {
    const values = await form.validateFields()
    setSaving(true)
    try {
      const payload = {
        ...values,
        document_type_id: values.document_type_id || null,
        lines: values.lines.map((l: any, i: number) => ({
          ...l, line_no: i + 1,
        })),
      }
      if (template) {
        await updateVoucherTemplate(template.id, payload)
        message.success('已更新')
      } else {
        await createVoucherTemplate(payload)
        message.success('已创建')
      }
      onSaved()
      onClose()
    } catch (err: any) {
      message.error(err.response?.data?.detail || err.message || '保存失败')
    } finally { setSaving(false) }
  }

  return (
    <Modal
      title={template ? '编辑分录模板' : '新增分录模板'}
      open={open}
      onOk={handleSave}
      onCancel={onClose}
      confirmLoading={saving}
      width={900}
      destroyOnClose
      style={{ top: 20 }}
    >
      <Form form={form} layout="vertical">
        <Space style={{ width: '100%' }} size={16}>
          <Form.Item name="document_name" label="单据名称" rules={[{ required: true }]}
            style={{ width: 180 }}>
            <Select showSearch placeholder="选择"
              filterOption={(i, o) => (o?.label ?? '').includes(i)}
              options={docTypes.map(d => ({ value: d.name, label: `${d.code} ${d.name}` }))}
              onChange={(v) => {
                const dt = docTypes.find(d => d.name === v)
                form.setFieldValue('document_type_id', dt?.id || null)
              }}
            />
          </Form.Item>
          <Form.Item name="settlement_method" label="结算方式" rules={[{ required: true }]}
            style={{ width: 120 }}>
            <Select options={SETTLEMENT_OPTIONS.map(v => ({ value: v, label: v }))} />
          </Form.Item>
          <Form.Item name="business_type" label="业务类型" rules={[{ required: true }]}
            style={{ width: 140 }}>
            <Select showSearch options={BUSINESS_TYPES.map(v => ({ value: v, label: v }))} />
          </Form.Item>
          <Form.Item name="priority" label="优先级" style={{ width: 70 }}>
            <InputNumber min={0} max={100} />
          </Form.Item>
          <Form.Item name="is_enabled" label="启用" valuePropName="checked">
            <Switch />
          </Form.Item>
        </Space>
        <Form.Item name="summary_template" label="摘要模板"
          rules={[{ required: true }]}
          help="支持变量: {counterpartyName}, {month}, {date} 等">
          <Input placeholder="e.g. 销售收入" />
        </Form.Item>
        <Form.Item name="document_type_id" hidden><Input /></Form.Item>
        <Typography.Text strong>分录行</Typography.Text>
        <Form.List name="lines">
          {(fields, { add, remove }) => (
            <div style={{ border: '1px solid #f0f0f0', borderRadius: 8, padding: 12, marginTop: 8 }}>
              {fields.map(({ key, name, ...rest }, index) => (
                <div key={key} style={{
                  display: 'flex', gap: 8, alignItems: 'center',
                  padding: '6px 0', borderBottom: index < fields.length - 1 ? '1px solid #f5f5f5' : 'none',
                }}>
                  <span style={{ width: 20, textAlign: 'center', color: '#888' }}>{index + 1}</span>
                  <Form.Item {...rest} name={[name, 'debit_credit']} noStyle rules={[{ required: true }]}>
                    <Select style={{ width: 70 }} options={[
                      { value: 'debit', label: '借' }, { value: 'credit', label: '贷' },
                    ]} />
                  </Form.Item>
                  <Form.Item {...rest} name={[name, 'account_code']} noStyle rules={[{ required: true }]}>
                    <Select showSearch style={{ width: 140 }} placeholder="科目代码"
                      filterOption={(input, option) =>
                        (option?.label ?? '').includes(input) || (option?.value ?? '').includes(input)
                      }
                      options={subjectOptions}
                      onChange={(v) => {
                        const found = subjectOptions.find(o => o.value === v)
                        const names = form.getFieldValue('lines')
                        names[name].account_name = found?.label?.split(' ').slice(1).join(' ') || ''
                        names[name].account_full_name = found?.label || ''
                        form.setFieldsValue({ lines: names })
                      }}
                    />
                  </Form.Item>
                  <Form.Item {...rest} name={[name, 'account_name']} noStyle>
                    <Input style={{ width: 120 }} placeholder="科目名称" />
                  </Form.Item>
                  <Form.Item {...rest} name={[name, 'amount_source']} noStyle>
                    <Select style={{ width: 100 }} options={AMOUNT_SOURCES} />
                  </Form.Item>
                  <Form.Item {...rest} name={[name, 'require_sub_account']} noStyle valuePropName="checked">
                    <Switch checkedChildren="明细" unCheckedChildren="明细" size="small" />
                  </Form.Item>
                  {form.getFieldValue(['lines', name, 'require_sub_account']) && (
                    <Form.Item {...rest} name={[name, 'sub_account_match_mode']} noStyle>
                      <Select style={{ width: 80 }} size="small" options={SUB_MATCH_MODES} />
                    </Form.Item>
                  )}
                  <Button type="link" danger size="small" icon={<DeleteOutlined />}
                    onClick={() => remove(name)} disabled={fields.length <= 2} />
                </div>
              ))}
              <Button type="dashed" block icon={<PlusOutlined />}
                onClick={() => add({
                  line_no: fields.length + 1,
                  debit_credit: 'debit',
                  account_code: '',
                  account_name: '',
                  amount_source: 'totalAmount',
                  require_sub_account: false,
                  sub_account_match_mode: 'none',
                  allow_manual_edit: true,
                })}
                style={{ marginTop: 8 }}>
                添加分录行
              </Button>
            </div>
          )}
        </Form.List>
      </Form>
    </Modal>
  )
}

// ═══════════════════════════════════════════════════════════════
// Template Preview Modal
// ═══════════════════════════════════════════════════════════════

function TemplatePreviewModal({
  open, template, onClose,
}: { open: boolean; template: VoucherTemplate | null; onClose: () => void }) {
  if (!template) return null

  return (
    <Modal title="模板预览" open={open} onCancel={onClose} footer={null} width={600}>
      <Descriptions column={2} size="small" bordered>
        <Descriptions.Item label="单据名称">{template.document_name}</Descriptions.Item>
        <Descriptions.Item label="结算方式">{template.settlement_method}</Descriptions.Item>
        <Descriptions.Item label="业务类型">{template.business_type}</Descriptions.Item>
        <Descriptions.Item label="优先级">{template.priority}</Descriptions.Item>
        <Descriptions.Item label="摘要" span={2}>{template.summary_template}</Descriptions.Item>
      </Descriptions>
      <Typography.Text strong style={{ display: 'block', marginTop: 16, marginBottom: 8 }}>
        分录明细
      </Typography.Text>
      <Table
        dataSource={template.lines}
        rowKey="id"
        size="small"
        pagination={false}
        columns={[
          { title: '行号', dataIndex: 'line_no', width: 50 },
          { title: '方向', dataIndex: 'debit_credit', width: 50,
            render: (v: string) => <Tag color={v === 'debit' ? 'blue' : 'red'}>{v === 'debit' ? '借' : '贷'}</Tag> },
          { title: '科目代码', dataIndex: 'account_code', width: 100 },
          { title: '科目名称', dataIndex: 'account_name' },
          { title: '金额来源', dataIndex: 'amount_source', width: 100,
            render: (v: string) => AMOUNT_SOURCES.find(s => s.value === v)?.label || v },
          { title: '需明细', dataIndex: 'require_sub_account', width: 60,
            render: (v: boolean) => v ? <Tag color="orange">是</Tag> : '-' },
        ]}
      />
    </Modal>
  )
}

