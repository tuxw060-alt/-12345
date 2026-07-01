import { useState } from 'react'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { ConfigProvider } from 'antd'
import zhCN from 'antd/locale/zh_CN'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import Login from './pages/Login'
import AppLayout from './components/Layout/AppLayout'
import Dashboard from './pages/Dashboard'
import InvoiceUpload from './pages/InvoiceUpload'
import InvoiceReview from './pages/InvoiceReview'
import EntryList from './pages/EntryList'
import EntryEditor from './pages/EntryEditor'
import ClientList from './pages/ClientList'
import SubjectManager from './pages/SubjectManager'
import ExportPage from './pages/ExportPage'
import Reports from './pages/Reports'
import BankImport from './pages/BankImport'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: { refetchOnWindowFocus: false, retry: 1 },
  },
})

export default function App() {
  const [token, setToken] = useState<string | null>(localStorage.getItem('token'))

  if (!token) {
    return (
      <ConfigProvider locale={zhCN}>
        <Login onLogin={setToken} />
      </ConfigProvider>
    )
  }

  return (
    <QueryClientProvider client={queryClient}>
      <ConfigProvider
        locale={zhCN}
        theme={{
          token: {
            colorPrimary: '#1677ff',
            borderRadius: 6,
            fontFamily: `-apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC',
              'Hiragino Sans GB', 'Microsoft YaHei', sans-serif`,
          },
        }}
      >
        <BrowserRouter>
          <Routes>
            <Route element={<AppLayout />}>
              <Route index element={<Dashboard />} />
              <Route path="invoices/upload" element={<InvoiceUpload />} />
              <Route path="invoices/:id/review" element={<InvoiceReview />} />
              <Route path="entries" element={<EntryList />} />
              <Route path="entries/:id/edit" element={<EntryEditor />} />
              <Route path="clients" element={<ClientList />} />
              <Route path="subjects" element={<SubjectManager />} />
              <Route path="export" element={<ExportPage />} />
              <Route path="reports" element={<Reports />} />
              <Route path="bank" element={<BankImport />} />
            </Route>
          </Routes>
        </BrowserRouter>
      </ConfigProvider>
    </QueryClientProvider>
  )
}
