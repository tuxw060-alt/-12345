import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import {
  Card, Table, Button, Space, Typography, Input, DatePicker,
  Select, InputNumber, message, Tag, Popconfirm, Row, Col,
} from 'antd'
import {
  SaveOutlined, PlusOutlined, DeleteOutlined, ArrowLeftOutlined,
  CheckOutlined,
} from '@ant-design/icons'
import { getEntry, updateEntry, confirmEntry, deleteEntry } from '../api/entries'
import { getSubjectTree } from '../api/subjects'
import type { JournalEntry, JournalEntryLine, SubjectTreeNode } from '../types/invoice'
import dayjs from 'dayjs'

export default function EntryEditor() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [entry, setEntry] = useState<JournalEntry | null>(null)
  const [loading, setLoading] = useState(true)
  const [subjects, setSubjects] = useState<SubjectTreeNode[]>([])
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    if (id) {
      getEntry(id).then((data) => {
        setEntry(data)
        setLoading(false)
      })
    }
    getSubjectTree().then(setSubjects)
  }, [id])

  const handleHeaderChange = (field: string, value: any) => {
    if (!entry) return
    setEntry({ ...entry, [field]: value })
  }

  const handleLineChange = (lineId: string, field: string, value: any) => {
    if (!entry) return
    setEntry({
      ...entry,
      lines: entry.lines.map((l) =>
        l.id === lineId ? { ...l, [field]: value } : l
      ),
    })
  }

  const addLine = () => {
    if (!entry) return
    const maxNum = entry.lines.reduce((m, l) => Math.max(m, l.line_number), 0)
    const newLine: JournalEntryLine = {
      id: `new_${Date.now()}`,
      entry_id: entry.id,
      line_number: maxNum + 1,
      account_code: '',
      account_name: '',
      direction: 'debit',
      amount: 0,
      summary_detail: '',
    }
    setEntry({ ...entry, lines: [...entry.lines, newLine] })
  }

  const removeLine = (lineId: string) => {
    if (!entry || entry.lines.length <= 2) {
      message.warning('凭证至少保留 2 行分录')
      return
    }
    setEntry({
      ...entry,
      lines: entry.lines.filter((l) => l.id !== lineId),
    })
  }

  const flattenSubjects = (nodes: SubjectTreeNode[], prefix = ''): { value: string; label: string }[] => {
    let result: { value: string; label: string }[] = []
    for (const n of nodes) {
      const label = n.full_name || `${n.code} ${n.name}`
      result.push({ value: n.code, label })
      if (n.children?.length) {
        result = result.concat(flattenSubjects(n.children, ''))
      }
    }
    return result
  }

  const handleSave = async () => {
    if (!entry || !id) return
    setSaving(true)
    try {
      await updateEntry(id, {
        voucher_date: entry.voucher_date,
        voucher_type: entry.voucher_type,
        voucher_number: entry.voucher_number,
        summary: entry.summary,
        lines: entry.lines.map((l) => ({
          line_number: l.line_number,
          account_code: l.account_code,
          account_name: l.account_name,
          direction: l.direction,
          amount: l.amount,
          summary_detail: l.summary_detail ?? undefined,
        })),
      })
      message.success('已保存')
    } catch (err: any) {
      message.error(`保存失败: ${err.message}`)
    } finally {
      setSaving(false)
    }
  }

  const handleConfirm = async () => {
    if (!entry || !id) return
    try {
      await confirmEntry(id)
      message.success('凭证已确认，可以导出了')
      navigate('/entries')
    } catch (err: any) {
      message.error(`确认失败: ${err.message}`)
    }
  }

  if (!entry) return <Typography.Text type="danger">凭证不存在</Typography.Text>

  const debitTotal = entry.lines.filter((l) => l.direction === 'debit').reduce((s, l) => s + l.amount, 0)
  const creditTotal = entry.lines.filter((l) => l.direction === 'credit').reduce((s, l) => s + l.amount, 0)
  const balanced = Math.abs(debitTotal - creditTotal) < 0.01

  const subjectOptions = flattenSubjects(subjects)

  const columns = [
    {
      title: '行号', dataIndex: 'line_number', key: 'num', width: 60,
    },
    {
      title: '科目代码', dataIndex: 'account_code', key: 'code', width: 160,
      render: (_: any, record: JournalEntryLine) => (
        <Select
          showSearch
          value={record.account_code || undefined}
          onChange={(v) => {
            const found = subjectOptions.find((o) => o.value === v)
            handleLineChange(record.id, 'account_code', v)
            handleLineChange(record.id, 'account_name', found?.label?.split(' ').slice(1).join(' ') || '')
          }}
          options={subjectOptions}
          style={{ width: '100%' }}
          placeholder="选择科目"
          filterOption={(input, option) =>
            (option?.label ?? '').includes(input) || (option?.value ?? '').includes(input)
          }
        />
      ),
    },
    {
      title: '科目名称', dataIndex: 'account_name', key: 'name', width: 180,
      render: (v: string) => v || '-',
    },
    {
      title: '方向', dataIndex: 'direction', key: 'dir', width: 80,
      render: (v: string, record: JournalEntryLine) => (
        <Select
          value={v}
          onChange={(val) => handleLineChange(record.id, 'direction', val)}
          style={{ width: '100%' }}
          options={[
            { value: 'debit', label: '借' },
            { value: 'credit', label: '贷' },
          ]}
        />
      ),
    },
    {
      title: '金额', dataIndex: 'amount', key: 'amount', width: 150,
      render: (_: any, record: JournalEntryLine) => (
        <InputNumber
          value={record.amount}
          onChange={(v) => handleLineChange(record.id, 'amount', v || 0)}
          prefix="¥"
          style={{ width: '100%' }}
        />
      ),
    },
    {
      title: '明细说明', dataIndex: 'summary_detail', key: 'detail',
      render: (v: string | null, record: JournalEntryLine) => (
        <Input
          value={v || ''}
          onChange={(e) => handleLineChange(record.id, 'summary_detail', e.target.value)}
        />
      ),
    },
    {
      title: '操作', key: 'op', width: 60,
      render: (_: any, record: JournalEntryLine) => (
        <Button
          type="link"
          danger
          icon={<DeleteOutlined />}
          onClick={() => removeLine(record.id)}
        />
      ),
    },
  ]

  return (
    <div>
      <Space style={{ marginBottom: 16 }}>
        <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/entries')}>返回</Button>
        <Typography.Title level={4} style={{ margin: 0 }}>编辑凭证</Typography.Title>
        <Tag color={entry.status === 'draft' ? 'blue' : entry.status === 'confirmed' ? 'green' : 'default'}>
          {entry.status === 'draft' ? '草稿' : entry.status === 'confirmed' ? '已确认' : '已导出'}
        </Tag>
      </Space>

      <Card style={{ marginBottom: 16 }}>
        <Row gutter={16}>
          <Col span={6}>
            <Typography.Text type="secondary">凭证日期</Typography.Text>
            <DatePicker
              value={entry.voucher_date ? dayjs(entry.voucher_date) : null}
              onChange={(d) => handleHeaderChange('voucher_date', d?.format('YYYY-MM-DD') || '')}
              style={{ width: '100%' }}
            />
          </Col>
          <Col span={4}>
            <Typography.Text type="secondary">凭证字</Typography.Text>
            <Select
              value={entry.voucher_type}
              onChange={(v) => handleHeaderChange('voucher_type', v)}
              style={{ width: '100%' }}
              options={[
                { value: '记', label: '记' },
                { value: '收', label: '收' },
                { value: '付', label: '付' },
                { value: '转', label: '转' },
              ]}
            />
          </Col>
          <Col span={4}>
            <Typography.Text type="secondary">凭证号</Typography.Text>
            <Input
              value={entry.voucher_number || ''}
              onChange={(e) => handleHeaderChange('voucher_number', e.target.value)}
              placeholder="自动编号"
            />
          </Col>
          <Col span={10}>
            <Typography.Text type="secondary">摘要</Typography.Text>
            <Input
              value={entry.summary}
              onChange={(e) => handleHeaderChange('summary', e.target.value)}
            />
          </Col>
        </Row>
      </Card>

      <Card>
        <Table
          columns={columns}
          dataSource={entry.lines}
          rowKey="id"
          pagination={false}
          size="small"
          footer={() => (
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <Button icon={<PlusOutlined />} onClick={addLine} type="dashed">
                添加分录行
              </Button>
              <Space>
                <Typography.Text>
                  借方合计: <span style={{ color: '#1677ff', fontWeight: 600 }}>¥{debitTotal.toFixed(2)}</span>
                  {' | '}
                  贷方合计: <span style={{ color: '#ff4d4f', fontWeight: 600 }}>¥{creditTotal.toFixed(2)}</span>
                </Typography.Text>
                <Tag color={balanced ? 'green' : 'red'}>
                  {balanced ? '✓ 借贷平衡' : `✗ 差额 ¥${Math.abs(debitTotal - creditTotal).toFixed(2)}`}
                </Tag>
              </Space>
            </div>
          )}
        />

        <Space style={{ marginTop: 16 }}>
          <Button
            type="primary"
            icon={<SaveOutlined />}
            onClick={handleSave}
            loading={saving}
          >
            保存草稿
          </Button>
          <Button
            icon={<CheckOutlined />}
            onClick={handleConfirm}
            disabled={!balanced}
            style={{ background: '#52c41a', borderColor: '#52c41a', color: '#fff' }}
          >
            确认凭证
          </Button>
        </Space>
      </Card>
    </div>
  )
}
