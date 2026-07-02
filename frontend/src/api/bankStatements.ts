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
