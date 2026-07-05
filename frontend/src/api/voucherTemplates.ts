import api from './client'
import type {
  DocumentType, VoucherTemplate,
  GenerateDraftResponse, ListResponse,
} from '../types/invoice'

const BASE = '/document-vouchers'

// ── Document Types ──────────────────────────────────────────

export async function getDocumentTypes(companyId?: string): Promise<DocumentType[]> {
  const res = await api.get<ListResponse<DocumentType>>(`${BASE}/document-types`, {
    params: companyId ? { company_id: companyId } : {},
  })
  return res.data.items
}

export async function createDocumentType(data: Partial<DocumentType>): Promise<DocumentType> {
  const res = await api.post<DocumentType>(`${BASE}/document-types`, data)
  return res.data
}

export async function updateDocumentType(id: string, data: Partial<DocumentType>): Promise<DocumentType> {
  const res = await api.put<DocumentType>(`${BASE}/document-types/${id}`, data)
  return res.data
}

export async function deleteDocumentType(id: string): Promise<void> {
  await api.delete(`${BASE}/document-types/${id}`)
}

export async function restorePresetDocumentTypes(): Promise<DocumentType[]> {
  await api.post(`${BASE}/document-types/restore-defaults`)
  const res = await api.get<ListResponse<DocumentType>>(`${BASE}/document-types`)
  return res.data.items
}

// ── Voucher Templates ───────────────────────────────────────

export async function getVoucherTemplates(documentTypeId?: string): Promise<VoucherTemplate[]> {
  const res = await api.get<ListResponse<VoucherTemplate>>(`${BASE}/templates`, {
    params: documentTypeId ? { document_type_id: documentTypeId } : {},
  })
  return res.data.items
}

export async function getVoucherTemplate(id: string): Promise<VoucherTemplate> {
  const res = await api.get<VoucherTemplate>(`${BASE}/templates/${id}`)
  return res.data
}

export async function createVoucherTemplate(data: {
  document_type_id: string
  document_name: string
  settlement_method: string
  business_type: string
  summary_template: string
  priority?: number
  lines: {
    line_no: number
    debit_credit: string
    account_code: string
    account_name: string
    account_full_name?: string | null
    parent_account_code?: string | null
    amount_source: string
    require_sub_account?: boolean
    sub_account_match_mode?: string
    allow_manual_edit?: boolean
  }[]
}): Promise<VoucherTemplate> {
  const res = await api.post<VoucherTemplate>(`${BASE}/templates`, data)
  return res.data
}

export async function updateVoucherTemplate(
  id: string,
  data: Record<string, any>
): Promise<VoucherTemplate> {
  const res = await api.put<VoucherTemplate>(`${BASE}/templates/${id}`, data)
  return res.data
}

export async function deleteVoucherTemplate(id: string): Promise<void> {
  await api.delete(`${BASE}/templates/${id}`)
}

export async function copyVoucherTemplate(id: string): Promise<VoucherTemplate> {
  const res = await api.post<VoucherTemplate>(`${BASE}/templates/${id}/copy`)
  return res.data
}

// ── Matching & Generation ───────────────────────────────────

export async function recommendTemplate(params: {
  client_id?: string
  template_id?: string
  document_type_id?: string
  document_name?: string
  settlement_method?: string
  business_type?: string
  summary?: string
  counterparty_name?: string
  total_amount?: number
  amount?: number
  tax_amount?: number
  income_amount?: number
  expense_amount?: number
  balance?: number
}): Promise<{
  template_id: string | null
  document_type_id: string | null
  document_name: string | null
  settlement_method: string | null
  business_type: string
  confidence: number
  reason: string
}> {
  const res = await api.post(`${BASE}/recommend-template`, params)
  return res.data
}
