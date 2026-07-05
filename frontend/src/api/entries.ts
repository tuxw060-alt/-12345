import api from './client'
import type { JournalEntry, ListResponse } from '../types/invoice'

export interface EntryGenerateRequest {
  invoice_id: string
  client_id: string
  voucher_date?: string
  voucher_type?: string
  summary?: string
}

export interface EntryCreateData {
  voucher_date: string
  voucher_type: string
  voucher_number?: string | null
  summary: string
  client_id: string
  source_invoice_id?: string
  lines: {
    line_number: number
    account_code: string
    account_name: string
    direction: 'debit' | 'credit'
    amount: number
    summary_detail?: string
    account_full_name?: string | null
    parent_account_code?: string | null
    parent_account_name?: string | null
    auxiliary_type?: string | null
    auxiliary_code?: string | null
    auxiliary_name?: string | null
    counterparty_name?: string | null
    counterparty_account?: string | null
    source_type?: string | null
    source_document_id?: string | null
    source_row_id?: string | null
    manual_account_override?: boolean
    account_selection_source?: 'auto' | 'manual' | 'rematch' | 'new_sub_account'
  }[]
}

export async function generateEntry(data: EntryGenerateRequest): Promise<EntryCreateData> {
  const res = await api.post<EntryCreateData>('/entries/generate', data)
  return res.data
}

export async function listEntries(params?: {
  client_id?: string
  status?: string
  date_from?: string
  date_to?: string
  offset?: number
  limit?: number
}): Promise<ListResponse<JournalEntry>> {
  const res = await api.get<ListResponse<JournalEntry>>('/entries', { params })
  return res.data
}

export async function getEntry(id: string): Promise<JournalEntry> {
  const res = await api.get<JournalEntry>(`/entries/${id}`)
  return res.data
}

export async function createEntry(data: EntryCreateData): Promise<JournalEntry> {
  const res = await api.post<JournalEntry>('/entries', data)
  return res.data
}

export async function updateEntry(id: string, data: Partial<EntryCreateData>): Promise<JournalEntry> {
  const res = await api.put<JournalEntry>(`/entries/${id}`, data)
  return res.data
}

export async function confirmEntry(id: string): Promise<JournalEntry> {
  const res = await api.post<JournalEntry>(`/entries/${id}/confirm`)
  return res.data
}

export async function batchConfirm(ids: string[]): Promise<{ confirmed: number; failed: any[] }> {
  const res = await api.post('/entries/batch-confirm', ids)
  return res.data
}

export async function batchDeleteEntries(ids: string[]): Promise<{ deleted: number; failed: any[] }> {
  const res = await api.post('/entries/batch-delete', ids)
  return res.data
}

export async function deleteEntry(id: string): Promise<void> {
  await api.delete(`/entries/${id}`)
}

export interface ExportRequest {
  client_id?: string
  date_from?: string
  date_to?: string
  entry_ids?: string[]
}

export async function previewExport(data: ExportRequest) {
  const res = await api.post('/export/preview', data)
  return res.data
}

export async function exportKingdee(data: ExportRequest): Promise<Blob> {
  const res = await api.post('/export/kingdee', data, { responseType: 'blob' })
  return res.data
}
