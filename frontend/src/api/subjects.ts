import api from './client'
import type { AccountSubject, SubjectTreeNode, MatchingRule, ListResponse } from '../types/invoice'

export interface SubjectImportResult {
  filename: string
  parent_code: string | null
  parent_name: string | null
  inserted: number
  updated: number
  skipped: number
  conflicts: {
    code: string
    name: string
    reason: string
    existing_code: string | null
    existing_name: string | null
  }[]
  warnings: string[]
}

export async function listSubjects(params?: {
  client_id?: string
  category?: string
  search?: string
  leaf_only?: boolean
  offset?: number
  limit?: number
}): Promise<ListResponse<AccountSubject>> {
  const res = await api.get<ListResponse<AccountSubject>>('/subjects', { params })
  return res.data
}

export async function getSubjectTree(clientId?: string): Promise<SubjectTreeNode[]> {
  const res = await api.get<SubjectTreeNode[]>('/subjects/tree', {
    params: clientId ? { client_id: clientId } : {},
  })
  return res.data
}

export async function getSubject(code: string): Promise<AccountSubject> {
  const res = await api.get<AccountSubject>(`/subjects/${code}`)
  return res.data
}

export async function createSubject(data: {
  client_id?: string | null
  code: string
  name: string
  full_name?: string | null
  level: number
  parent_code?: string | null
  parent_account_name?: string | null
  category: string
  direction: 'debit' | 'credit'
  is_leaf: boolean
  created_from?: string | null
}): Promise<AccountSubject> {
  const res = await api.post<AccountSubject>('/subjects', data)
  return res.data
}

export async function getNextSubAccountCode(parentCode: string, clientId?: string) {
  const res = await api.get<{ parent_code: string; next_code: string }>('/subjects/next-sub-code', {
    params: { parent_code: parentCode, ...(clientId ? { client_id: clientId } : {}) },
  })
  return res.data
}

export async function importLegacySubjects(file: File, clientId?: string): Promise<SubjectImportResult> {
  const form = new FormData()
  form.append('file', file)
  const res = await api.post<SubjectImportResult>('/subjects/import-legacy', form, {
    params: clientId ? { client_id: clientId } : {},
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return res.data
}

export async function listMatchingRules(params?: {
  client_id?: string
}): Promise<ListResponse<MatchingRule>> {
  const res = await api.get<ListResponse<MatchingRule>>('/matching-rules', { params })
  return res.data
}

export async function createMatchingRule(data: Partial<MatchingRule>): Promise<MatchingRule> {
  const res = await api.post<MatchingRule>('/matching-rules', data)
  return res.data
}

export async function deleteMatchingRule(id: string): Promise<void> {
  await api.delete(`/matching-rules/${id}`)
}

export async function testMatchingRule(text: string, clientId?: string) {
  const res = await api.post('/matching-rules/test', { text, client_id: clientId })
  return res.data
}
