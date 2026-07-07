import { useEffect, useMemo, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import {
  Button, Space, Typography, Input, DatePicker,
  Select, message, Tag, Tooltip,
} from 'antd'
import {
  SaveOutlined, PlusOutlined, DeleteOutlined, ArrowLeftOutlined,
  CheckOutlined, PaperClipOutlined, FileSearchOutlined,
} from '@ant-design/icons'
import dayjs from 'dayjs'
import { getEntry, updateEntry, confirmEntry } from '../api/entries'
import { getSubjectTree } from '../api/subjects'
import { useAppStore } from '../hooks/useAppStore'
import AccountSubjectPicker from '../components/account/AccountSubjectPicker'
import MoneyGrid from '../components/voucher/MoneyGrid'
import { amountToChineseUppercase, amountUnits, normalizeAmountInput } from '../utils/accountingAmount'
import type { JournalEntry, JournalEntryLine, SubjectTreeNode } from '../types/invoice'

const receivablePayableAccountPrefixes = ['1122', '2202', '1123', '2203', '1221', '2241']
const requiredAuxiliaryPrefixes = ['1122', '2202', '1123', '2203']
const currentParentCodes = ['1122', '1123', '1221', '2202', '2203', '2241']

function cleanText(value?: string | null) {
  return (value || '').replace(/\s+/g, ' ').trim()
}

function isReceivablePayableAccount(accountCode?: string | null) {
  return receivablePayableAccountPrefixes.some((prefix) => (accountCode || '').startsWith(prefix))
}

function requiresAuxiliaryName(accountCode?: string | null) {
  return requiredAuxiliaryPrefixes.some((prefix) => (accountCode || '').startsWith(prefix))
}

function normalizeAccountName(name?: string | null, auxiliaryName?: string | null, accountCode?: string | null) {
  const rawName = cleanText(name)
  const auxName = cleanText(auxiliaryName)
  if (!rawName) return ''
  if (!isReceivablePayableAccount(accountCode) || !auxName) return rawName

  const underscoreSuffix = `_${auxName}`
  if (rawName.endsWith(underscoreSuffix)) return rawName.slice(0, -underscoreSuffix.length)
  if (rawName.endsWith(auxName)) return rawName.slice(0, -auxName.length).replace(/[_＿\s-]+$/, '')
  return rawName
}

function escapeRegExp(value: string) {
  return value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
}

function formatVoucherAccountDisplay(line: JournalEntryLine) {
  const code = line.account_code || ''
  if (!code || !line.account_name) {
    return { primaryText: '待选择科目', secondaryText: '' }
  }
  // Display: "编码 科目名称" once, no redundant repetition
  return {
    primaryText: `${code} ${line.account_full_name || line.account_name}`,
    secondaryText: '',
  }
}

function flattenSubjects(nodes: SubjectTreeNode[]): {
  value: string
  label: string
  name: string
  parentCode: string | null
  parentName: string | null
  fullName: string
  isLeaf: boolean
}[] {
  let result: {
    value: string
    label: string
    name: string
    parentCode: string | null
    parentName: string | null
    fullName: string
    isLeaf: boolean
  }[] = []
  for (const node of nodes) {
    const parentName = node.parent_account_name || null
    const fullName = node.full_name || (parentName ? `${parentName}_${node.name}` : node.name)
    result.push({
      value: node.code,
      label: `${node.code} ${fullName}`,
      name: node.name,
      parentCode: node.parent_code || null,
      parentName,
      fullName,
      isLeaf: node.is_leaf,
    })
    if (node.children?.length) result = result.concat(flattenSubjects(node.children))
  }
  return result
}

function validLineSummary(entry: JournalEntry, line: JournalEntryLine, index: number) {
  return (index === 0 ? entry.summary : line.summary_detail || entry.summary).trim()
}

function lineAmount(line: JournalEntryLine) {
  return normalizeAmountInput(line.direction === 'credit' ? line.creditAmount : line.debitAmount)
}

function lineHasContent(line: JournalEntryLine, entry: JournalEntry, index: number) {
  return Boolean(
    validLineSummary(entry, line, index)
    || line.account_code
    || line.account_name
    || lineAmount(line) > 0,
  )
}

function getSourceLabel(entry: JournalEntry) {
  const hasBankSource = entry.lines.some((line) => line.source_type === 'bank_statement')
  if (entry.source_invoice_id && hasBankSource) return '发票 + 银行流水'
  if (entry.source_invoice_id) return '发票识别'
  if (hasBankSource) return '银行流水'
  return '手工录入'
}

function validateEntryBeforeConfirm(entry: JournalEntry) {
  const effectiveLines = entry.lines
    .map((line, index) => ({ line, index }))
    .filter(({ line, index }) => lineHasContent(line, entry, index))

  if (effectiveLines.length < 2) return '至少需要两条有效分录'

  for (const { line, index } of effectiveLines) {
    if (!validLineSummary(entry, line, index)) return `第 ${index + 1} 行缺少摘要`
    if (!line.account_code || !line.account_name) return `第 ${index + 1} 行缺少会计科目`
    if (currentParentCodes.includes(line.account_code)) return `第 ${index + 1} 行使用了往来父级科目，请选择明细科目`
    if (requiresAuxiliaryName(line.account_code) && !cleanText(line.auxiliary_name)) {
      return `第 ${index + 1} 行往来科目缺少辅助核算名称`
    }
    if (!line.direction || lineAmount(line) <= 0) return `第 ${index + 1} 行缺少借方或贷方金额`
  }

  const debitTotal = entry.lines
    .filter((line) => line.direction === 'debit')
    .reduce((sum, line) => sum + normalizeAmountInput(line.debitAmount), 0)
  const creditTotal = entry.lines
    .filter((line) => line.direction === 'credit')
    .reduce((sum, line) => sum + normalizeAmountInput(line.creditAmount), 0)

  if (Math.max(debitTotal, creditTotal) <= 0) return '合计金额不能为 0'
  if (Math.abs(debitTotal - creditTotal) >= 0.01) return '借贷不平，不能确认凭证'
  return null
}

export default function EntryEditor() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const currentClient = useAppStore((state) => state.currentClient)
  const [entry, setEntry] = useState<JournalEntry | null>(null)
  const [subjects, setSubjects] = useState<SubjectTreeNode[]>([])
  const [saving, setSaving] = useState(false)
  const [attachmentCount, setAttachmentCount] = useState(0)

  useEffect(() => {
    if (id) getEntry(id).then(setEntry)
    getSubjectTree(currentClient?.id).then(setSubjects)
  }, [id, currentClient?.id])

  const subjectOptions = useMemo(() => flattenSubjects(subjects), [subjects])

  const handleHeaderChange = (field: string, value: any) => {
    if (!entry || entry.status !== 'draft') return
    setEntry({ ...entry, [field]: value })
  }

  const handleLineChange = (lineId: string, field: string, value: any) => {
    if (!entry || entry.status !== 'draft') return
    setEntry({
      ...entry,
      lines: entry.lines.map((line) =>
        line.id === lineId ? { ...line, [field]: value } : line
      ),
    })
  }

  const handleLineAmountChange = (lineId: string, direction: 'debit' | 'credit', value: number) => {
    if (!entry || entry.status !== 'draft') return
    setEntry({
      ...entry,
      lines: entry.lines.map((line) =>
        line.id === lineId
          ? {
              ...line,
              direction,
              debitAmount: direction === 'debit' ? normalizeAmountInput(value) : 0,
              creditAmount: direction === 'credit' ? normalizeAmountInput(value) : 0,
            }
          : line
      ),
    })
  }

  const addLine = () => {
    if (!entry || entry.status !== 'draft') return
    const maxNum = entry.lines.reduce((max, line) => Math.max(max, line.line_number), 0)
    const newLine: JournalEntryLine = {
      id: `new_${Date.now()}`,
      entry_id: entry.id,
      line_number: maxNum + 1,
      account_code: '',
      account_name: '',
      direction: 'debit',
      debitAmount: 0,
      creditAmount: 0,
      summary_detail: '',
      account_full_name: null,
      parent_account_code: null,
      parent_account_name: null,
      auxiliary_type: null,
      auxiliary_code: null,
      auxiliary_name: null,
      counterparty_name: null,
      counterparty_account: null,
      source_type: null,
      source_document_id: null,
      source_row_id: null,
      manual_account_override: false,
      account_selection_source: 'auto',
    }
    setEntry({ ...entry, lines: [...entry.lines, newLine] })
  }

  const removeLine = (lineId: string) => {
    if (!entry || entry.status !== 'draft') return
    if (entry.lines.length <= 2) {
      message.warning('凭证至少保留 2 行分录')
      return
    }
    setEntry({ ...entry, lines: entry.lines.filter((line) => line.id !== lineId) })
  }

  const handleSave = async () => {
    if (!entry || !id || entry.status !== 'draft') return
    setSaving(true)
    try {
      await updateEntry(id, {
        voucher_date: entry.voucher_date,
        voucher_type: entry.voucher_type,
        voucher_number: entry.voucher_number,
        summary: entry.summary || '未填写摘要',
        lines: entry.lines.map((line, index) => ({
          line_number: index + 1,
          account_code: line.account_code,
          account_name: line.parent_account_name ? line.account_name : normalizeAccountName(line.account_name, line.auxiliary_name, line.account_code),
          direction: line.direction,
          debitAmount: normalizeAmountInput(line.debitAmount),
          creditAmount: normalizeAmountInput(line.creditAmount),
          summary_detail: line.summary_detail ?? undefined,
          account_full_name: line.account_full_name
            || (line.parent_account_name && line.account_name
              ? `${line.parent_account_name}_${line.account_name}`
              : normalizeAccountName(line.account_name, line.auxiliary_name, line.account_code)),
          parent_account_code: line.parent_account_code,
          parent_account_name: line.parent_account_name,
          auxiliary_type: line.auxiliary_type,
          auxiliary_code: line.auxiliary_code,
          auxiliary_name: line.auxiliary_name,
          counterparty_name: line.counterparty_name,
          counterparty_account: line.counterparty_account,
          source_type: line.source_type,
          source_document_id: line.source_document_id,
          source_row_id: line.source_row_id,
          manual_account_override: line.manual_account_override,
          account_selection_source: line.account_selection_source,
        })),
      })
      message.success('已保存草稿')
      getEntry(id).then(setEntry)
    } catch (err: any) {
      message.error(err.response?.data?.detail || `保存失败: ${err.message}`)
    } finally {
      setSaving(false)
    }
  }

  const handleConfirm = async () => {
    if (!entry || !id || entry.status !== 'draft') return
    const validationError = validateEntryBeforeConfirm(entry)
    if (validationError) {
      message.error(validationError)
      return
    }

    try {
      await handleSave()
      await confirmEntry(id)
      message.success('凭证已确认，可以导出')
      navigate('/entries')
    } catch (err: any) {
      message.error(err.response?.data?.detail || `确认失败: ${err.message}`)
    }
  }

  if (!entry) return <Typography.Text type="danger">凭证不存在</Typography.Text>

  const readonly = entry.status !== 'draft'
  const debitTotal = entry.lines
    .filter((line) => line.direction === 'debit')
    .reduce((sum, line) => sum + normalizeAmountInput(line.debitAmount), 0)
  const creditTotal = entry.lines
    .filter((line) => line.direction === 'credit')
    .reduce((sum, line) => sum + normalizeAmountInput(line.creditAmount), 0)
  const balanced = Math.abs(debitTotal - creditTotal) < 0.01
  const totalAmount = Math.max(debitTotal, creditTotal)
  const statusMap = {
    draft: { color: 'blue', text: '草稿' },
    confirmed: { color: 'green', text: '已确认' },
    voided: { color: 'default', text: '已作废' },
  } as const
  const status = statusMap[entry.status] || statusMap.draft
  const visibleLineCount = Math.max(entry.lines.length, 5)

  return (
    <div className="voucher-page">
      <Space className="voucher-toolbar">
        <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/entries')}>返回</Button>
        <Tag color={status.color}>{status.text}</Tag>
        <Tag color="cyan">来源：{getSourceLabel(entry)}</Tag>
        <Button icon={<PlusOutlined />} onClick={addLine} type="dashed" disabled={readonly}>
          添加分录行
        </Button>
      </Space>

      <section className={`voucher-sheet ${readonly ? 'voucher-sheet-readonly' : ''}`}>
        {readonly && <div className="voucher-closed-stamp">已结账</div>}

        <div className="voucher-head">
          <div className="voucher-head-left">
            <span>凭证字</span>
            <Select
              value={entry.voucher_type}
              onChange={(value) => handleHeaderChange('voucher_type', value)}
              className="voucher-small-select"
              disabled={readonly}
              options={[
                { value: '记', label: '记' },
                { value: '收', label: '收' },
                { value: '付', label: '付' },
                { value: '转', label: '转' },
              ]}
            />
            <Input
              className="voucher-number-input"
              value={entry.voucher_number || ''}
              onChange={(event) => handleHeaderChange('voucher_number', event.target.value)}
              placeholder="1"
              readOnly={readonly}
            />
            <span>号</span>
            <span>日期</span>
            <DatePicker
              value={entry.voucher_date ? dayjs(entry.voucher_date) : null}
              onChange={(dateValue) => handleHeaderChange('voucher_date', dateValue?.format('YYYY-MM-DD') || '')}
              className="voucher-date-picker"
              disabled={readonly}
            />
          </div>
          <div className="voucher-title-wrap">
            <Typography.Title level={2} className="voucher-title">记账凭证</Typography.Title>
            <div className="voucher-period">
              {entry.voucher_date ? dayjs(entry.voucher_date).format('YYYY年第M期') : dayjs().format('YYYY年第M期')}
            </div>
          </div>
          <div className="voucher-head-right">
            <Button icon={<PaperClipOutlined />} disabled={readonly}>附件</Button>
            <Input
              className="voucher-attachment-input"
              value={attachmentCount}
              onChange={(event) => setAttachmentCount(Number(event.target.value) || 0)}
              readOnly={readonly}
            />
            <span>张</span>
            <Tooltip title="查看来源文件">
              <Button icon={<FileSearchOutlined />} disabled={!entry.source_invoice_id} />
            </Tooltip>
          </div>
        </div>

        <div className="voucher-table" style={{ gridTemplateRows: `56px repeat(${visibleLineCount}, 92px) 70px` }}>
          <div className="voucher-th voucher-summary-head">摘要</div>
          <div className="voucher-th voucher-subject-head">会计科目</div>
          <div className="voucher-th voucher-debit-head">
            <strong>借方金额</strong>
            <div className="voucher-unit-row">{amountUnits.map((unit, index) => <span key={`d-${index}`}>{unit}</span>)}</div>
          </div>
          <div className="voucher-th voucher-credit-head">
            <strong>贷方金额</strong>
            <div className="voucher-unit-row">{amountUnits.map((unit, index) => <span key={`c-${index}`}>{unit}</span>)}</div>
          </div>

          {entry.lines.map((line, index) => (
            <div className="voucher-line-row" key={line.id}>
              <div className="voucher-cell voucher-summary-cell">
                {index === 0 ? (
                  <Input.TextArea
                    value={entry.summary}
                    autoSize={{ minRows: 2, maxRows: 3 }}
                    onChange={(event) => handleHeaderChange('summary', event.target.value)}
                    placeholder="摘要"
                    readOnly={readonly}
                  />
                ) : (
                  <Input
                    value={line.summary_detail || ''}
                    onChange={(event) => handleLineChange(line.id, 'summary_detail', event.target.value)}
                    placeholder="摘要"
                    readOnly={readonly}
                  />
                )}
                <Button
                  type="text"
                  danger
                  size="small"
                  className="voucher-row-delete"
                  icon={<DeleteOutlined />}
                  onClick={() => removeLine(line.id)}
                  disabled={readonly}
                />
              </div>

              <div className="voucher-cell voucher-subject-cell">
                {!readonly && (
                  <div className="voucher-subject-picker">
                    <AccountSubjectPicker
                      value={line.account_code}
                      subjects={subjects}
                      clientId={currentClient?.id}
                      counterpartyName={line.counterparty_name}
                      auxiliaryName={line.auxiliary_name}
                      manualOverride={line.manual_account_override}
                      disabled={readonly}
                      onCreated={() => getSubjectTree(currentClient?.id).then(setSubjects)}
                      onApply={(account) => {
                        setEntry((prev) => prev ? {
                          ...prev,
                          lines: prev.lines.map((currentLine) => currentLine.id === line.id
                            ? {
                                ...currentLine,
                                account_code: account.account_code,
                                account_name: account.account_name,
                                account_full_name: account.account_full_name,
                                parent_account_code: account.parent_account_code,
                                parent_account_name: account.parent_account_name,
                                auxiliary_name: account.auxiliary_name || currentLine.auxiliary_name,
                                auxiliary_code: account.auxiliary_code || currentLine.auxiliary_code,
                                manual_account_override: account.manual_account_override,
                                account_selection_source: account.account_selection_source,
                              }
                            : currentLine),
                        } : prev)
                      }}
                    />
                  </div>
                )}
                <span className="voucher-subject-text">
                  <strong>
                    {formatVoucherAccountDisplay(line).primaryText}
                    {line.manual_account_override && <Tag color="gold" className="voucher-manual-tag">手动</Tag>}
                  </strong>
                  {formatVoucherAccountDisplay(line).secondaryText && <small>{formatVoucherAccountDisplay(line).secondaryText}</small>}
                </span>
              </div>

              <div className="voucher-cell voucher-amount-cell">
                <MoneyGrid
                  amount={line.debitAmount}
                  side="debit"
                  readonly={readonly}
                  onChange={(amount) => handleLineAmountChange(line.id, 'debit', amount)}
                />
              </div>
              <div className="voucher-cell voucher-amount-cell">
                <MoneyGrid
                  amount={line.creditAmount}
                  side="credit"
                  readonly={readonly}
                  onChange={(amount) => handleLineAmountChange(line.id, 'credit', amount)}
                />
              </div>
            </div>
          ))}

          {Array.from({ length: Math.max(0, visibleLineCount - entry.lines.length) }).map((_, index) => (
            <div className="voucher-line-row voucher-empty-row" key={`empty-${index}`}>
              <div className="voucher-cell" />
              <div className="voucher-cell" />
              <div className="voucher-cell"><MoneyGrid amount={0} side="debit" readonly /></div>
              <div className="voucher-cell"><MoneyGrid amount={0} side="credit" readonly /></div>
            </div>
          ))}

          <div className="voucher-total-row">
            <div className="voucher-total-text">
              <span>合计：{amountToChineseUppercase(totalAmount)}</span>
              <Tag color={balanced ? 'green' : 'red'}>{balanced ? '借贷平衡' : `借贷不平 ${Math.abs(debitTotal - creditTotal).toFixed(2)}`}</Tag>
            </div>
            <div className="voucher-total-amount"><MoneyGrid amount={debitTotal} side="debit" totalRow readonly /></div>
            <div className="voucher-total-amount"><MoneyGrid amount={creditTotal} side="credit" totalRow readonly /></div>
          </div>
        </div>

        <div className="voucher-footer">
          <Space className="voucher-actions">
            <Button
              type="primary"
              icon={<SaveOutlined />}
              onClick={handleSave}
              loading={saving}
              disabled={readonly}
            >
              保存草稿
            </Button>
            <Button
              icon={<CheckOutlined />}
              onClick={handleConfirm}
              disabled={readonly || !balanced}
              className="voucher-confirm-button"
            >
              确认凭证
            </Button>
          </Space>
          <div className="voucher-meta">
            <span>制单人：账无忧用户990</span>
            <span>录入时间：{dayjs(entry.created_at).format('YYYY-MM-DD HH:mm:ss')}</span>
            <span>最后修改时间：{entry.updated_at ? dayjs(entry.updated_at).format('YYYY-MM-DD HH:mm:ss') : dayjs(entry.created_at).format('YYYY-MM-DD HH:mm:ss')}</span>
          </div>
        </div>
      </section>
    </div>
  )
}

