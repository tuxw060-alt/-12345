import { useState, useRef } from 'react'
import {
  Card,
  Space,
  Typography,
  message,
  Table,
  Tag,
  Progress,
  Switch,
  Button,
  Popconfirm,
} from 'antd'
import {
  InboxOutlined,
  FilePdfOutlined,
  FileImageOutlined,
  ThunderboltOutlined,
  DeleteOutlined,
} from '@ant-design/icons'
import { batchUpload, deleteInvoice } from '../api/invoices'
import { useAppStore } from '../hooks/useAppStore'
import { useNavigate } from 'react-router-dom'
import type { UploadResult } from '../api/invoices'
import dayjs from 'dayjs'

export default function InvoiceUpload() {
  const [uploading, setUploading] = useState(false)
  const [results, setResults] = useState<UploadResult[]>([])
  const [autoGenerate, setAutoGenerate] = useState(true)
  const [progress, setProgress] = useState({ done: 0, total: 0 })
  const fileInputRef = useRef<HTMLInputElement>(null)
  const { currentClient } = useAppStore()
  const navigate = useNavigate()

  const doUpload = async (files: FileList | File[]) => {
    if (!currentClient) {
      message.warning('请先在顶部选择要记账的客户')
      return
    }

    const fileArray = Array.from(files)
    if (fileArray.length === 0) return

    setUploading(true)
    setProgress({ done: 0, total: fileArray.length })

    // Upload files in parallel with individual progress
    const allResults: UploadResult[] = []
    const batchSize = 5 // Upload 5 at a time to avoid overwhelming the server

    for (let i = 0; i < fileArray.length; i += batchSize) {
      const batch = fileArray.slice(i, i + batchSize)
      const batchResults = await batchUpload(batch, currentClient.id, autoGenerate)
      allResults.push(...batchResults)
      setProgress({ done: Math.min(i + batchSize, fileArray.length), total: fileArray.length })
    }

    setResults((prev) => [...allResults, ...prev])
    setUploading(false)

    const successCount = allResults.filter((r) => r.invoice.ocr_status === 'done').length
    const failCount = allResults.filter((r) => r.invoice.ocr_status === 'failed').length
    const entryCount = allResults.filter((r) => r.entry_id).length

    if (successCount > 0) {
      let msg = `${successCount} 个文件识别成功`
      if (entryCount > 0) msg += `，${entryCount} 个凭证已自动生成`
      message.success(msg)
    }
    if (failCount > 0) {
      message.error(`${failCount} 个文件识别失败`)
    }
  }

  const handleDelete = async (id: string, filename: string) => {
    try {
      await deleteInvoice(id)
      setResults((prev) => prev.filter((r) => r.invoice.id !== id))
      message.success(`已删除 ${filename}`)
    } catch {
      message.error('删除失败')
    }
  }

  const columns = [
    {
      title: '文件', dataIndex: ['invoice', 'image_filename'], key: 'file',
      width: 200,
      render: (name: string, r: UploadResult) => {
        const isPdf = name?.toLowerCase().endsWith('.pdf')
        return (
          <Space>
            {isPdf ? <FilePdfOutlined style={{ color: '#ff4d4f' }} /> :
             <FileImageOutlined style={{ color: '#1677ff' }} />}
            <span>{name}</span>
          </Space>
        )
      },
    },
    {
      title: '识别状态', key: 'status',
      render: (_: any, r: UploadResult) => {
        const inv = r.invoice
        const s = inv.ocr_status
        return (
          <Space>
            <Tag color={s === 'done' ? 'green' : s === 'failed' ? 'red' : 'processing'}>
              {s === 'done' ? '✓ 已识别' : s === 'failed' ? '✗ 失败' : '处理中...'}
            </Tag>
            {inv.ocr_confidence != null && (
              <Progress
                percent={Math.round(inv.ocr_confidence)}
                size="small"
                style={{ width: 80 }}
                strokeColor={
                  inv.ocr_confidence >= 90 ? '#52c41a' :
                  inv.ocr_confidence >= 70 ? '#faad14' : '#ff4d4f'
                }
              />
            )}
          </Space>
        )
      },
    },
    {
      title: '发票号码', dataIndex: ['invoice', 'invoice_number'], key: 'number',
      render: (v: string | null) => v || '-',
    },
    {
      title: '金额', key: 'amount',
      render: (_: any, r: UploadResult) => {
        const v = r.invoice.total_amount
        return v ? `¥${v.toFixed(2)}` : '-'
      },
    },
    {
      title: '销售方', dataIndex: ['invoice', 'vendor_name'], key: 'vendor',
      render: (v: string | null) => v || '-',
      ellipsis: true,
    },
    {
      title: '推荐科目', dataIndex: ['invoice', 'suggested_subject_name'], key: 'subject',
      render: (v: string | null) => {
        if (!v) return '-'
        return <Tag color="blue">{v}</Tag>
      },
      ellipsis: true,
    },
    {
      title: '操作', key: 'action', width: 140,
      render: (_: any, r: UploadResult) => (
        <Space size={0}>
          {r.entry_id && (
            <Button type="link" size="small" icon={<ThunderboltOutlined />}
              onClick={() => navigate(`/entries/${r.entry_id}/edit`)}>凭证</Button>
          )}
          {r.invoice.ocr_status === 'done' && !r.entry_id && (
            <Button type="link" size="small"
              onClick={() => navigate(`/invoices/${r.invoice.id}/review`)}>审核</Button>
          )}
          <Popconfirm
            title="确定删除？"
            onConfirm={() => handleDelete(r.invoice.id, r.invoice.image_filename)}
          >
            <Button type="link" size="small" danger icon={<DeleteOutlined />} />
          </Popconfirm>
        </Space>
      ),
    },
  ]

  return (
    <div>
      <Space style={{ marginBottom: 16, width: '100%', justifyContent: 'space-between' }}>
        <Typography.Title level={4} style={{ margin: 0 }}>上传发票</Typography.Title>
        <Space>
          <Typography.Text>自动生成凭证</Typography.Text>
          <Switch
            checked={autoGenerate}
            onChange={setAutoGenerate}
            checkedChildren="开"
            unCheckedChildren="关"
          />
          <Button
            type="primary"
            icon={<InboxOutlined />}
            onClick={() => fileInputRef.current?.click()}
            loading={uploading}
          >
            选择文件
          </Button>
        </Space>
      </Space>

      {autoGenerate && (
        <Typography.Paragraph type="secondary" style={{ marginBottom: 8 }}>
          ⚡ 开启自动生成：上传识别成功后，直接生成记账凭证（草稿状态），可在凭证列表中查看和确认。
        </Typography.Paragraph>
      )}

      {/* Hidden file input for multi-file selection */}
      <input
        ref={fileInputRef}
        type="file"
        accept="image/*,.pdf"
        multiple
        style={{ display: 'none' }}
        onChange={(e) => {
          if (e.target.files) {
            doUpload(e.target.files)
            e.target.value = '' // Reset so same file can be re-selected
          }
        }}
      />

      <Card style={{ marginBottom: 16 }}>
        <div
          onClick={() => fileInputRef.current?.click()}
          style={{
            border: '2px dashed #d9d9d9',
            borderRadius: 8,
            padding: 40,
            textAlign: 'center',
            cursor: uploading ? 'not-allowed' : 'pointer',
            background: uploading ? '#f5f5f5' : '#fafafa',
            transition: 'border-color 0.3s',
          }}
          onMouseEnter={(e) => {
            if (!uploading) (e.currentTarget.style.borderColor = '#1677ff')
          }}
          onMouseLeave={(e) => {
            (e.currentTarget.style.borderColor = '#d9d9d9')
          }}
        >
          <InboxOutlined style={{ fontSize: 48, color: '#1677ff' }} />
          <p style={{ fontSize: 16, margin: '16px 0 4px' }}>
            {uploading
              ? `正在识别中... (${progress.done}/${progress.total})`
              : '点击选择发票文件（支持多选）'}
          </p>
          <p style={{ color: '#888', margin: 0 }}>
            支持 JPG、PNG、WEBP、PDF 格式，可一次性选择多个文件
          </p>
          {uploading && progress.total > 0 && (
            <Progress
              percent={Math.round((progress.done / progress.total) * 100)}
              style={{ maxWidth: 400, margin: '16px auto 0' }}
            />
          )}
        </div>
      </Card>

      {results.length > 0 && (
        <Card title={`上传记录 (${results.length})`}>
          <Table
            columns={columns}
            dataSource={results}
            rowKey={(r) => r.invoice.id || Math.random().toString()}
            size="small"
            pagination={{ pageSize: 20 }}
          />
        </Card>
      )}
    </div>
  )
}
