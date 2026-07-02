import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import {
  Button, Space, Typography, Input, DatePicker,
  Select, message, Tag,
} from 'antd'
import {
  SaveOutlined, PlusOutlined, DeleteOutlined, ArrowLeftOutlined,
  CheckOutlined,
} from '@ant-design/icons'
import { getEntry, updateEntry, confirmEntry } from '../api/entries'
import { getSubjectTree } from '../api/subjects'
import type { JournalEntry, JournalEntryLine, SubjectTreeNode } from '../types/invoice'
import dayjs from 'dayjs'

const amountUnits = ['亿', '千', '百', '十', '万', '千', '百', '十', '元', '角', '分']
const cnDigits = ['零', '壹', '贰', '叁', '肆', '伍', '陆', '柒', '捌', '玖']
const cnUnits = ['', '拾', '佰', '仟']
const cnSections = ['', '万', '亿']

function amountToDigits(value?: number) {
  const cents = Math.round(Math.abs(value || 0) * 100)
  if (!cents) return amountUnits.map(() => '')
  const raw = String(cents).padStart(amountUnits.length, '0').slice(-amountUnits.length)
  const first = raw.search(/[1-9]/)
  return raw.split('').map((char, index) => {
    if (index < first) return ''
    return char
  })
}

function sectionToChinese(section: number) {
  let text = ''
  let zero = false
  for (let i = 0; i < 4; i += 1) {
    const digit = section % 10
    if (digit === 0) {
      zero = text.length > 0
    } else {
      if (zero) text = `零${text}`
      text = `${cnDigits[digit]}${cnUnits[i]}${text}`
      zero = false
    }
    section = Math.floor(section / 10)
  }
  return text
}

function amountToChinese(value: number) {
  const amount = Math.abs(value)
  const yuan = Math.floor(amount)
  const jiao = Math.floor(Math.round(amount * 100) / 10) % 10
  const fen = Math.round(amount * 100) % 10

  if (yuan === 0 && jiao === 0 && fen === 0) return '零元整'

  let integerText = ''
  let sectionIndex = 0
  let integer = yuan
  let needsZero = false
  while (integer > 0) {
    const section = integer % 10000
    if (section === 0) {
      needsZero = integerText.length > 0
    } else {
      let sectionText = sectionToChinese(section)
      if (needsZero) sectionText = `零${sectionText}`
      integerText = `${sectionText}${cnSections[sectionIndex]}${integerText}`
      needsZero = section < 1000
    }
    integer = Math.floor(integer / 10000)
    sectionIndex += 1
  }

  const decimalText = `${jiao ? `${cnDigits[jiao]}角` : ''}${fen ? `${cnDigits[fen]}分` : ''}`
  return `${value < 0 ? '负' : ''}${integerText || '零'}元${decimalText || '整'}`
}

function AmountGrid({ value }: { value?: number }) {
  return (
    <div className="voucher-amount-grid">
      {amountToDigits(value).map((digit, index) => (
        <span key={`${index}-${amountUnits[index]}`}>{digit}</span>
      ))}
    </div>
  )
}

function EditableAmountCell({
  line,
  targetDirection,
  onLineChange,
}: {
  line: JournalEntryLine
  targetDirection: 'debit' | 'credit'
  onLineChange: (field: string, value: any) => void
}) {
  const active = line.direction === targetDirection
  const label = targetDirection === 'debit' ? '借' : '贷'

  return (
    <div className="voucher-cell voucher-amount-cell">
      <AmountGrid value={active ? line.amount : 0} />
      <div className={`voucher-amount-editor ${active ? 'active' : ''}`}>
        <Button
          size="small"
          type={active ? 'primary' : 'default'}
          onClick={() => onLineChange('direction', targetDirection)}
        >
          {label}
        </Button>
        {active && (
          <Input
            value={line.amount}
            onChange={(e) => onLineChange('amount', Number(e.target.value) || 0)}
            size="small"
          />
        )}
      </div>
    </div>
  )
}

