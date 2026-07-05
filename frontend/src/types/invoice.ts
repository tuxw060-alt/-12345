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
  parent_account_name: string | null
  category: string
  direction: 'debit' | 'credit'
  is_leaf: boolean
  is_active: boolean
  created_from: string | null
  created_at: string
  updated_at: string | null
}

export interface SubjectTreeNode {
  code: string
  name: string
  full_name: string | null
  level: number
  parent_code: string | null
  parent_account_name: string | null
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
  account_full_name: string | null
  parent_account_code: string | null
  parent_account_name: string | null
  auxiliary_type: string | null
  auxiliary_code: string | null
  auxiliary_name: string | null
  counterparty_name: string | null
  counterparty_account: string | null
  source_type: string | null
  source_document_id: string | null
  source_row_id: string | null
  manual_account_override: boolean
  account_selection_source: 'auto' | 'manual' | 'rematch' | 'new_sub_account'
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

export interface BankStatementTransaction {
  id: string
  upload_id: string
  client_id: string
  transaction_date: string | null
  summary: string | null
  counterparty: string | null
  account_number: string | null
  income_amount: number | null
  expense_amount: number | null
  balance: number | null
  suggested_subject_code: string | null
  suggested_subject_name: string | null
  selected_account_code: string | null
  selected_account_name: string | null
  selected_account_full_name: string | null
  selected_parent_account_code: string | null
  selected_parent_account_name: string | null
  manual_account_override: boolean
  account_selection_source: 'auto' | 'manual' | 'rematch' | 'new_sub_account'
  document_type_id: string | null
  document_name: string | null
  settlement_method: string | null
  business_type: string | null
  selected_template_id: string | null
  recommended_template_id: string | null
  template_match_reason: string | null
  subject_reason: string | null
  confidence: number | null
  status: 'recognized' | 'failed'
  error_msg: string | null
  entry_id: string | null
  created_at: string
}

export interface BankStatementUpload {
  id: string
  client_id: string
  filename: string
  status: 'pending' | 'done' | 'failed'
  error_msg: string | null
  file_type: string | null
  processing_mode: string | null
  use_ocr: boolean
  use_ai: boolean
  processing_display: string | null
  processing_description: string | null
  total_rows: number | null
  valid_rows: number | null
  error_rows: number | null
  created_at: string
  transactions: BankStatementTransaction[]
}

// API list responses
export interface ListResponse<T> {
  items: T[]
  total: number
}
