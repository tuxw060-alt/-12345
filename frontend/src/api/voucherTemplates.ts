import api from './client'
import type {
  DocumentType, VoucherTemplate, VoucherTemplateLine,
  GenerateDraftResponse, ListResponse,
} from '../types/invoice'

// ── Document Types ──────────────────────────────────────────

export async function getDocumentTypes(enabledOnly = false): Promise<DocumentType[]> {
  const res = await api.get<ListResponse<DocumentType>>('/document-types', {
    params: { enabled_only: enabledOnly },
  })
  return res.data.items
}

export async function createDocumentType(data: Partial<DocumentType>): Promise<DocumentType> {
  const res = await api.post<DocumentType>('/document-types', data)
  return res.data
}

export async function updateDocumentType(id: string, data: Partial<DocumentType>): Promise<DocumentType> {
  const res = await api.put<DocumentType>(`/document-types/${id}`, data)
  return res.data
}

export async function deleteDocumentType(id: string): Promise<void> {
  await api.delete(`/document-types/${id}`)
}

export async function restorePresetDocumentTypes(): Promise<DocumentType[]> {
  const res = await api.post<ListResponse<DocumentType>>('/document-types/restore-presets')
  return res.data.items
}

// ── Voucher Templates ───────────────────────────────────────

export async function getVoucherTemplates(documentTypeId?: string): Promise<VoucherTemplate[]> {
  const res = await api.get<ListResponse<VoucherTemplate>>('/voucher-templates', {
    params: documentTypeId ? { document_type_id: documentTypeId } : {},
  })
  return res.data.items
}

export async function getVoucherTemplate(id: string): Promise<VoucherTemplate> {
  const res = await api.get<VoucherTemplate>(`/voucher-templates/${id}`)
  return res.data
}

export async function createVoucherTemplate(data: {
  document_type_id?: string | null
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
  const res = await api.post<VoucherTemplate>('/voucher-templates', data)
  return res.data
}

export async function updateVoucherTemplate(
  id: string,
  data: Partial<{
    document_type_id: string | null
    document_name: string
    settlement_method: string
    business_type: string
    summary_template: string
    is_enabled: boolean
    priority: number
    lines: any[]
  }>
): Promise<VoucherTemplate> {
  const res = await api.put<VoucherTemplate>(`/voucher-templates/${id}`, data)
  return res.data
}

export async function deleteVoucherTemplate(id: string): Promise<void> {
  await api.delete(`/voucher-templates/${id}`)
}

export async function copyVoucherTemplate(id: string): Promise<VoucherTemplate> {
  const res = await api.post<VoucherTemplate>(`/voucher-templates/${id}/copy`)
  return res.data
}

export async function toggleVoucherTemplate(id: string): Promise<VoucherTemplate> {
  const res = await api.put<VoucherTemplate>(`/voucher-templates/${id}/toggle`)
  return res.data
}

// ── Matching & Generation ───────────────────────────────────

export async function matchTemplates(params: {
  document_type_id?: string
  settlement_method?: string
  business_type?: string
  search_text?: string
}): Promise<{
  matched_templates: VoucherTemplate[]
  suggested_document_type_id: string | null
  suggested_business_type: string | null
  suggested_settlement_method: string | null
}> {
  const res = await api.post('/voucher-templates/match', params)
  return res.data
}

export async function generateDraftFromTemplate(data: {
  template_id: string
  client_id: string
  voucher_date?: string
  amounts: {
    total_amount?: number
    amount?: number
    tax_amount?: number
    income_amount?: number
    expense_amount?: number
    balance?: number
  }
  summary_vars?: Record<string, string>
  counterparty_name?: string
  source_invoice_id?: string
  source_transaction_id?: string
}): Promise<GenerateDraftResponse> {
  const res = await api.post<GenerateDraftResponse>('/voucher-templates/generate-draft', data)
  return res.data
}
