import { useCallback, useEffect, useRef, useState } from 'react'
import {
  Button,
  Card,
  Descriptions,
  message,
  Popconfirm,
  Progress,
  Select,
  Space,
  Switch,
  Table,
  Tag,
  Tooltip,
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
  updateBankStatementTransactionAccount,
  updateBankStatementTransactionTemplate,
  type BankStatementUploadResult,
} from '../api/bankStatements'
import { listDocumentTypes, listVoucherTemplates, type DocumentType, type VoucherTemplate } from '../api/documentVouchers'
import { getSubjectTree } from '../api/subjects'
import AccountSubjectPicker from '../components/account/AccountSubjectPicker'
import { useAppStore } from '../hooks/useAppStore'
import { detectBankStatementProcessingMode } from '../utils/bankStatementProcessing'
import type { BankStatementTransaction, SubjectTreeNode } from '../types/invoice'

interface RowData extends BankStatementTransaction {
  filename: string
  upload_status: string
  upload_error: string | null
  file_type: string | null
  processing_mode: string | null
  use_ocr: boolean
  use_ai: boolean
  total_rows: number | null
  valid_rows: number | null
  error_rows: number | null
}

function money(tx: BankStatementTransaction) {
  const amount = tx.expense_amount || tx.income_amount
  if (!amount) return '-'
  return `¥${Number(amount).toFixed(2)}`
}

function processingLabel(mode?: string | null) {
  const map: Record<string, string> = {
    excel_parser: 'Excel 表格解析',
    csv_parser: 'CSV 表格解析',
    pdf_text_parser: 'PDF 文本解析',
    pdf_ocr: 'OCR 扫描 PDF',
    image_ocr: 'OCR 图片识别',
    unsupported: '不支持',
  }
  return mode ? map[mode] || mode : '-'
}

