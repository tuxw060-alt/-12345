/** Axios client with base configuration. */

import axios from 'axios'

const api = axios.create({
  baseURL: '/api/v1',
  timeout: 120000,
})

// Request interceptor: attach JWT token
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// Response interceptor: handle errors and auth failures
api.interceptors.response.use(
  (res) => res,
  (error) => {
    if (error.response) {
      const detail = error.response.data?.detail
      if (error.response.status === 401) {
        localStorage.removeItem('token')
        window.location.reload()
        return Promise.reject(error)
      }
      if (Array.isArray(detail)) {
        const msgs = detail.map((d: any) => `${d.loc?.join('.')}: ${d.msg}`).join('; ')
        console.error(`Validation Error: ${msgs}`)
      } else {
        console.error(`API Error ${error.response.status}: ${detail || error.response.statusText}`)
      }
    } else if (error.request) {
      console.error('Network Error:', error.message)
    }
    return Promise.reject(error)
  }
)

export default api
