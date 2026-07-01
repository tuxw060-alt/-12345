import api from './client'
import type { AccountSubject, SubjectTreeNode, MatchingRule, ListResponse } from '../types/invoice'

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
