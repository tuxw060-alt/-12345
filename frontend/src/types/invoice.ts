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
  created_at: string
  transactions: BankStatementTransaction[]
}

// Document Type
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

// Voucher Template
export interface VoucherTemplateLine {
  id: string
  template_id: string
  line_no: number
  debit_credit: 'debit' | 'credit'
  account_code: string
  account_name: string
  account_full_name: string | null
  parent_account_code: string | null
  amount_source: string
  require_sub_account: boolean
  sub_account_match_mode: string
  allow_manual_edit: boolean
  created_at: string
  updated_at: string | null
}

export interface VoucherTemplate {
  id: string
  company_id: string | null
  document_type_id: string | null
  document_name: string
  settlement_method: string
  business_type: string
  summary_template: string
  is_enabled: boolean
  priority: number
  created_from: string
  lines: VoucherTemplateLine[]
  created_at: string
  updated_at: string | null
}

export interface PreviewLine {
  line_no: number
  debit_credit: string
  account_code: string
  account_name: string
  amount_source: string
  estimated_amount: number
  require_sub_account: boolean
  sub_account_match_mode: string
  matched_sub_code: string | null
  matched_sub_name: string | null
  is_pending: boolean
  warning: string | null
}

export interface GenerateDraftResponse {
  entry_id: string | null
  status: string
  preview_lines: PreviewLine[]
  warnings: string[]
  errors: string[]
}

// API list responses
export interface ListResponse<T> {
  items: T[]
  total: number
}
