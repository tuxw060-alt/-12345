import { useCallback, useEffect, useState } from 'react'
import { Outlet, useLocation, useNavigate } from 'react-router-dom'
import { Avatar, Button, Grid, Layout, Menu, Select, Space, Typography, message, theme } from 'antd'
import {
  AppstoreOutlined,
  AuditOutlined,
  BankOutlined,
  BarChartOutlined,
  BookOutlined,
  ExportOutlined,
  FileTextOutlined,
  LogoutOutlined,
  TeamOutlined,
  UploadOutlined,
  ToolOutlined,
} from '@ant-design/icons'
import { listClients } from '../../api/clients'
import { useAppStore } from '../../hooks/useAppStore'
import type { Client } from '../../types/invoice'

const { Header, Sider, Content } = Layout

const menuItems = [
  { key: '/', icon: <AppstoreOutlined />, label: '工作台' },
  { key: '/invoices/upload', icon: <UploadOutlined />, label: '上传发票' },
  { key: '/bank-statements/upload', icon: <BankOutlined />, label: '银行流水' },
  { key: '/entries', icon: <FileTextOutlined />, label: '记账凭证' },
  { key: '/subjects', icon: <BookOutlined />, label: '科目规则' },
  { key: '/voucher-settings', icon: <ToolOutlined />, label: '票据设置' },
  { key: '/clients', icon: <TeamOutlined />, label: '客户管理' },
  { key: '/export', icon: <ExportOutlined />, label: '金蝶导出' },
  { key: '/reports', icon: <BarChartOutlined />, label: '财务报表' },
]

const savedClientKey = 'currentClientId'

function getSelectedMenuKey(pathname: string) {
  if (pathname === '/') return '/'
  if (pathname.startsWith('/invoices')) return '/invoices/upload'
  if (pathname.startsWith('/bank-statements')) return '/bank-statements/upload'
  if (pathname.startsWith('/entries')) return '/entries'
  if (pathname.startsWith('/subjects')) return '/subjects'
  if (pathname.startsWith('/voucher-settings')) return '/voucher-settings'
  if (pathname.startsWith('/clients')) return '/clients'
  if (pathname.startsWith('/export')) return '/export'
  if (pathname.startsWith('/reports')) return '/reports'
  return '/'
}

export default function AppLayout() {
  const [collapsed, setCollapsed] = useState(false)
  const [clients, setClients] = useState<Client[]>([])
  const { currentClient, setCurrentClient, clientRefreshKey } = useAppStore()
  const navigate = useNavigate()
  const location = useLocation()
  const { token } = theme.useToken()
  const screens = Grid.useBreakpoint()
  const isMobile = !screens.md

  const refreshClientOptions = useCallback(() => {
    listClients({ is_active: true })
      .then((res) => {
        setClients(res.items)
        const savedClientId = localStorage.getItem(savedClientKey)
        const savedClient = savedClientId
          ? res.items.find((client) => client.id === savedClientId)
          : null

        if (currentClient && !res.items.some((client) => client.id === currentClient.id)) {
          setCurrentClient(savedClient || null)
          if (!savedClient) localStorage.removeItem(savedClientKey)
          return
        }

        if (!currentClient && savedClient) {
          setCurrentClient(savedClient)
        }
      })
      .catch(() => {
        message.error('客户列表加载失败，请稍后重试')
      })
  }, [currentClient, setCurrentClient])

  useEffect(() => {
    refreshClientOptions()
  }, [clientRefreshKey, refreshClientOptions])

  const selectedKey = getSelectedMenuKey(location.pathname)
  const currentMenu = menuItems.find((m) => m.key === selectedKey) || menuItems[0]
  const currentClientLabel = currentClient
    ? `${currentClient.name}${currentClient.tax_type === 'general' ? '（一般纳税人）' : '（小规模）'}`
    : undefined

  const handleClientChange = (val?: string) => {
    const client = clients.find((x) => x.id === val) || null
    setCurrentClient(client)
    if (client) {
      localStorage.setItem(savedClientKey, client.id)
    } else {
      localStorage.removeItem(savedClientKey)
    }
  }

  const handleLogout = () => {
    localStorage.removeItem('token')
    window.location.reload()
  }

  return (
    <Layout className="app-shell">
      <Sider
        className="app-sider"
        collapsible
        breakpoint="md"
        collapsedWidth={isMobile ? 0 : 88}
        width={236}
        collapsed={collapsed}
        onCollapse={setCollapsed}
        onBreakpoint={(broken) => setCollapsed(broken)}
      >
        <div className="app-brand">
          <span className="app-brand-mark">快</span>
          {!collapsed && (
            <span>
              <strong>快记帐</strong>
              <small>AI Accounting Copilot</small>
            </span>
          )}
        </div>
        <Menu
          className="app-menu"
          mode="inline"
          selectedKeys={[selectedKey]}
          items={menuItems}
          onClick={({ key }) => navigate(key)}
        />
        {!collapsed && (
          <div className="sider-note">
            <AuditOutlined />
            <span>发票识别、凭证复核、金蝶导出，一条流程闭环。</span>
          </div>
        )}
      </Sider>

      <Layout>
        <Header className="app-header">
          <Space size={12}>
            <Avatar className="page-avatar" icon={currentMenu.icon} />
            <div>
              <Typography.Text strong className="page-title">
                {currentMenu.label}
              </Typography.Text>
              <Typography.Text className="page-subtitle">
                代理记账 AI 工作台
              </Typography.Text>
            </div>
          </Space>
          <Space className="client-picker" size={10}>
            <Typography.Text type="secondary">当前客户</Typography.Text>
            <Select
              allowClear
              showSearch
              optionFilterProp="label"
              placeholder="选择客户"
              style={{ width: isMobile ? 190 : 280 }}
              value={currentClient?.id || undefined}
              title={currentClientLabel}
              onOpenChange={(open) => {
                if (open) refreshClientOptions()
              }}
              onChange={handleClientChange}
              options={clients.map((client) => ({
                value: client.id,
                label: `${client.name}${client.tax_type === 'general' ? '（一般纳税人）' : '（小规模）'}`,
              }))}
              suffixIcon={<BankOutlined />}
            />
            <Button type="text" icon={<LogoutOutlined />} onClick={handleLogout}>
              退出
            </Button>
          </Space>
        </Header>
        <Content
          className="app-content"
          style={{
            background: token.colorBgLayout,
            minHeight: 'calc(100vh - 72px)',
          }}
        >
          <Outlet />
        </Content>
      </Layout>
    </Layout>
  )
}
