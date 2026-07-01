/** TypeScript types matching backend Pydantic schemas. */

export interface Client {
  id: string
  name: string
  tax_id: string | null
  tax_type: 'general' | 'small'
  contact_person: string | null
  phone: string | null
  notes: string | null
  is_active: boolean
  created_at: string
  updated_at: string | null
}

export interface Invoice {
  id: string
  client_id: string | null
  image_filename: string
  invoice_type: string | null
  invoice_code: string | null
  invoice_number: string | null
  invoice_date: string | null
  total_amount: number | null
  amount: number | null
  tax_amount: number | null
  vendor_name: string | null
  vendor_tax_id: string | null
  buyer_name: string | null
  buyer_tax_id: string | null
  item_name: string | null
  remarks: string | null
  suggested_subject_code: string | null
  suggested_subject_name: string | null
  subject_confidence: number | null
  ocr_status: 'pending' | 'done' | 'failed'
  ocr_confidence: number | null
  ocr_error_msg: string | null
  human_verified: boolean
  created_at: string
}

export interface AccountSubject {
  id: string
  client_id: string | null
  code: string
  name: string
  full_name: string | null
  level: number
  parent_code: string | null
  category: string
  direction: 'debit' | 'credit'
  is_leaf: boolean
  is_active: boolean
  created_at: string
}

export interface SubjectTreeNode {
  code: string
  name: string
  full_name: string | null
  level: number
  direction: string
  is_leaf: boolean
  children: SubjectTreeNode[]
}

export interface MatchingRule {
  id: string
  keywords: string
  subject_code: string
  subject_name: string | null
  priority: number
  client_id: string | null
  is_active: boolean
  created_at: string
}

export interface JournalEntryLine {
  id: string
  entry_id: string
  line_number: number
  account_code: string
  account_name: string
  direction: 'debit' | 'credit'
  amount: number
  summary_detail: string | null
}

export interface JournalEntry {
  id: string
  client_id: string
  source_invoice_id: string | null
  voucher_date: string
  voucher_type: string
  voucher_number: string | null
  summary: string
  status: 'draft' | 'confirmed' | 'exported'
  lines: JournalEntryLine[]
  created_at: string
  updated_at: string | null
}

// API list responses
export interface ListResponse<T> {
  items: T[]
  total: number
}