export default function EntryEditor() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [entry, setEntry] = useState<JournalEntry | null>(null)
  const [subjects, setSubjects] = useState<SubjectTreeNode[]>([])
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    if (id) {
      getEntry(id).then((data) => {
        setEntry(data)
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

  return (
    <div className="voucher-page">
      <Space className="voucher-toolbar">
        <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/entries')}>返回</Button>
        <Tag color={entry.status === 'draft' ? 'blue' : entry.status === 'confirmed' ? 'green' : 'default'}>
          {entry.status === 'draft' ? '草稿' : entry.status === 'confirmed' ? '已确认' : '已导出'}
        </Tag>
        <Button icon={<PlusOutlined />} onClick={addLine} type="dashed">
          添加分录行
        </Button>
      </Space>

      <section className="voucher-sheet">
        <div className="voucher-head">
          <div className="voucher-head-left">
            <span>凭证字</span>
            <Select
              value={entry.voucher_type}
              onChange={(v) => handleHeaderChange('voucher_type', v)}
              className="voucher-small-select"
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
              onChange={(e) => handleHeaderChange('voucher_number', e.target.value)}
              placeholder="1"
            />
            <span>号</span>
            <span>日期</span>
            <DatePicker
              value={entry.voucher_date ? dayjs(entry.voucher_date) : null}
              onChange={(d) => handleHeaderChange('voucher_date', d?.format('YYYY-MM-DD') || '')}
              className="voucher-date-picker"
            />
          </div>
          <Typography.Title level={2} className="voucher-title">记账凭证</Typography.Title>
          <div className="voucher-period">
            {entry.voucher_date ? dayjs(entry.voucher_date).format('YYYY年M月') : dayjs().format('YYYY年M月')}
          </div>
        </div>

        <div className="voucher-table" style={{ gridTemplateRows: `64px repeat(${Math.max(entry.lines.length, 4)}, 96px) 80px` }}>
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
                    onChange={(e) => handleHeaderChange('summary', e.target.value)}
                  />
                ) : (
                  <Input
                    value={line.summary_detail || ''}
                    onChange={(e) => handleLineChange(line.id, 'summary_detail', e.target.value)}
                    placeholder="摘要"
                  />
                )}
                <Button
                  type="text"
                  danger
                  size="small"
                  className="voucher-row-delete"
                  icon={<DeleteOutlined />}
                  onClick={() => removeLine(line.id)}
                />
              </div>
              <div className="voucher-cell voucher-subject-cell">
                <Select
                  showSearch
                  value={line.account_code || undefined}
                  onChange={(v) => {
                    const found = subjectOptions.find((o) => o.value === v)
                    handleLineChange(line.id, 'account_code', v)
                    handleLineChange(line.id, 'account_name', found?.label?.split(' ').slice(1).join(' ') || '')
                  }}
                  options={subjectOptions}
                  placeholder="选择科目"
                  filterOption={(input, option) =>
                    (option?.label ?? '').includes(input) || (option?.value ?? '').includes(input)
                  }
                />
                <span className="voucher-subject-text">{line.account_code} {line.account_name}</span>
                <Space className="voucher-line-actions" size={4}>
                  <Select
                    value={line.direction}
                    onChange={(val) => handleLineChange(line.id, 'direction', val)}
                    size="small"
                    options={[
                      { value: 'debit', label: '借' },
                      { value: 'credit', label: '贷' },
                    ]}
                  />
                  <Input
                    value={line.amount}
                    onChange={(e) => handleLineChange(line.id, 'amount', Number(e.target.value) || 0)}
                    size="small"
                  />
                  <Button
                    type="text"
                    danger
                    size="small"
                    icon={<DeleteOutlined />}
                    onClick={() => removeLine(line.id)}
                  />
                </Space>
              </div>
              <EditableAmountCell
                line={line}
                targetDirection="debit"
                onLineChange={(field, value) => handleLineChange(line.id, field, value)}
              />
              <EditableAmountCell
                line={line}
                targetDirection="credit"
                onLineChange={(field, value) => handleLineChange(line.id, field, value)}
              />
            </div>
          ))}

          {Array.from({ length: Math.max(0, 4 - entry.lines.length) }).map((_, index) => (
            <div className="voucher-line-row voucher-empty-row" key={`empty-${index}`}>
              <div className="voucher-cell" />
              <div className="voucher-cell" />
              <div className="voucher-cell"><AmountGrid value={0} /></div>
              <div className="voucher-cell"><AmountGrid value={0} /></div>
            </div>
          ))}

          <div className="voucher-total-row">
            <div className="voucher-total-text">
              合计：{amountToChinese(debitTotal)}
              <Tag color={balanced ? 'green' : 'red'}>{balanced ? '借贷平衡' : `差额 ¥${Math.abs(debitTotal - creditTotal).toFixed(2)}`}</Tag>
            </div>
            <div className="voucher-total-amount"><AmountGrid value={debitTotal} /></div>
            <div className="voucher-total-amount"><AmountGrid value={creditTotal} /></div>
          </div>
        </div>

        <Space className="voucher-actions">
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
      </section>
    </div>
  )
}
