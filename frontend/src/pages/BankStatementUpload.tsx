import { useCallback, useEffect, useRef, useState } from 'react'
import {
  Button,
  Card,
  message,
  Popconfirm,
  Progress,
  Space,
  Switch,
  Table,
  Tag,
  Typography,
} from 'antd'
import {
  BankOutlined,
  DeleteOutlined,
  FileExcelOutlined,
  FilePdfOutlined,
  ThunderboltOutlined,
  UploadOutlined,
} from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import {
  batchDeleteBankStatementUploads,
  batchUploadBankStatements,
  generateBankStatementEntry,
  listBankStatementUploads,
  type BankStatementUploadResult,
} from '../api/bankStatements'
import { useAppStore } from '../hooks/useAppStore'
import type { BankStatementTransaction } from '../types/invoice'

interface RowData extends BankStatementTransaction {
  filename: string
  upload_status: string
  upload_error: string | null
}

function money(tx: BankStatementTransaction) {
  const amount = tx.expense_amount || tx.income_amount
  if (!amount) return '-'
  return `¥${Number(amount).toFixed(2)}`
}

export default function BankStatementUpload() {
  const [uploading, setUploading] = useState(false)
  const [loadingHistory, setLoadingHistory] = useState(false)
  const [deleteAllLoading, setDeleteAllLoading] = useState(false)
  const [autoGenerate, setAutoGenerate] = useState(true)
  const [results, setResults] = useState<BankStatementUploadResult[]>([])
  const [progress, setProgress] = useState({ done: 0, total: 0 })
  const fileInputRef = useRef<HTMLInputElement>(null)
  const { currentClient } = useAppStore()
  const navigate = useNavigate()

  const refreshUploads = useCallback(() => {
    if (!currentClient) {
      setResults([])
      return
    }
    setLoadingHistory(true)
    listBankStatementUploads({ client_id: currentClient.id, limit: 200 })
      .then((res) => {
        setResults(res.items.map((upload) => ({ upload, entry_ids: [] })))
      })
      .catch((err: any) => {
        message.error(err.response?.data?.detail || '加载上传记录失败')
      })
      .finally(() => setLoadingHistory(false))
  }, [currentClient])

  useEffect(() => {
    refreshUploads()
  }, [refreshUploads])

  const rows: RowData[] = results.flatMap((result) => {
    if (result.upload.transactions.length === 0) {
      return [{
        id: result.upload.id,
        upload_id: result.upload.id,
        client_id: result.upload.client_id,
        transaction_date: null,
        summary: null,
        counterparty: null,
        account_number: null,
        income_amount: null,
        expense_amount: null,
        balance: null,
        suggested_subject_code: null,
        suggested_subject_name: null,
        subject_reason: null,
        confidence: null,
        status: 'failed',
        error_msg: result.upload.error_msg,
        entry_id: null,
        created_at: result.upload.created_at,
        filename: result.upload.filename,
        upload_status: result.upload.status,
        upload_error: result.upload.error_msg,
      }]
    }
    return result.upload.transactions.map((tx) => ({
      ...tx,
      filename: result.upload.filename,
      upload_status: result.upload.status,
      upload_error: result.upload.error_msg,
    }))
  })

  const doUpload = async (files: FileList | File[]) => {
    if (!currentClient) {
      message.warning('请先在顶部选择要记账的客户')
      return
    }
    const fileArray = Array.from(files)
    if (fileArray.length === 0) return

    setUploading(true)
    setProgress({ done: 0, total: fileArray.length })
    try {
      const allResults: BankStatementUploadResult[] = []

      for (const file of fileArray) {
        const batch = await batchUploadBankStatements([file], currentClient.id, autoGenerate)
        allResults.push(...batch)
        setProgress({ done: allResults.length, total: fileArray.length })
      }

      const txCount = allResults.reduce((sum, r) => sum + r.upload.transactions.length, 0)
      const entryCount = allResults.reduce((sum, r) => sum + r.entry_ids.length, 0)
      const failed = allResults.filter((r) => r.upload.status === 'failed').length
      if (txCount > 0) {
        message.success(`识别 ${txCount} 条流水${entryCount ? `，生成 ${entryCount} 张凭证` : ''}`)
      }
      if (failed > 0) message.error(`${failed} 个文件识别失败`)
      refreshUploads()
    } catch (err: any) {
      message.error(err.response?.data?.detail || err.message || '上传失败，请稍后重试')
    } finally {
      setUploading(false)
    }
  }

  const handleGenerate = async (row: RowData) => {
    try {
      const res = await generateBankStatementEntry(row.id)
      setResults((prev) => prev.map((result) => ({
        ...result,
        upload: {
          ...result.upload,
          transactions: result.upload.transactions.map((tx) => (
            tx.id === row.id ? { ...tx, entry_id: res.entry_id } : tx
          )),
        },
      })))
      refreshUploads()
      navigate(`/entries/${res.entry_id}/edit`)
    } catch {
      message.error('生成凭证失败')
    }
  }

  const handleRemoveUpload = (uploadId: string) => {
    setResults((prev) => prev.filter((result) => result.upload.id !== uploadId))
  }

  const handleDeleteAll = async () => {
    const uploadIds = Array.from(new Set(results.map((result) => result.upload.id)))
    if (uploadIds.length === 0) {
      message.info('当前没有可删除的上传记录')
      return
    }
    setDeleteAllLoading(true)
    try {
      const { deleted, failed } = await batchDeleteBankStatementUploads(uploadIds)
      if (deleted > 0) message.success(`已删除 ${deleted} 个上传记录`)
      if (failed?.length > 0) {
        const reasons = failed.slice(0, 5).map((f: any) => `${f.id.slice(0, 8)}...: ${f.reason}`).join('; ')
        message.warning(`${failed.length} 个记录未删除: ${reasons}`)
      }
      refreshUploads()
    } catch (err: any) {
      message.error(err.response?.data?.detail || '全部删除失败')
    } finally {
      setDeleteAllLoading(false)
    }
  }

  const columns = [
    {
      title: '文件',
      dataIndex: 'filename',
      width: 260,
      render: (name: string) => (
        <Space>
          {name?.toLowerCase().endsWith('.pdf') ? <FilePdfOutlined /> : <FileExcelOutlined />}
          <span>{name}</span>
        </Space>
      ),
    },
    {
      title: '识别状态',
      key: 'status',
      width: 180,
      render: (_: any, row: RowData) => (
        <Space>
          <Tag color={row.status === 'recognized' ? 'green' : 'red'}>
            {row.status === 'recognized' ? '已识别' : '失败'}
          </Tag>
          {row.confidence != null && (
            <>
              <Progress
                percent={Math.round(row.confidence)}
                size="small"
                showInfo={false}
                style={{ width: 56 }}
                strokeColor={row.confidence >= 90 ? '#52c41a' : '#faad14'}
              />
              <span>{Math.round(row.confidence)}%</span>
            </>
          )}
        </Space>
      ),
    },
    {
      title: '日期',
      dataIndex: 'transaction_date',
      width: 120,
      render: (v: string | null) => v || '-',
    },
    {
      title: '金额',
      width: 120,
      render: (_: any, row: RowData) => money(row),
    },
    {
      title: '对方/摘要',
      key: 'summary',
      ellipsis: true,
      render: (_: any, row: RowData) => row.counterparty || row.summary || row.error_msg || '-',
    },
    {
      title: '推荐科目',
      dataIndex: 'suggested_subject_name',
      width: 190,
      render: (v: string | null) => v ? <Tag color="blue">{v}</Tag> : '-',
    },
    {
      title: '操作',
      key: 'action',
      width: 150,
      render: (_: any, row: RowData) => (
        <Space size={0}>
          {row.entry_id && row.entry_id !== 'merged' ? (
            <Button type="link" size="small" onClick={() => navigate(`/entries/${row.entry_id}/edit`)}>
              凭证
            </Button>
          ) : row.status === 'recognized' ? (
            <Button
              type="link"
              size="small"
              icon={<ThunderboltOutlined />}
              onClick={() => handleGenerate(row)}
            >
              凭证
            </Button>
          ) : null}
          <Popconfirm title="从当前列表移除？" onConfirm={() => handleRemoveUpload(row.upload_id)}>
            <Button type="link" size="small" danger icon={<DeleteOutlined />} />
          </Popconfirm>
        </Space>
      ),
    },
  ]

  return (
    <div>
      <Space style={{ marginBottom: 16, width: '100%', justifyContent: 'space-between' }}>
        <Typography.Title level={4} style={{ margin: 0 }}>上传银行流水</Typography.Title>
        <Space>
          <Typography.Text>自动生成凭证</Typography.Text>
          <Switch checked={autoGenerate} onChange={setAutoGenerate} />
          <Popconfirm
            title="删除全部银行流水上传记录？"
            description={`将删除当前客户 ${results.length} 个上传批次及其流水明细，已生成的凭证不会自动删除。此操作不可恢复。`}
            okText="全部删除"
            cancelText="取消"
            okButtonProps={{ danger: true, loading: deleteAllLoading }}
            onConfirm={handleDeleteAll}
          >
            <Button danger icon={<DeleteOutlined />} loading={deleteAllLoading} disabled={results.length === 0}>
              全部删除
            </Button>
          </Popconfirm>
          <Button
            type="primary"
            icon={<UploadOutlined />}
            loading={uploading}
            disabled={!currentClient}
            onClick={() => fileInputRef.current?.click()}
          >
            选择文件
          </Button>
        </Space>
      </Space>

      <input
        ref={fileInputRef}
        type="file"
        multiple
        accept=".csv,.xlsx,.xlsm,.pdf,image/*"
        style={{ display: 'none' }}
        onChange={(e) => {
          if (e.target.files) {
            doUpload(e.target.files)
            e.target.value = ''
          }
        }}
      />

      <Card style={{ marginBottom: 16 }}>
        <div
          onClick={() => !uploading && currentClient && fileInputRef.current?.click()}
          style={{
            border: '2px dashed #d9d9d9',
            borderRadius: 8,
            padding: 40,
            textAlign: 'center',
            cursor: uploading || !currentClient ? 'not-allowed' : 'pointer',
            background: uploading ? '#f5f5f5' : '#fafafa',
          }}
        >
          <BankOutlined style={{ fontSize: 48, color: '#1677ff' }} />
          <p style={{ fontSize: 16, margin: '16px 0 4px' }}>
            {uploading
              ? `正在识别流水 (${progress.done}/${progress.total})`
              : !currentClient
                ? '请先在顶部选择客户'
                : '点击选择银行流水文件（支持多选）'}
          </p>
          <p style={{ color: '#888', margin: 0 }}>
            支持 CSV、XLSX、PDF、图片。表格流水优先解析，PDF/图片会走 OCR + AI 识别。
          </p>
          {uploading && progress.total > 0 && (
            <Progress
              percent={Math.round((progress.done / progress.total) * 100)}
              style={{ maxWidth: 400, margin: '16px auto 0' }}
            />
          )}
        </div>
      </Card>

      {rows.length > 0 && (
        <Card title={`上传记录 (${rows.length})`}>
          <Table
            columns={columns}
            dataSource={rows}
            rowKey="id"
            size="small"
            loading={loadingHistory}
            pagination={{ pageSize: 20 }}
            scroll={{ x: 1100 }}
          />
        </Card>
      )}
    </div>
  )
}
