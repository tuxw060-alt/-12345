import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import {
  Card, Descriptions, Button, Space, Typography, Tag, Input, InputNumber,
  DatePicker, Select, Spin, message, Row, Col, Alert, Tabs, Table, Divider,
} from 'antd'
import { SaveOutlined, ThunderboltOutlined, ArrowLeftOutlined, FileTextOutlined, PictureOutlined, SearchOutlined } from '@ant-design/icons'
import { getInvoice, updateInvoice } from '../api/invoices'
import { generateEntry, createEntry } from '../api/entries'
import { getDocumentTypes, matchTemplates, generateDraftFromTemplate } from '../api/voucherTemplates'
import { useAppStore } from '../hooks/useAppStore'
import type { Invoice, DocumentType, VoucherTemplate, PreviewLine } from '../types/invoice'
import dayjs from 'dayjs'

export default function InvoiceReview() {
  const { id } = useParams<{ id: string }>()
  const [invoice, setInvoice] = useState<Invoice | null>(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [generating, setGenerating] = useState(false)
  const { currentClient } = useAppStore()
  const navigate = useNavigate()

  // Template-related state
  const [docTypes, setDocTypes] = useState<DocumentType[]>([])
  const [selectedDocTypeId, setSelectedDocTypeId] = useState<string | undefined>()
  const [settlementMethod, setSettlementMethod] = useState<string>('往来结算')
  const [businessType, setBusinessType] = useState<string | undefined>()
  const [matchedTemplates, setMatchedTemplates] = useState<VoucherTemplate[]>([])
  const [selectedTemplate, setSelectedTemplate] = useState<VoucherTemplate | null>(null)
  const [previewLines, setPreviewLines] = useState<PreviewLine[]>([])
  const [templateWarnings, setTemplateWarnings] = useState<string[]>([])

  useEffect(() => {
    if (id) {
      getInvoice(id).then((data) => {
        setInvoice(data)
        setLoading(false)
      })
    }
    getDocumentTypes(true).then(setDocTypes).catch(() => {})
  }, [id])

  // Match templates when selections change
  const handleMatchTemplates = async () => {
    if (!selectedDocTypeId) return
    try {
      const result = await matchTemplates({
        document_type_id: selectedDocTypeId,
        settlement_method: settlementMethod,
        business_type: businessType,
        search_text: invoice?.item_name || invoice?.vendor_name || '',
      })
      setMatchedTemplates(result.matched_templates)
      if (!businessType && result.suggested_business_type) {
        setBusinessType(result.suggested_business_type)
      }
      if (result.matched_templates.length > 0) {
        setSelectedTemplate(result.matched_templates[0])
      }
    } catch { /* ignore */ }
  }

  // Preview entry lines for selected template
  const handlePreviewDraft = async () => {
    if (!selectedTemplate || !currentClient || !invoice) return
    try {
      const result = await generateDraftFromTemplate({
        template_id: selectedTemplate.id,
        client_id: currentClient.id,
        voucher_date: invoice.invoice_date || dayjs().format('YYYY-MM-DD'),
        amounts: {
          total_amount: invoice.total_amount || 0,
          amount: invoice.amount || 0,
          tax_amount: invoice.tax_amount || 0,
        },
        summary_vars: {
          counterpartyName: invoice.vendor_name || '',
          itemName: invoice.item_name || '',
        },
        counterparty_name: invoice.vendor_name || undefined,
        source_invoice_id: invoice.id,
      })
      setPreviewLines(result.preview_lines)
      setTemplateWarnings(result.warnings)
      if (result.errors.length > 0) {
        message.error(result.errors.join('; '))
      }
    } catch (err: any) {
      message.error(err.response?.data?.detail || err.message || '预览失败')
    }
  }

  const handleFieldUpdate = (field: string, value: any) => {
    if (!invoice) return
    setInvoice({ ...invoice, [field]: value })
  }

  const handleSave = async () => {
    if (!invoice || !id) return
    setSaving(true)
    try {
      const updated = await updateInvoice(id, {
        invoice_type: invoice.invoice_type,
        invoice_code: invoice.invoice_code,
        invoice_number: invoice.invoice_number,
        invoice_date: invoice.invoice_date,
        total_amount: invoice.total_amount,
        amount: invoice.amount,
        tax_amount: invoice.tax_amount,
        vendor_name: invoice.vendor_name,
        vendor_tax_id: invoice.vendor_tax_id,
        buyer_name: invoice.buyer_name,
        buyer_tax_id: invoice.buyer_tax_id,
        item_name: invoice.item_name,
        remarks: invoice.remarks,
        suggested_subject_code: invoice.suggested_subject_code,
        suggested_subject_name: invoice.suggested_subject_name,
        client_id: currentClient?.id || invoice.client_id,
        human_verified: true,
      })
      setInvoice(updated)
      message.success('已保存')
    } catch (err: any) {
      message.error(`保存失败: ${err.message}`)
    } finally {
      setSaving(false)
    }
  }

  const handleGenerateEntry = async () => {
    if (!invoice || !id) return
    if (!currentClient) {
      message.warning('请先在顶部选择当前客户')
      return
    }
    setGenerating(true)
    try {
      // Try template engine first if template is selected
      if (selectedTemplate) {
        const result = await generateDraftFromTemplate({
          template_id: selectedTemplate.id,
          client_id: currentClient.id,
          voucher_date: invoice.invoice_date || dayjs().format('YYYY-MM-DD'),
          amounts: {
            total_amount: invoice.total_amount || 0,
            amount: invoice.amount || 0,
            tax_amount: invoice.tax_amount || 0,
          },
          summary_vars: {
            counterpartyName: invoice.vendor_name || '',
            itemName: invoice.item_name || '',
          },
          counterparty_name: invoice.vendor_name || undefined,
          source_invoice_id: invoice.id,
        })
        if (result.errors.length > 0) {
          message.error(result.errors.join('; '))
          setGenerating(false)
          return
        }
        if (result.entry_id) {
          message.success('凭证草稿已生成！')
          navigate(`/entries/${result.entry_id}/edit`)
          return
        }
      }
      // Fallback to old method
      const entryData = await generateEntry({
        invoice_id: id,
        client_id: currentClient.id,
        voucher_date: invoice.invoice_date || dayjs().format('YYYY-MM-DD'),
      })
      const entry = await createEntry(entryData)
      message.success('凭证已生成！')
      navigate(`/entries/${entry.id}/edit`)
    } catch (err: any) {
      message.error(`生成凭证失败: ${err.message}`)
    } finally {
      setGenerating(false)
    }
  }

  if (loading) return <Spin size="large" style={{ display: 'block', margin: '100px auto' }} />
  if (!invoice) return <Typography.Text type="danger">发票不存在</Typography.Text>

  // Extract OCR raw text from AI response
  const rawText = (invoice as any).raw_ai_response?.raw_text || ''
  const warnings = (invoice as any).raw_ai_response?.warnings || []

  const subjectOptions = [
    { value: '5602.05', label: '5602.05 管理费用-业务招待费' },
    { value: '5602.02', label: '5602.02 管理费用-办公费' },
    { value: '5602.03', label: '5602.03 管理费用-交通费' },
    { value: '5602.04', label: '5602.04 管理费用-差旅费' },
    { value: '5602.08', label: '5602.08 管理费用-租赁费' },
    { value: '5602.09', label: '5602.09 管理费用-物业水电费' },
    { value: '5602.10', label: '5602.10 管理费用-中介咨询费' },
    { value: '5602.11', label: '5602.11 管理费用-软件服务费' },
    { value: '5602.14', label: '5602.14 管理费用-维修费' },
    { value: '5602.15', label: '5602.15 管理费用-快递物流费' },
    { value: '5602.16', label: '5602.16 管理费用-通讯费' },
    { value: '5602.06', label: '5602.06 管理费用-职工教育经费' },
    { value: '5602.07', label: '5602.07 管理费用-福利费' },
    { value: '5602.17', label: '5602.17 管理费用-社保费' },
    { value: '5602.18', label: '5602.18 管理费用-公积金' },
    { value: '5602.19', label: '5602.19 管理费用-招聘费' },
    { value: '5602.99', label: '5602.99 管理费用-其他' },
    { value: '5601.01', label: '5601.01 销售费用-广告宣传费' },
    { value: '5603.01', label: '5603.01 财务费用-利息支出' },
    { value: '5603.02', label: '5603.02 财务费用-手续费' },
    { value: '5001', label: '5001 主营业务收入' },
    { value: '1601', label: '1601 固定资产' },
  ]

  return (
    <div>
      <Space style={{ marginBottom: 16 }}>
        <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/invoices/upload')}>返回</Button>
        <Typography.Title level={4} style={{ margin: 0 }}>
          {invoice.image_filename}
        </Typography.Title>
        <Tag color={invoice.ocr_status === 'done' ? 'green' : 'red'}>
          {invoice.ocr_status === 'done' ? `识别完成 ${Math.round(invoice.ocr_confidence || 0)}%` : '识别失败'}
        </Tag>
      </Space>

      {invoice.ocr_status === 'failed' && (
        <Alert type="error" message={invoice.ocr_error_msg || 'AI识别失败'} style={{ marginBottom: 16 }} />
      )}
      {warnings.length > 0 && (
        <Alert type="warning" message={warnings.join('；')} style={{ marginBottom: 16 }} showIcon />
      )}

      <Row gutter={16}>
        {/* Left: AI Extracted Fields */}
        <Col span={10}>
          <Card title="AI 识别字段（点击修改）" size="small" style={{ marginBottom: 12 }}>
            <Descriptions column={1} bordered size="small">
              <Descriptions.Item label="发票类型">
                <Select value={invoice.invoice_type} onChange={(v) => handleFieldUpdate('invoice_type', v)}
                  style={{ width: '100%' }} allowClear placeholder="选择类型"
                  options={['增值税专用发票','增值税普通发票','增值税电子普通发票','全电发票','定额发票','其他'].map(t=>({value:t,label:t}))} />
              </Descriptions.Item>
              <Descriptions.Item label="发票号码">
                <Input value={invoice.invoice_number || ''} onChange={(e) => handleFieldUpdate('invoice_number', e.target.value)} placeholder="发票号码" />
              </Descriptions.Item>
              <Descriptions.Item label="开票日期">
                <DatePicker value={invoice.invoice_date ? dayjs(invoice.invoice_date) : null}
                  onChange={(d) => handleFieldUpdate('invoice_date', d?.format('YYYY-MM-DD') || null)} style={{ width: '100%' }} />
              </Descriptions.Item>
              <Descriptions.Item label="金额(不含税)">
                <InputNumber value={invoice.amount} onChange={(v) => handleFieldUpdate('amount', v)}
                  prefix="¥" style={{ width: '100%' }} precision={2} />
              </Descriptions.Item>
              <Descriptions.Item label="税额">
                <InputNumber value={invoice.tax_amount} onChange={(v) => handleFieldUpdate('tax_amount', v)}
                  prefix="¥" style={{ width: '100%' }} precision={2} />
              </Descriptions.Item>
              <Descriptions.Item label="价税合计">
                <InputNumber value={invoice.total_amount} onChange={(v) => handleFieldUpdate('total_amount', v)}
                  prefix="¥" style={{ width: '100%' }} precision={2} />
              </Descriptions.Item>
              <Descriptions.Item label="销售方">
                <Input value={invoice.vendor_name || ''} onChange={(e) => handleFieldUpdate('vendor_name', e.target.value)} placeholder="销售方名称" />
              </Descriptions.Item>
              <Descriptions.Item label="货物/服务">
                <Input.TextArea value={invoice.item_name || ''} onChange={(e) => handleFieldUpdate('item_name', e.target.value)} rows={2} />
              </Descriptions.Item>
            </Descriptions>
          </Card>

          {/* AI Subject Suggestion */}
          <Card title="AI 推荐科目" size="small" style={{ marginBottom: 12, borderLeft: '3px solid #1677ff' }}>
            <Space direction="vertical" style={{ width: '100%' }}>
              <Select value={invoice.suggested_subject_code || undefined}
                onChange={(v) => {
                  handleFieldUpdate('suggested_subject_code', v)
                  const found = subjectOptions.find(o => o.value === v)
                  handleFieldUpdate('suggested_subject_name', found?.label?.split(' ').slice(1).join(' ') || '')
                }}
                style={{ width: '100%' }} showSearch placeholder="选择或搜索科目"
                options={subjectOptions}
                filterOption={(input, option) => (option?.label ?? '').includes(input)}
              />
              {invoice.subject_confidence != null && (
                <Tag color={invoice.subject_confidence >= 90 ? 'green' : invoice.subject_confidence >= 70 ? 'orange' : 'red'}>
                  匹配置信度 {Math.round(invoice.subject_confidence)}%
                </Tag>
              )}
            </Space>
          </Card>

          {/* Template Configuration */}
          <Card title="分录模板配置" size="small" style={{ marginBottom: 12, borderLeft: '3px solid #52c41a' }}>
            <Space direction="vertical" style={{ width: '100%' }} size={8}>
              <Space wrap>
                <Select placeholder="单据名称" style={{ width: 180 }}
                  value={selectedDocTypeId}
                  onChange={(v) => { setSelectedDocTypeId(v); setSelectedTemplate(null); setPreviewLines([]) }}
                  options={docTypes.map(d => ({ value: d.id, label: `${d.code} ${d.name}` }))}
                />
                <Select placeholder="结算方式" style={{ width: 120 }}
                  value={settlementMethod} onChange={setSettlementMethod}
                  options={['往来结算','现金','银行','未结算','其他'].map(v=>({value:v,label:v}))}
                />
                <Select placeholder="业务类型" style={{ width: 140 }}
                  value={businessType} onChange={setBusinessType}
                  showSearch
                  options={['销售收入','采购商品','福利费','运杂费','服务费','办公用品','业务招待费','交通费','利息','手续费','税费缴纳','还款','往来款','银行收款','银行付款','利息收入'].map(v=>({value:v,label:v}))}
                />
                <Button icon={<SearchOutlined />} onClick={handleMatchTemplates} size="small">
                  匹配模板
                </Button>
              </Space>

              {matchedTemplates.length > 0 && (
                <>
                  <Select placeholder="选择模板" style={{ width: '100%' }}
                    value={selectedTemplate?.id}
                    onChange={(v) => {
                      const tpl = matchedTemplates.find(t => t.id === v)
                      setSelectedTemplate(tpl || null)
                      setPreviewLines([])
                    }}
                    options={matchedTemplates.map(t => ({
                      value: t.id,
                      label: `${t.document_name} / ${t.business_type} / ${t.settlement_method} [${t.summary_template}]`,
                    }))}
                  />
                  {selectedTemplate && (
                    <Button type="dashed" size="small" onClick={handlePreviewDraft}>
                      预览分录
                    </Button>
                  )}
                </>
              )}

              {previewLines.length > 0 && (
                <>
                  <Divider style={{ margin: '8px 0' }} />
                  <Typography.Text strong>分录预览：</Typography.Text>
                  <Table
                    dataSource={previewLines}
                    rowKey="line_no"
                    size="small"
                    pagination={false}
                    columns={[
                      { title: '#', dataIndex: 'line_no', width: 40 },
                      { title: '方向', dataIndex: 'debit_credit', width: 50,
                        render: (v: string) => <Tag color={v==='debit'?'blue':'red'}>{v==='debit'?'借':'贷'}</Tag> },
                      { title: '科目', key: 'acct', render: (_: any, r: PreviewLine) => (
                        <span>
                          <span style={{fontFamily:'monospace'}}>{r.account_code}</span>
                          {' '}{r.account_name}
                          {r.is_pending && <Tag color="orange" style={{marginLeft:4}}>待选择</Tag>}
                          {r.matched_sub_code && <Tag color="green" style={{marginLeft:4}}>{r.matched_sub_code}</Tag>}
                        </span>
                      )},
                      { title: '金额来源', dataIndex: 'amount_source', width: 100 },
                      { title: '预计金额', dataIndex: 'estimated_amount', width: 100,
                        render: (v:number)=>`¥${v.toFixed(2)}` },
                    ]}
                  />
                  {templateWarnings.length > 0 && (
                    <Alert type="warning" message={templateWarnings.map((w,i)=><div key={i}>{w}</div>)}
                      style={{marginTop:8}} />
                  )}
                </>
              )}
            </Space>
          </Card>

          {/* Actions */}
          <Space direction="vertical" style={{ width: '100%' }}>
            <Button type="primary" icon={<SaveOutlined />} block onClick={handleSave} loading={saving}>
              保存审核结果
            </Button>
            <Button icon={<ThunderboltOutlined />} block onClick={handleGenerateEntry}
              loading={generating} style={{ background: '#52c41a', borderColor: '#52c41a', color: '#fff' }}>
              {selectedTemplate ? '按模板生成凭证草稿' : '一键生成记账凭证'}
            </Button>
          </Space>
        </Col>

        {/* Right: OCR Raw Text & Image */}
        <Col span={14}>
          <Tabs defaultActiveKey="ocr" size="small" items={[
            {
              key: 'ocr',
              label: <span><FileTextOutlined /> OCR 提取原文</span>,
              children: (
                <Card size="small" style={{ maxHeight: 500, overflow: 'auto', background: '#fafafa' }}>
                  <pre style={{ whiteSpace: 'pre-wrap', wordBreak: 'break-all', fontSize: 12, fontFamily: 'monospace', margin: 0 }}>
                    {rawText || '（无OCR文字——请确认文件是否包含文字层）'}
                  </pre>
                </Card>
              ),
            },
            {
              key: 'image',
              label: <span><PictureOutlined /> 发票预览</span>,
              children: (
                <Card size="small" style={{ textAlign: 'center' }}>
                  <img
                    src={`/uploads/${invoice.id}${invoice.image_filename.slice(invoice.image_filename.lastIndexOf('.'))}`}
                    alt="发票预览"
                    style={{ maxWidth: '100%', maxHeight: 500, objectFit: 'contain', border: '1px solid #eee' }}
                    onError={(e) => { (e.target as HTMLImageElement).style.display = 'none' }}
                  />
                  {invoice.image_filename.toLowerCase().endsWith('.pdf') && (
                    <Typography.Text type="secondary" style={{ display: 'block', marginTop: 8 }}>
                      PDF文件——显示渲染的第一页预览
                    </Typography.Text>
                  )}
                </Card>
              ),
            },
          ]} />
        </Col>
      </Row>
    </div>
  )
}
