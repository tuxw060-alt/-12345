import { useState, useRef } from 'react'
import {
  Card, Table, Button, Space, Typography, Tag, message, Select, DatePicker,
  Checkbox, Row, Col,
} from 'antd'
import { UploadOutlined, ThunderboltOutlined, BankOutlined } from '@ant-design/icons'
import { useAppStore } from '../hooks/useAppStore'
import api from '../api/client'
import dayjs from 'dayjs'

export default function BankImport() {
  const [txns, setTxns] = useState<any[]>([])
  const [selected, setSelected] = useState<Set<number>>(new Set())
  const [filename, setFilename] = useState('')
  const [loading, setLoading] = useState(false)
  const [generating, setGenerating] = useState(false)
  const [voucherDate, setVoucherDate] = useState(dayjs().format('YYYY-MM-DD'))
  const fileInputRef = useRef<HTMLInputElement>(null)
  const { currentClient } = useAppStore()

  const handleUpload = async (file: File) => {
    if (!currentClient) { message.warning('请先选择客户'); return }
    setLoading(true)
    setFilename(file.name)
    try {
      const form = new FormData()
      form.append('file', file)
      const res = await api.post('/bank/upload', form, {
        params: { client_id: currentClient.id },
        headers: { 'Content-Type': 'multipart/form-data' },
      })
      setTxns(res.data.transactions)
      setSelected(new Set(res.data.transactions.map((_: any, i: number) => i)))
      message.success(`解析到 ${res.data.total} 条交易`)
    } catch (err: any) {
      message.error(err.response?.data?.detail || '解析失败')
    } finally {
      setLoading(false)
    }
  }

  const handleGenerate = async () => {
    if (!currentClient) return
    const selectedTxns = Array.from(selected).map((i) => txns[i])
    if (selectedTxns.length === 0) { message.warning('请勾选要生成的交易'); return }
    setGenerating(true)
    try {
      const res = await api.post('/bank/generate', {
        client_id: currentClient.id,
        transactions: selectedTxns,
        voucher_date: voucherDate,
      })
      message.success(`已生成 ${res.data.created} 张凭证`)
      setTxns((prev) => prev.filter((_: any, i: number) => !selected.has(i)))
      setSelected(new Set())
    } catch (err: any) {
      message.error(err.response?.data?.detail || '生成失败')
    } finally {
      setGenerating(false)
    }
  }

  const toggleSelect = (idx: number) => {
    const next = new Set(selected)
    if (next.has(idx)) next.delete(idx)
    else next.add(idx)
    setSelected(next)
  }

  const columns = [
    {
      title: '', width: 40,
      render: (_: any, __: any, idx: number) => (
        <Checkbox checked={selected.has(idx)} onChange={() => toggleSelect(idx)} />
      ),
    },
    { title: '日期', dataIndex: 'date', key: 'date', width: 110 },
    { title: '摘要', dataIndex: 'description', key: 'desc', ellipsis: true },
    {
      title: '收入', dataIndex: 'income', key: 'in', width: 130,
      render: (v: number) => v > 0 ? <span style={{ color: '#52c41a' }}>¥{v.toFixed(2)}</span> : '-',
    },
    {
      title: '支出', dataIndex: 'expense', key: 'out', width: 130,
      render: (v: number) => v > 0 ? <span style={{ color: '#ff4d4f' }}>¥{v.toFixed(2)}</span> : '-',
    },
    { title: '对方', dataIndex: 'counterparty', key: 'cp', width: 120, ellipsis: true },
    {
      title: '匹配科目', key: 'match', width: 150,
      render: (_: any, r: any) => (
        <Space>
          <Tag color={r.auto_matched ? 'green' : 'orange'}>
            {r.suggested_name || '未匹配'}
          </Tag>
        </Space>
      ),
    },
  ]

  const totalIncome = txns.reduce((s: number, t: any) => s + (t.income || 0), 0)
  const totalExpense = txns.reduce((s: number, t: any) => s + (t.expense || 0), 0)

  return (
    <div>
      <Typography.Title level={4}>银行流水导入</Typography.Title>

      <Card style={{ marginBottom: 16 }}>
        <Typography.Paragraph type="secondary">
          上传银行流水文件（CSV 或 Excel），系统自动匹配科目并生成记账凭证。
          支持工商银行、建设银行、农业银行、中国银行等主流银行格式。
        </Typography.Paragraph>

        <Space>
          <Button type="primary" icon={<UploadOutlined />} loading={loading}
            onClick={() => fileInputRef.current?.click()}>
            选择流水文件
          </Button>
          <input ref={fileInputRef} type="file" accept=".csv,.xlsx,.xls"
            style={{ display: 'none' }}
            onChange={(e) => { if (e.target.files?.[0]) handleUpload(e.target.files[0]); e.target.value = '' }} />
          {filename && <Tag>{filename}</Tag>}
        </Space>
      </Card>

      {txns.length > 0 && (
        <>
          <Row gutter={16} style={{ marginBottom: 16 }}>
            <Col span={6}><Card size="small"><Stat title="交易笔数" value={txns.length} /></Card></Col>
            <Col span={6}><Card size="small"><Stat title="收入合计" value={`¥${totalIncome.toFixed(2)}`} color="#52c41a" /></Card></Col>
            <Col span={6}><Card size="small"><Stat title="支出合计" value={`¥${totalExpense.toFixed(2)}`} color="#ff4d4f" /></Card></Col>
            <Col span={6}><Card size="small"><Stat title="已勾选" value={selected.size} color="#1677ff" /></Card></Col>
          </Row>

          <Card size="small" style={{ marginBottom: 16 }}>
            <Space>
              <Typography.Text>凭证日期:</Typography.Text>
              <DatePicker value={dayjs(voucherDate)} onChange={(d) => setVoucherDate(d?.format('YYYY-MM-DD') || '')} />
              <Button type="primary" icon={<ThunderboltOutlined />} onClick={handleGenerate}
                loading={generating} disabled={selected.size === 0}
                style={{ background: '#52c41a', borderColor: '#52c41a' }}>
                生成 {selected.size} 张凭证
              </Button>
              <Button onClick={() => setSelected(new Set(txns.map((_: any, i: number) => i)))}>全选</Button>
              <Button onClick={() => setSelected(new Set())}>取消全选</Button>
            </Space>
          </Card>

          <Table columns={columns} dataSource={txns} rowKey={(_, i) => String(i)}
            size="small" pagination={{ pageSize: 50 }} scroll={{ y: 500 }} />
        </>
      )}
    </div>
  )
}

function Stat({ title, value, color }: { title: string; value: string | number; color?: string }) {
  return (
    <div style={{ textAlign: 'center' }}>
      <Typography.Text type="secondary">{title}</Typography.Text>
      <Typography.Title level={5} style={{ margin: 0, color }}>{value}</Typography.Title>
    </div>
  )
}
