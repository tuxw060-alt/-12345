import api from './client'

export interface DocumentType {
  id: string
  company_id: string | null
  code: string
  category: string
  name: string
  is_system: boolean
  is_enabled: boolean
  created_at: string
  updated_at: string | null
}

export interface VoucherTemplateLine {
  id?: string
  template_id?: string
  line_no: number
  debit_credit: 'debit' | 'credit'
  account_code: string
  account_name: string
  account_full_name?: string | null
  parent_account_code?: string | null
  amount_source: string
  require_sub_account: boolean
  sub_account_match_mode: string
  allow_manual_edit: boolean
}

export interface VoucherTemplate {
  id: string
  company_id: string | null
  document_type_id: string
  document_name: string
  settlement_method: string
  business_type: string
  summary_template: string
  is_enabled: boolean
  priority: number
  created_from: string
  created_at: string
  updated_at: string | null
  lines: VoucherTemplateLine[]
}

export interface ListResponse<T> {
  items: T[]
  total: number
}

export const settlementMethods = ['往来结算', '现金', '银行', '未结算', '其他']
export const amountSources = [
  { value: 'totalAmount', label: '合计金额' },
  { value: 'amount', label: '金额' },
  { value: 'taxAmount', label: '税额' },
  { value: 'incomeAmount', label: '收入金额' },
  { value: 'expenseAmount', label: '支出金额' },
  { value: 'balance', label: '余额' },
  { value: 'manual', label: '手工输入' },
  { value: 'zero', label: '0' },
]
export const subAccountModes = [
  { value: 'none', label: '无' },
  { value: 'customer', label: '客户' },
  { value: 'supplier', label: '供应商' },
  { value: 'counterparty', label: '对方户名' },
  { value: 'legacy_sub_account', label: '老账套明细' },
  { value: 'bank_account', label: '银行账户' },
]

export async function listDocumentTypes(companyId?: string) {
  const res = await api.get<ListResponse<DocumentType>>('/document-vouchers/document-types', {
    params: { company_id: companyId },
  })
  return res.data
}

export async function createDocumentType(data: Partial<DocumentType>) {
  const res = await api.post<DocumentType>('/document-vouchers/document-types', data)
  return res.data
}

export async function updateDocumentType(id: string, data: Partial<DocumentType>) {
  const res = await api.put<DocumentType>(`/document-vouchers/document-types/${id}`, data)
  return res.data
}

export async function deleteDocumentType(id: string) {
  await api.delete(`/document-vouchers/document-types/${id}`)
}

export async function restoreDocumentTypeDefaults() {
  await api.post('/document-vouchers/document-types/restore-defaults')
}

export async function listVoucherTemplates(params?: {
  company_id?: string
  document_type_id?: string
  enabled_only?: boolean
}) {
  const res = await api.get<ListResponse<VoucherTemplate>>('/document-vouchers/templates', { params })
  return res.data
}

export async function createVoucherTemplate(data: Partial<VoucherTemplate> & { lines: VoucherTemplateLine[] }) {
  const res = await api.post<VoucherTemplate>('/document-vouchers/templates', data)
  return res.data
}

export async function updateVoucherTemplate(id: string, data: Partial<VoucherTemplate> & { lines?: VoucherTemplateLine[] }) {
  const res = await api.put<VoucherTemplate>(`/document-vouchers/templates/${id}`, data)
  return res.data
}

export async function deleteVoucherTemplate(id: string) {
  await api.delete(`/document-vouchers/templates/${id}`)
}

export async function copyVoucherTemplate(id: string) {
  const res = await api.post<VoucherTemplate>(`/document-vouchers/templates/${id}/copy`)
  return res.data
}
