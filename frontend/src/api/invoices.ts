import api from './client'
import type { Invoice, ListResponse } from '../types/invoice'

export interface UploadResult {
  invoice: Invoice
  entry_id?: string
}

export async function uploadInvoice(
  file: File,
  clientId?: string,
  autoGenerate: boolean = false
): Promise<UploadResult> {
  const form = new FormData()
  form.append('file', file)
  const params: Record<string, string> = {}
  if (clientId) params.client_id = clientId
  if (autoGenerate) params.auto_generate = 'true'
  const res = await api.post<UploadResult>('/invoices/upload', form, { params })
  return res.data
}

/** Upload multiple files in parallel */
export async function batchUpload(
  files: File[],
  clientId?: string,
  autoGenerate: boolean = false
): Promise<UploadResult[]> {
  const results = await Promise.allSettled(
    files.map((file) => uploadInvoice(file, clientId, autoGenerate))
  )
  return results.map((r, i) => {
    if (r.status === 'fulfilled') return r.value
    return {
      invoice: {
        id: '',
        image_filename: files[i].name,
        ocr_status: 'failed',
        ocr_error_msg: r.reason?.message || '上传失败',
      } as any,
    }
  })
}

export async function listInvoices(params?: {
  client_id?: string
  status?: string
  date_from?: string
  date_to?: string
  offset?: number
  limit?: number
}): Promise<ListResponse<Invoice>> {
  const res = await api.get<ListResponse<Invoice>>('/invoices', { params })
  return res.data
}

export async function getInvoice(id: string): Promise<Invoice> {
  const res = await api.get<Invoice>(`/invoices/${id}`)
  return res.data
}

export async function updateInvoice(id: string, data: Partial<Invoice>): Promise<Invoice> {
  const res = await api.put<Invoice>(`/invoices/${id}`, data)
  return res.data
}

export async function deleteInvoice(id: string): Promise<void> {
  await api.delete(`/invoices/${id}`)
}
