import api from './client'
import type { BankStatementUpload, ListResponse } from '../types/invoice'

export interface BankStatementUploadResult {
  upload: BankStatementUpload
  entry_ids: string[]
}

export async function uploadBankStatement(
  file: File,
  clientId: string,
  autoGenerate = false,
) {
  const form = new FormData()
  form.append('file', file)
  const res = await api.post<BankStatementUploadResult>('/bank-statements/upload', form, {
    params: { client_id: clientId, auto_generate: autoGenerate },
  })
  return res.data
}

export async function batchUploadBankStatements(
  files: File[],
  clientId: string,
  autoGenerate = false,
) {
  const results: BankStatementUploadResult[] = []
  for (const file of files) {
    try {
      results.push(await uploadBankStatement(file, clientId, autoGenerate))
    } catch (error: any) {
      results.push({
        upload: {
          id: `${file.name}-${Date.now()}`,
          client_id: clientId,
          filename: file.name,
          status: 'failed',
          error_msg: error?.response?.data?.detail || error?.message || '上传失败',
          file_type: null,
          processing_mode: null,
          use_ocr: false,
          use_ai: false,
          processing_display: null,
          processing_description: null,
          total_rows: null,
          valid_rows: null,
          error_rows: null,
          created_at: new Date().toISOString(),
          transactions: [],
        },
        entry_ids: [],
      })
    }
  }
  return results
}

export async function listBankStatementUploads(params?: {
  client_id?: string
  status?: string
  offset?: number
  limit?: number
}) {
  const res = await api.get<ListResponse<BankStatementUpload>>('/bank-statements', { params })
  return res.data
}

export async function batchDeleteBankStatementUploads(uploadIds: string[]) {
  const res = await api.post<{ deleted: number; failed: any[] }>('/bank-statements/batch-delete', {
    upload_ids: uploadIds,
  })
  return res.data
}

export async function generateBankStatementEntry(transactionId: string) {
  const res = await api.post<{ entry_id: string }>(
    `/bank-statements/transactions/${transactionId}/generate-entry`,
  )
  return res.data
}

export async function updateBankStatementTransactionAccount(
  transactionId: string,
  data: {
    account_code: string
    account_name: string
    account_full_name?: string | null
    parent_account_code?: string | null
    parent_account_name?: string | null
    source?: 'manual' | 'rematch' | 'new_sub_account'
  },
) {
  const res = await api.patch(`/bank-statements/transactions/${transactionId}/account-selection`, data)
  return res.data
}

export async function generateBankStatementEntries(clientId: string) {
  const res = await api.post<{ entry_ids: string[]; generated: number }>(
    '/bank-statements/generate-entries',
    { client_id: clientId },
  )
  return res.data
}

export async function updateBankStatementTransactionTemplate(
  transactionId: string,
  data: {
    document_type_id?: string | null
    document_name?: string | null
    settlement_method?: string | null
    business_type?: string | null
    template_id?: string | null
  },
) {
  const res = await api.patch(`/bank-statements/transactions/${transactionId}/template-selection`, data)
  return res.data
}
