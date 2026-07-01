import api from './client'
import type { Client, ListResponse } from '../types/invoice'

export async function listClients(params?: {
  is_active?: boolean
  search?: string
}): Promise<ListResponse<Client>> {
  const res = await api.get<ListResponse<Client>>('/clients', { params })
  return res.data
}

export async function getClient(id: string): Promise<Client> {
  const res = await api.get<Client>(`/clients/${id}`)
  return res.data
}

export async function createClient(data: Partial<Client>): Promise<Client> {
  const res = await api.post<Client>('/clients', data)
  return res.data
}

export async function updateClient(id: string, data: Partial<Client>): Promise<Client> {
  const res = await api.put<Client>(`/clients/${id}`, data)
  return res.data
}

export async function deleteClient(id: string): Promise<void> {
  await api.delete(`/clients/${id}`)
}
