import api from './client'
import type { JournalEntry } from '../types/invoice'

export interface TemplateLine {
  line_number: number
  account_code: string
  account_name: string
  direction: string
  amount_source: string
  fixed_amount: number | null
  summary_detail: string | null
}

export interface EntryTemplate {
  id: string
  name: string
  description: string | null
  summary_template: string
  voucher_type: string
  client_id: string | null
  lines: TemplateLine[]
}

export async function listTemplates(clientId?: string) {
  const res = await api.get('/templates', { params: clientId ? { client_id: clientId } : {} })
  return res.data
}

export async function applyTemplate(data: {
  template_id: string
  client_id: string
  voucher_date: string
  summary?: string
  amounts?: Record<number, number>
}): Promise<JournalEntry> {
  const res = await api.post<JournalEntry>('/templates/apply', data)
  return res.data
}
