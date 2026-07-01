import { useEffect, useMemo, useState } from 'react'
import { Button, Card, Col, Empty, Popconfirm, Progress, Row, Space, Table, Tag, Typography, message } from 'antd'
import {
  ArrowRightOutlined,
  BankOutlined,
  CheckCircleOutlined,
  ClockCircleOutlined,
  DeleteOutlined,
  ExportOutlined,
  FileSearchOutlined,
  FileTextOutlined,
  RiseOutlined,
  SafetyCertificateOutlined,
  UploadOutlined,
} from '@ant-design/icons'
import axios from 'axios'
import dayjs from 'dayjs'
import { useNavigate } from 'react-router-dom'
import { deleteInvoice, listInvoices } from '../api/invoices'
import { listEntries } from '../api/entries'
import { useAppStore } from '../hooks/useAppStore'
import type { Invoice, JournalEntry } from '../types/invoice'

const currency = (value?: number | null) => (value ? `¥${value.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}` : '-')

export default function Dashboard() {
  const [invoices, setInvoices] = useState<Invoice[]>([])
  const [entries, setEntries] = useState<JournalEntry[]>([])
  const [taxData, setTaxData] = useState<any>(null)
  const [monthlyData, setMonthlyData] = useState<any[]>([])
  const { currentClient } = useAppStore()
  const navigate = useNavigate()

  const fetchData = () => {
    listInvoices({ limit: 10 }).then((res) => setInvoices(res.items))
    listEntries({ limit: 100 }).then((res) => setEntries(res.items))

    if (!currentClient) {
      setTaxData(null)
      setMonthlyData([])
      return
    }

    const now = dayjs()
    axios
      .get('/api/v1/tax/summary', {
        params: {
          client_id: currentClient.id,
          date_from: now.startOf('month').format('YYYY-MM-DD'),
          date_to: now.endOf('month').format('YYYY-MM-DD'),
        },
      })
      .then((res) => setTaxData(res.data))
      .catch(() => setTaxData(null))

    const months = Array.from({ length: 6 }, (_, index) => {
      const month = now.subtract(5 - index, 'month')
      return { label: month.format('M月'), month: month.format('YYYY-MM') }
    })

    Promise.all(
      months.map(async (month) => {
        try {
          const res = await axios.get('/api/v1/tax/summary', {
            params: {
              client_id: currentClient.id,
              date_from: `${month.month}-01`,
              date_to: dayjs(`${month.month}-01`).endOf('month').format('YYYY-MM-DD'),
            },
          })
          return {
            label: month.label,
            revenue: res.data.income_tax?.revenue || 0,
            expense: res.data.income_tax?.expense || 0,
          }
        } catch {
          return { label: month.label, revenue: 0, expense: 0 }
        }
      }),
    ).then(setMonthlyData)
  }

  useEffect(() => {
    fetchData()
  }, [currentClient])

  const pendingInvoices = invoices.filter((invoice) => invoice.ocr_status === 'pending' || !invoice.human_verified).length
  const draftEntries = entries.filter((entry) => entry.status === 'draft').length
  const confirmedEntries = entries.filter((entry) => entry.status === 'confirmed').length
  const thisMonthEntries = entries.filter((entry) => dayjs(entry.voucher_date).isSame(dayjs(), 'month')).length
  const totalInvoiceAmount = invoices.reduce((sum, invoice) => sum + (invoice.total_amount || 0), 0)

  const maxTrendValue = useMemo(
    () => Math.max(...monthlyData.map((item) => Math.max(item.revenue, item.expense)), 1),
    [monthlyData],
  )

  const handleDeleteInvoice = async (id: string, name: string) => {
    await deleteInvoice(id)
    setInvoices((prev) => prev.filter((invoice) => invoice.id !== id))
    message.success(`已删除 ${name}`)
  }

  const invoiceColumns = [
    {
      title: '文件',
      dataIndex: 'image_filename',
      key: 'file',
      ellipsis: true,
      render: (text: string, record: Invoice) => (
        <Button type="link" className="table-link" onClick={() => navigate(`/invoices/${record.id}/review`)}>
          {text}
        </Button>
      ),
    },
    {
      title: '状态',
      dataIndex: 'ocr_status',
      key: 'status',
      width: 110,
      render: (status: string) => (
        <Tag color={status === 'done' ? 'green' : status === 'failed' ? 'red' : 'processing'}>
          {status === 'done' ? '已识别' : status === 'failed' ? '失败' : '处理中'}
        </Tag>
      ),
    },
    {
      title: '金额',
      dataIndex: 'total_amount',
      key: 'amount',
      width: 140,
      render: (value: number | null) => <strong>{currency(value)}</strong>,
    },
    {
      title: '日期',
      dataIndex: 'created_at',
      key: 'date',
      width: 130,
      render: (value: string) => dayjs(value).format('MM-DD HH:mm'),
    },
    {
      title: '',
      key: 'action',
      width: 56,
      render: (_: unknown, record: Invoice) => (
        <Popconfirm title="删除这张发票？" onConfirm={() => handleDeleteInvoice(record.id, record.image_filename)}>
          <Button type="text" danger icon={<DeleteOutlined />} />
        </Popconfirm>
      ),
    },
  ]

  return (
    <div className="dashboard-page">
      <section className="dashboard-hero">
        <div>
          <p className="dashboard-eyebrow">今日工作台</p>
          <h1>{currentClient ? currentClient.name : '选择客户后开始处理票据与凭证'}</h1>
          <p>
            把上传、识别、复核、确认和导出放在同一条工作流里。需要处理的票据、草稿凭证和税务风险会优先浮到前面。
          </p>
          <Space wrap>
            <Button type="primary" size="large" icon={<UploadOutlined />} onClick={() => navigate('/invoices/upload')}>
              上传发票
            </Button>
            <Button size="large" icon={<FileTextOutlined />} onClick={() => navigate('/entries')}>
              查看凭证
            </Button>
            <Button size="large" icon={<ExportOutlined />} onClick={() => navigate('/export')}>
              金蝶导出
            </Button>
          </Space>
        </div>
        <div className="hero-status-card">
          <SafetyCertificateOutlined />
          <span>本月应缴税额</span>
          <strong>{taxData ? currency(taxData.total_tax_liability) : '选择客户查看'}</strong>
          <Progress percent={confirmedEntries + draftEntries ? Math.round((confirmedEntries / (confirmedEntries + draftEntries)) * 100) : 0} showInfo={false} strokeColor="#126b56" />
          <small>凭证确认进度</small>
        </div>
      </section>

      <Row gutter={[16, 16]} className="metric-row">
        <Col xs={24} sm={12} xl={6}>
          <Card className="metric-card warning" onClick={() => navigate('/invoices/upload')}>
            <FileSearchOutlined />
            <span>待处理发票</span>
            <strong>{pendingInvoices}</strong>
            <small>点击继续上传或复核</small>
          </Card>
        </Col>
        <Col xs={24} sm={12} xl={6}>
          <Card className="metric-card blue" onClick={() => navigate('/entries')}>
            <FileTextOutlined />
            <span>草稿凭证</span>
            <strong>{draftEntries}</strong>
            <small>需要确认后才能导出</small>
          </Card>
        </Col>
        <Col xs={24} sm={12} xl={6}>
          <Card className="metric-card green">
            <CheckCircleOutlined />
            <span>已确认凭证</span>
            <strong>{confirmedEntries}</strong>
            <small>可进入导出队列</small>
          </Card>
        </Col>
        <Col xs={24} sm={12} xl={6}>
          <Card className="metric-card dark">
            <ClockCircleOutlined />
            <span>本月凭证</span>
            <strong>{thisMonthEntries}</strong>
            <small>最近发票金额 {currency(totalInvoiceAmount)}</small>
          </Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]} className="dashboard-main-grid">
        <Col xs={24} xl={15}>
          <Card
            className="panel-card trend-card"
            title="近 6 月收入 / 支出趋势"
            extra={<Tag color="green">{currentClient ? '客户数据' : '待选择客户'}</Tag>}
          >
            {monthlyData.length ? (
              <div className="trend-chart">
                {monthlyData.map((month) => (
                  <div className="trend-month" key={month.label}>
                    <div className="trend-bars">
                      <span className="income" style={{ height: `${Math.max((month.revenue / maxTrendValue) * 160, 4)}px` }} title={`收入 ${currency(month.revenue)}`} />
                      <span className="expense" style={{ height: `${Math.max((month.expense / maxTrendValue) * 160, 4)}px` }} title={`支出 ${currency(month.expense)}`} />
                    </div>
                    <strong>{month.label}</strong>
                  </div>
                ))}
              </div>
            ) : (
              <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="选择客户后显示趋势图" />
            )}
            <Space className="chart-legend">
              <Tag color="green">收入</Tag>
              <Tag color="red">支出</Tag>
            </Space>
          </Card>
        </Col>
        <Col xs={24} xl={9}>
          <Card className="panel-card tax-card" title={<span><BankOutlined /> 本月税务概览</span>}>
            {taxData ? (
              <div className="tax-list">
                <div>
                  <span>增值税</span>
                  <strong>{currency(taxData.vat.payable)}</strong>
                  <small>销项 {currency(taxData.vat.output_vat)} / 进项 {currency(taxData.vat.input_vat)}</small>
                </div>
                <div>
                  <span>附加税</span>
                  <strong>{currency(taxData.surcharges.total)}</strong>
                  <small>城建、教育及地方教育附加</small>
                </div>
                <div>
                  <span>企业所得税预估</span>
                  <strong>{currency(taxData.income_tax.estimated_tax)}</strong>
                  <small>利润 {currency(taxData.income_tax.profit)}</small>
                </div>
                <div className="tax-total">
                  <span>合计应缴</span>
                  <strong>{currency(taxData.total_tax_liability)}</strong>
                </div>
              </div>
            ) : (
              <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="选择客户查看税务概览" />
            )}
          </Card>
        </Col>
      </Row>

      <Card
        className="panel-card invoice-table-card"
        title="最近上传的发票"
        extra={
          <Button type="link" icon={<ArrowRightOutlined />} onClick={() => navigate('/invoices/upload')}>
            上传更多
          </Button>
        }
      >
        <Table
          columns={invoiceColumns}
          dataSource={invoices}
          rowKey="id"
          pagination={false}
          size="middle"
          locale={{ emptyText: '暂无发票，点击上传发票开始处理' }}
          scroll={{ x: 760 }}
        />
      </Card>
    </div>
  )
}
