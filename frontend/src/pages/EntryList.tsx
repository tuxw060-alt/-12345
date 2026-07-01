import { useEffect, useState } from 'react'
import { Card, Table, Tag, Button, Space, Typography, Popconfirm, message, Modal, List, DatePicker } from 'antd'
import { CheckOutlined, DeleteOutlined, EyeOutlined, ThunderboltOutlined } from '@ant-design/icons'
import { listEntries, confirmEntry, deleteEntry } from '../api/entries'
import { listTemplates, applyTemplate, type EntryTemplate } from '../api/templates'
import axios from 'axios'
import { useAppStore } from '../hooks/useAppStore'
import { useNavigate } from 'react-router-dom'
import type { JournalEntry } from '../types/invoice'
import dayjs from 'dayjs'

export default function EntryList() {
  const [entries, setEntries] = useState<JournalEntry[]>([])
  const [templates, setTemplates] = useState<EntryTemplate[]>([])
  const [tplModalOpen, setTplModalOpen] = useState(false)
  const [tplDate, setTplDate] = useState(dayjs().format('YYYY-MM-DD'))
  const [loading, setLoading] = useState(true)
  const [selectedIds, setSelectedIds] = useState<string[]>([])
  const [batchLoading, setBatchLoading] = useState(false)
  const { currentClient } = useAppStore()
  const navigate = useNavigate()

  const fetchEntries = () => {
    setLoading(true)
    listEntries({ client_id: currentClient?.id, limit: 200 })
      .then((r) => setEntries(r.items))
      .finally(() => setLoading(false))
  }

  useEffect(() => { fetchEntries() }, [currentClient])

  const handleConfirm = async (id: string) => {
    await confirmEntry(id)
    message.success('已确认')
    fetchEntries()
  }

  const handleDelete = async (id: string) => {
    await deleteEntry(id)
    message.success('已删除')
    fetchEntries()
  }

  const handleApplyTemplate = async (tpl: EntryTemplate) => {
    if (!currentClient) { message.warning('请先选择客户'); return }
    try {
      const entry = await applyTemplate({
        template_id: tpl.id,
        client_id: currentClient.id,
        voucher_date: tplDate,
      })
      message.success(`已应用模板"${tpl.name}"`)
      setTplModalOpen(false)
      navigate(`/entries/${entry.id}/edit`)
    } catch (err: any) {
      message.error(err.response?.data?.detail || '应用失败')
    }
  }

  const openTemplates = () => {
    if (!currentClient) { message.warning('请先选择客户'); return }
    listTemplates(currentClient.id).then((res) => setTemplates(res.items))
    setTplModalOpen(true)
  }

  const handleBatchConfirm = async () => {
    if (selectedIds.length === 0) return
    setBatchLoading(true)
    try {
      const res = await axios.post('/api/v1/entries/batch-confirm', selectedIds)
      const { confirmed, failed } = res.data
      if (confirmed > 0) message.success(`已确认 ${confirmed} 张凭证`)
      if (failed?.length > 0) {
        const reasons = failed.map((f: any) => `${f.id.slice(0, 8)}...: ${f.reason}`).join('; ')
        message.warning(`${failed.length} 张失败: ${reasons}`)
      }
      setSelectedIds([])
      fetchEntries()
    } catch (err: any) {
      message.error('批量确认失败')
    } finally {
      setBatchLoading(false)
    }
  }

  const rowSelection = {
    selectedRowKeys: selectedIds,
    onChange: (keys: React.Key[]) => setSelectedIds(keys as string[]),
    getCheckboxProps: (record: JournalEntry) => ({
      disabled: record.status !== 'draft',
    }),
  }

  const statusTag = (s: string) => {
    const map: Record<string, { color: string; text: string }> = {
      draft: { color: 'blue', text: '草稿' },
      confirmed: { color: 'green', text: '已确认' },
      exported: { color: 'default', text: '已导出' },
    }
    const m = map[s] || { color: 'default', text: s }
    return <Tag color={m.color}>{m.text}</Tag>
  }

  const columns = [
    { title: '日期', dataIndex: 'voucher_date', key: 'date', width: 110,
      render: (v: string) => dayjs(v).format('YYYY-MM-DD') },
    { title: '字', dataIndex: 'voucher_type', key: 'type', width: 50 },
    { title: '号', dataIndex: 'voucher_number', key: 'number', width: 60,
      render: (v: string | null) => v || '-' },
    { title: '摘要', dataIndex: 'summary', key: 'summary', ellipsis: true },
    { title: '分录', key: 'lines', width: 50,
      render: (_: any, r: JournalEntry) => r.lines?.length || 0 },
    { title: '借方', key: 'debit', width: 120,
      render: (_: any, r: JournalEntry) => {
        const t = r.lines?.filter((l) => l.direction === 'debit').reduce((s, l) => s + l.amount, 0) || 0
        return <span style={{ color: '#1677ff' }}>¥{t.toFixed(2)}</span>
      }},
    { title: '贷方', key: 'credit', width: 120,
      render: (_: any, r: JournalEntry) => {
        const t = r.lines?.filter((l) => l.direction === 'credit').reduce((s, l) => s + l.amount, 0) || 0
        return <span style={{ color: '#ff4d4f' }}>¥{t.toFixed(2)}</span>
      }},
    { title: '状态', dataIndex: 'status', key: 'status', width: 80, render: statusTag },
    { title: '操作', key: 'action', width: 140,
      render: (_: any, r: JournalEntry) => (
        <Space size={0}>
          <Button type="link" size="small" icon={<EyeOutlined />}
            onClick={() => navigate(`/entries/${r.id}/edit`)}>查看</Button>
          {r.status === 'draft' && (
            <>
              <Button type="link" size="small" icon={<CheckOutlined />}
                onClick={() => handleConfirm(r.id)}>确认</Button>
              <Popconfirm title="删除?" onConfirm={() => handleDelete(r.id)}>
                <Button type="link" size="small" danger icon={<DeleteOutlined />} />
              </Popconfirm>
            </>
          )}
        </Space>
      )},
  ]

  const draftCount = entries.filter((e) => e.status === 'draft').length

  return (
    <div>
      <Space style={{ marginBottom: 16, width: '100%', justifyContent: 'space-between' }}>
        <Typography.Title level={4} style={{ margin: 0 }}>
          记账凭证
          {draftCount > 0 && <Tag style={{ marginLeft: 8 }} color="blue">{draftCount} 张草稿</Tag>}
        </Typography.Title>
        <Space>
          <Button icon={<ThunderboltOutlined />} onClick={openTemplates}>快速凭证</Button>
          {selectedIds.length > 0 && (
            <Button
              type="primary"
              icon={<CheckOutlined />}
              onClick={handleBatchConfirm}
              loading={batchLoading}
              style={{ background: '#52c41a', borderColor: '#52c41a' }}
            >
              批量确认 ({selectedIds.length})
            </Button>
          )}
        </Space>
      </Space>

      <Card>
        <Table
          rowSelection={rowSelection}
          columns={columns}
          dataSource={entries}
          rowKey="id"
          loading={loading}
          size="small"
          pagination={{ pageSize: 50, showTotal: (t) => `共 ${t} 张凭证` }}
          locale={{ emptyText: '暂无凭证，请先上传发票并生成凭证' }}
        />
      </Card>

      <Modal
        title="快速凭证模板"
        open={tplModalOpen}
        onCancel={() => setTplModalOpen(false)}
        footer={null}
        width={600}
      >
        <Space style={{ marginBottom: 16 }}>
          <Typography.Text>凭证日期:</Typography.Text>
          <DatePicker value={dayjs(tplDate)} onChange={(d) => setTplDate(d?.format('YYYY-MM-DD') || '')} />
        </Space>
        <List
          dataSource={templates}
          renderItem={(tpl: EntryTemplate) => (
            <List.Item
              actions={[
                <Button type="primary" size="small" icon={<ThunderboltOutlined />}
                  onClick={() => handleApplyTemplate(tpl)}>应用</Button>,
              ]}
            >
              <List.Item.Meta
                title={tpl.name}
                description={
                  <Space wrap>
                    <Tag>{tpl.voucher_type}</Tag>
                    <span>{tpl.summary_template}</span>
                    <Typography.Text type="secondary">
                      {tpl.lines.length}行分录
                    </Typography.Text>
                  </Space>
                }
              />
            </List.Item>
          )}
          locale={{ emptyText: '暂无凭证模板' }}
        />
      </Modal>
    </div>
  )
}
