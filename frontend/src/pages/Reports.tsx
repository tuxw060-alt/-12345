import { useState } from 'react'
import {
  Card, Table, Tabs, Typography, Button, Space, DatePicker, Tag, message,
} from 'antd'
import { DownloadOutlined, FileTextOutlined } from '@ant-design/icons'
import { useAppStore } from '../hooks/useAppStore'
import axios from 'axios'
import dayjs from 'dayjs'

export default function Reports() {
  const { currentClient } = useAppStore()
  const [dateRange, setDateRange] = useState<[string, string] | null>(null)
  const [trialBalance, setTrialBalance] = useState<any>(null)
  const [incomeStatement, setIncomeStatement] = useState<any>(null)
  const [loading, setLoading] = useState(false)

  const fetchReports = async () => {
    if (!currentClient) {
      message.warning('请先选择客户')
      return
    }
    setLoading(true)
    try {
      const params: any = { client_id: currentClient.id }
      if (dateRange) {
        params.date_from = dateRange[0]
        params.date_to = dateRange[1]
      }
      const [tb, inc] = await Promise.all([
        axios.get('/api/v1/reports/trial-balance', { params }),
        axios.get('/api/v1/reports/income-statement', { params }),
      ])
      setTrialBalance(tb.data)
      setIncomeStatement(inc.data)
    } catch (err: any) {
      message.error('加载报表失败: ' + (err.response?.data?.detail || err.message))
    } finally {
      setLoading(false)
    }
  }

  const downloadExcel = async (type: string) => {
    if (!currentClient) return
    const params: any = { client_id: currentClient.id }
    if (dateRange) {
      params.date_from = dateRange[0]
      params.date_to = dateRange[1]
    }
    try {
      const res = await axios.get(`/api/v1/reports/${type}/excel`, {
        params, responseType: 'blob',
      })
      const url = URL.createObjectURL(res.data)
      const a = document.createElement('a')
      a.href = url
      a.download = `${type === 'trial-balance' ? '科目余额表' : '利润表'}_${currentClient.name}_${dayjs().format('YYYYMMDD')}.xlsx`
      a.click()
      URL.revokeObjectURL(url)
      message.success('下载成功')
    } catch (err: any) {
      message.error('下载失败')
    }
  }

  const tbColumns = [
    { title: '科目代码', dataIndex: 'code', key: 'code', width: 120 },
    { title: '科目名称', dataIndex: 'name', key: 'name' },
    { title: '类别', dataIndex: 'category', key: 'cat', width: 60 },
    {
      title: '本期借方', dataIndex: 'current_debit', key: 'dr',
      render: (v: number) => v > 0 ? <span style={{ color: '#1677ff' }}>¥{v.toFixed(2)}</span> : '-',
    },
    {
      title: '本期贷方', dataIndex: 'current_credit', key: 'cr',
      render: (v: number) => v > 0 ? <span style={{ color: '#ff4d4f' }}>¥{v.toFixed(2)}</span> : '-',
    },
    {
      title: '期末借方', dataIndex: 'ending_debit', key: 'edr',
      render: (v: number) => v > 0 ? <b style={{ color: '#1677ff' }}>¥{v.toFixed(2)}</b> : '-',
    },
    {
      title: '期末贷方', dataIndex: 'ending_credit', key: 'ecr',
      render: (v: number) => v > 0 ? <b style={{ color: '#ff4d4f' }}>¥{v.toFixed(2)}</b> : '-',
    },
  ]

  const incColumns = [
    { title: '项目', dataIndex: 'name', key: 'name' },
    {
      title: '金额', dataIndex: 'amount', key: 'amount',
      render: (v: number | undefined) => v != null ? `¥${v.toFixed(2)}` : '-',
    },
  ]

  return (
    <div>
      <Typography.Title level={4}>财务报表</Typography.Title>

      <Card style={{ marginBottom: 16 }}>
        <Space>
          <Typography.Text strong>选择客户和期间:</Typography.Text>
          <DatePicker.RangePicker
            onChange={(dates) => {
              if (dates && dates[0] && dates[1]) {
                setDateRange([dates[0].format('YYYY-MM-DD'), dates[1].format('YYYY-MM-DD')])
              } else {
                setDateRange(null)
              }
            }}
          />
          <Button type="primary" icon={<FileTextOutlined />} onClick={fetchReports} loading={loading}>
            生成报表
          </Button>
        </Space>
      </Card>

      <Tabs defaultActiveKey="trial" items={[
        {
          key: 'trial',
          label: '科目余额表',
          children: trialBalance ? (
            <Card
              title={`科目余额表 — ${trialBalance.client_name} (${trialBalance.date_range})`}
              extra={
                <Button icon={<DownloadOutlined />} onClick={() => downloadExcel('trial-balance')}>
                  下载Excel
                </Button>
              }
            >
              <Table
                columns={tbColumns}
                dataSource={trialBalance.items}
                rowKey="code"
                size="small"
                pagination={false}
                scroll={{ y: 500 }}
                summary={() => (
                  <Table.Summary.Row>
                    <Table.Summary.Cell index={0} colSpan={3}><b>合计</b></Table.Summary.Cell>
                    <Table.Summary.Cell index={1}>
                      <b style={{ color: '#1677ff' }}>¥{trialBalance.totals.current_debit.toFixed(2)}</b>
                    </Table.Summary.Cell>
                    <Table.Summary.Cell index={2}>
                      <b style={{ color: '#ff4d4f' }}>¥{trialBalance.totals.current_credit.toFixed(2)}</b>
                    </Table.Summary.Cell>
                    <Table.Summary.Cell index={3}>
                      <b style={{ color: '#1677ff' }}>¥{trialBalance.totals.ending_debit.toFixed(2)}</b>
                    </Table.Summary.Cell>
                    <Table.Summary.Cell index={4}>
                      <b style={{ color: '#ff4d4f' }}>¥{trialBalance.totals.ending_credit.toFixed(2)}</b>
                    </Table.Summary.Cell>
                  </Table.Summary.Row>
                )}
              />
            </Card>
          ) : (
            <Card><Typography.Text type="secondary">请选择客户和期间，点击"生成报表"</Typography.Text></Card>
          ),
        },
        {
          key: 'income',
          label: '利润表',
          children: incomeStatement ? (
            <Card
              title={`利润表 — ${incomeStatement.client_name} (${incomeStatement.date_range})`}
              extra={
                <Button icon={<DownloadOutlined />} onClick={() => downloadExcel('income-statement')}>
                  下载Excel
                </Button>
              }
            >
              <div style={{ maxWidth: 600, margin: '0 auto' }}>
                {incomeStatement.revenue?.length > 0 && (
                  <>
                    <Typography.Title level={5}>一、营业收入</Typography.Title>
                    <Table columns={incColumns} dataSource={incomeStatement.revenue} rowKey="code" pagination={false} size="small" />
                    <Typography.Title level={5} style={{ textAlign: 'right' }}>
                      营业收入合计: ¥{incomeStatement.total_revenue.toFixed(2)}
                    </Typography.Title>
                  </>
                )}
                {incomeStatement.cost?.length > 0 && (
                  <>
                    <Typography.Title level={5}>二、营业成本</Typography.Title>
                    <Table columns={incColumns} dataSource={incomeStatement.cost} rowKey="code" pagination={false} size="small" />
                  </>
                )}
                <Typography.Title level={5} style={{ textAlign: 'right', color: incomeStatement.gross_profit >= 0 ? '#52c41a' : '#ff4d4f' }}>
                  毛利: ¥{incomeStatement.gross_profit.toFixed(2)}
                </Typography.Title>
                {incomeStatement.expense?.length > 0 && (
                  <>
                    <Typography.Title level={5}>三、期间费用</Typography.Title>
                    <Table columns={incColumns} dataSource={incomeStatement.expense} rowKey="code" pagination={false} size="small" />
                  </>
                )}
                <Typography.Title level={5} style={{ textAlign: 'right' }}>
                  费用合计: ¥{incomeStatement.total_expense.toFixed(2)}
                </Typography.Title>
                <Typography.Title level={4} style={{
                  textAlign: 'right',
                  color: incomeStatement.net_profit >= 0 ? '#52c41a' : '#ff4d4f',
                  borderTop: '2px solid #333',
                  paddingTop: 8,
                }}>
                  净利润: ¥{incomeStatement.net_profit.toFixed(2)}
                </Typography.Title>
              </div>
            </Card>
          ) : (
            <Card><Typography.Text type="secondary">请选择客户和期间，点击"生成报表"</Typography.Text></Card>
          ),
        },
      ]} />
    </div>
  )
}