export default function BankStatementUpload() {
  const [uploading, setUploading] = useState(false)
  const [loadingHistory, setLoadingHistory] = useState(false)
  const [deleteAllLoading, setDeleteAllLoading] = useState(false)
  const [autoCreateVoucherDraft, setAutoCreateVoucherDraft] = useState(false)
  const [results, setResults] = useState<BankStatementUploadResult[]>([])
  const [progress, setProgress] = useState({ done: 0, total: 0 })
  const [processingText, setProcessingText] = useState('')
  const [processingDescription, setProcessingDescription] = useState('')
  const [subjects, setSubjects] = useState<SubjectTreeNode[]>([])
  const [documentTypes, setDocumentTypes] = useState<DocumentType[]>([])
  const [voucherTemplates, setVoucherTemplates] = useState<VoucherTemplate[]>([])
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
      .then((res) => setResults(res.items.map((upload) => ({ upload, entry_ids: [] }))))
      .catch((err: any) => message.error(err.response?.data?.detail || '加载上传记录失败'))
      .finally(() => setLoadingHistory(false))
  }, [currentClient])

  useEffect(() => {
    refreshUploads()
    if (currentClient?.id) {
      getSubjectTree(currentClient.id).then(setSubjects)
      listDocumentTypes(currentClient.id).then((res) => setDocumentTypes(res.items))
      listVoucherTemplates({ company_id: currentClient.id, enabled_only: true }).then((res) => setVoucherTemplates(res.items))
    }
  }, [refreshUploads])

  const rows: RowData[] = results.flatMap((result) => {
    const uploadFields = {
      filename: result.upload.filename,
      upload_status: result.upload.status,
      upload_error: result.upload.error_msg,
      file_type: result.upload.file_type,
      processing_mode: result.upload.processing_mode,
      use_ocr: result.upload.use_ocr,
      use_ai: result.upload.use_ai,
      total_rows: result.upload.total_rows,
      valid_rows: result.upload.valid_rows,
      error_rows: result.upload.error_rows,
    }

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
        selected_account_code: null,
        selected_account_name: null,
        selected_account_full_name: null,
        selected_parent_account_code: null,
        selected_parent_account_name: null,
        manual_account_override: false,
        account_selection_source: 'auto' as const,
        document_type_id: null,
        document_name: null,
        settlement_method: null,
        business_type: null,
        selected_template_id: null,
        recommended_template_id: null,
        template_match_reason: null,
        subject_reason: null,
        confidence: null,
        status: 'failed' as const,
        error_msg: result.upload.error_msg,
        entry_id: null,
        created_at: result.upload.created_at,
        ...uploadFields,
      }]
    }

    return result.upload.transactions.map((tx) => ({ ...tx, ...uploadFields }))
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
        const mode = detectBankStatementProcessingMode(file)
        setProcessingText(`${mode.displayText} (${allResults.length + 1}/${fileArray.length})`)
        setProcessingDescription(mode.description)
        const batch = await batchUploadBankStatements([file], currentClient.id, autoCreateVoucherDraft)
        allResults.push(...batch)
        setProgress({ done: allResults.length, total: fileArray.length })
      }

      const txCount = allResults.reduce((sum, r) => sum + r.upload.transactions.length, 0)
      const entryCount = allResults.reduce((sum, r) => sum + r.entry_ids.length, 0)
      const failed = allResults.filter((r) => r.upload.status === 'failed').length
      if (txCount > 0) {
        message.success(`解析 ${txCount} 条流水${entryCount ? `，生成 ${entryCount} 张凭证草稿` : ''}`)
      }
      if (failed > 0) message.error(`${failed} 个文件解析失败`)
      refreshUploads()
    } catch (err: any) {
      message.error(err.response?.data?.detail || err.message || '上传失败，请稍后重试')
    } finally {
      setUploading(false)
      setProcessingText('')
      setProcessingDescription('')
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
    } catch (err: any) {
      message.error(err.response?.data?.detail || '生成凭证草稿失败')
    }
  }

  const handleApplyAccount = async (row: RowData, account: any) => {
    try {
      await updateBankStatementTransactionAccount(row.id, {
        account_code: account.account_code,
        account_name: account.account_name,
        account_full_name: account.account_full_name,
        parent_account_code: account.parent_account_code,
        parent_account_name: account.parent_account_name,
        source: account.account_selection_source === 'new_sub_account' ? 'new_sub_account' : 'manual',
      })
      setResults((prev) => prev.map((result) => ({
        ...result,
        upload: {
          ...result.upload,
          transactions: result.upload.transactions.map((tx) => (
            tx.id === row.id
              ? {
                  ...tx,
                  suggested_subject_code: account.account_code,
                  suggested_subject_name: account.account_full_name,
                  selected_account_code: account.account_code,
                  selected_account_name: account.account_name,
                  selected_account_full_name: account.account_full_name,
                  selected_parent_account_code: account.parent_account_code,
                  selected_parent_account_name: account.parent_account_name,
                  manual_account_override: true,
                  account_selection_source: account.account_selection_source,
                }
              : tx
          )),
        },
      })))
      message.success('已保存该流水的手动科目')
    } catch (err: any) {
      message.error(err.response?.data?.detail || `保存科目失败: ${err.message}`)
    }
  }

  const handleTemplateChange = async (row: RowData, templateId: string) => {
    const template = voucherTemplates.find((item) => item.id === templateId)
    if (!template) return
    try {
      await updateBankStatementTransactionTemplate(row.id, {
        document_type_id: template.document_type_id,
        document_name: template.document_name,
        settlement_method: template.settlement_method,
        business_type: template.business_type,
        template_id: template.id,
      })
      setResults((prev) => prev.map((result) => ({
        ...result,
        upload: {
          ...result.upload,
          transactions: result.upload.transactions.map((tx) => (
            tx.id === row.id
              ? {
                  ...tx,
                  document_type_id: template.document_type_id,
                  document_name: template.document_name,
                  settlement_method: template.settlement_method,
                  business_type: template.business_type,
                  selected_template_id: template.id,
                  template_match_reason: '人工选择模板',
                }
              : tx
          )),
        },
      })))
      message.success('已保存该流水的分录模板')
    } catch (err: any) {
      message.error(err.response?.data?.detail || `保存模板失败: ${err.message}`)
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
      width: 240,
      render: (name: string) => (
        <Space>
          {name?.toLowerCase().endsWith('.pdf') ? <FilePdfOutlined /> : <FileExcelOutlined />}
          <span>{name}</span>
        </Space>
      ),
    },
    {
      title: '处理方式',
      key: 'processing',
      width: 220,
      render: (_: any, row: RowData) => (
        <Space size={4} wrap>
          <Tag color="blue">{processingLabel(row.processing_mode)}</Tag>
          <Tag color={row.use_ocr ? 'orange' : 'default'}>{row.use_ocr ? 'OCR' : '无 OCR'}</Tag>
          <Tag color={row.use_ai ? 'purple' : 'default'}>{row.use_ai ? 'AI' : '无 AI'}</Tag>
        </Space>
      ),
    },
    {
      title: '行数',
      key: 'row_count',
      width: 110,
      render: (_: any, row: RowData) => row.total_rows == null ? '-' : `${row.valid_rows || 0}/${row.total_rows}`,
    },
    {
      title: '状态',
      key: 'status',
      width: 180,
      render: (_: any, row: RowData) => (
        <Space>
          <Tag color={row.status === 'recognized' ? 'green' : 'red'}>
            {row.status === 'recognized' ? '已解析' : '失败'}
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
      title: '摘要',
      dataIndex: 'summary',
      ellipsis: true,
      width: 220,
      render: (v: string | null, row: RowData) => v || row.error_msg || '-',
    },
    {
      title: '对方户名',
      dataIndex: 'counterparty',
      ellipsis: true,
      width: 220,
      render: (v: string | null) => v || <Typography.Text type="warning">对方未识别</Typography.Text>,
    },
    {
      title: '对方账号',
      dataIndex: 'account_number',
      width: 180,
      render: (v: string | null) => v || '-',
    },
    {
      title: '金额',
      width: 120,
      render: (_: any, row: RowData) => money(row),
    },
    {
      title: '单据名称',
      width: 150,
      render: (_: any, row: RowData) => row.document_name || (
        documentTypes.find((item) => item.name === '银行票据')?.name || '银行票据'
      ),
    },
    {
      title: '业务类型',
      dataIndex: 'business_type',
      width: 130,
      render: (value: string | null) => value || <Typography.Text type="warning">待选择</Typography.Text>,
    },
    {
      title: '推荐模板',
      key: 'template',
      width: 260,
      render: (_: any, row: RowData) => row.status === 'recognized' ? (
        <Space direction="vertical" size={4} style={{ width: '100%' }}>
          <Select
            showSearch
            value={row.selected_template_id || row.recommended_template_id || undefined}
            placeholder="选择分录模板"
            style={{ width: '100%' }}
            onChange={(value) => handleTemplateChange(row, value)}
            options={voucherTemplates.map((tpl) => ({
              value: tpl.id,
              label: `${tpl.document_name} / ${tpl.settlement_method} / ${tpl.business_type}`,
            }))}
          />
          <Typography.Text type="secondary">{row.template_match_reason || '按票据、结算方式、业务类型匹配'}</Typography.Text>
        </Space>
      ) : '-',
    },
    {
      title: '??/????',
      key: 'subject',
      width: 360,
      render: (_: any, row: RowData) => row.status === 'recognized' ? (
        <Space direction="vertical" size={4} style={{ width: '100%' }}>
          <AccountSubjectPicker
            value={row.selected_account_code || row.suggested_subject_code}
            subjects={subjects}
            clientId={currentClient?.id}
            counterpartyName={row.counterparty}
            auxiliaryName={row.counterparty}
            manualOverride={row.manual_account_override}
            onCreated={() => currentClient?.id && getSubjectTree(currentClient.id).then(setSubjects)}
            onApply={(account) => handleApplyAccount(row, account)}
          />
          <Space size={4}>
            <Tag color={row.manual_account_override ? 'gold' : 'blue'}>
              {row.manual_account_override ? '??' : '??'}
            </Tag>
            <Typography.Text type="secondary">
              {row.selected_account_full_name || row.suggested_subject_name || '?????'}
            </Typography.Text>
          </Space>
        </Space>
      ) : '-',
    },
    {
      title: '操作',
      key: 'action',
      width: 160,
      fixed: 'right' as const,
      render: (_: any, row: RowData) => (
        <Space size={0}>
          {row.entry_id && row.entry_id !== 'merged' ? (
            <Button type="link" size="small" onClick={() => navigate(`/entries/${row.entry_id}/edit`)}>
              凭证草稿
            </Button>
          ) : row.status === 'recognized' ? (
            <Button
              type="link"
              size="small"
              icon={<ThunderboltOutlined />}
              onClick={() => handleGenerate(row)}
            >
              生成草稿
            </Button>
          ) : null}
          <Popconfirm title="从当前列表移除？" onConfirm={() => handleRemoveUpload(row.upload_id)}>
            <Button type="link" size="small" danger icon={<DeleteOutlined />} />
          </Popconfirm>
        </Space>
      ),
    },
  ]

  const latestUpload = results[0]?.upload

  return (
    <div>
      <Space style={{ marginBottom: 16, width: '100%', justifyContent: 'space-between' }}>
        <Typography.Title level={4} style={{ margin: 0 }}>上传银行流水</Typography.Title>
        <Space>
          <Tooltip title="系统只会生成草稿，正式凭证需要人工确认。">
            <Space>
              <Typography.Text>自动生成凭证草稿</Typography.Text>
              <Switch checked={autoCreateVoucherDraft} onChange={setAutoCreateVoucherDraft} />
            </Space>
          </Tooltip>
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
        accept=".csv,.xls,.xlsx,.xlsm,.ods,.pdf,image/*"
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
              ? processingText || `正在处理流水 (${progress.done}/${progress.total})`
              : !currentClient
                ? '请先在顶部选择客户'
                : '点击选择银行流水文件（支持多选）'}
          </p>
          <p style={{ color: '#888', margin: 0 }}>
            {uploading && processingDescription
              ? processingDescription
              : '支持 CSV、XLSX、PDF、图片。Excel / CSV 优先表格解析；PDF 优先文本解析；只有图片或扫描 PDF 才走 OCR + AI 辅助。'}
          </p>
          {uploading && progress.total > 0 && (
            <Progress
              percent={Math.round((progress.done / progress.total) * 100)}
              style={{ maxWidth: 400, margin: '16px auto 0' }}
            />
          )}
        </div>
      </Card>

      {latestUpload && (
        <Card style={{ marginBottom: 16 }}>
          <Descriptions size="small" column={4}>
            <Descriptions.Item label="文件">{latestUpload.filename}</Descriptions.Item>
            <Descriptions.Item label="文件类型">{latestUpload.file_type || '-'}</Descriptions.Item>
            <Descriptions.Item label="处理方式">{processingLabel(latestUpload.processing_mode)}</Descriptions.Item>
            <Descriptions.Item label="OCR">{latestUpload.use_ocr ? '是' : '否'}</Descriptions.Item>
            <Descriptions.Item label="AI">{latestUpload.use_ai ? '是' : '否'}</Descriptions.Item>
            <Descriptions.Item label="总行数">{latestUpload.total_rows ?? '-'}</Descriptions.Item>
            <Descriptions.Item label="有效行数">{latestUpload.valid_rows ?? '-'}</Descriptions.Item>
            <Descriptions.Item label="异常行数">{latestUpload.error_rows ?? '-'}</Descriptions.Item>
          </Descriptions>
        </Card>
      )}

      {rows.length > 0 && (
        <Card title={`流水确认列表 (${rows.length})`}>
          <Table
            columns={columns}
            dataSource={rows}
            rowKey="id"
            size="small"
            loading={loadingHistory}
            pagination={{ pageSize: 20 }}
            scroll={{ x: 2350 }}
          />
        </Card>
      )}
    </div>
  )
}
