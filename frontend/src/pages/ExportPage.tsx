import { useState } from 'react'
import {
  Card, Button, Space, Typography, Table, Tag, DatePicker, message, Alert,
} from 'antd'
import { ExportOutlined, DownloadOutlined } from '@ant-design/icons'
import { previewExport, exportKingdee } from '../api/entries'
import { useAppStore } from '../hooks/useAppStore'
import dayjs from 'dayjs'

export default function ExportPage() {
  const [preview, setPreview] = useState<any>(null)
  const [loading, setLoading] = useState(false)
  const [downloading, setDownloading] = useState(false)
  const [dateRange, setDateRange] = useState<[string, string] | null>(null)
  const { currentClient } = useAppStore()

  const handlePreview = async () => {
    if (!currentClient) {
      message.warning('请先在顶部选择要导出的客户')
      return
    }
    setLoading(true)
    try {
      const result = await previewExport({
        client_id: currentClient.id,
        date_from: dateRange?.[0],
        date_to: dateRange?.[1],
      })
      setPreview(result)
    } catch (err: any) {
      message.error(`预览失败: ${err.response?.data?.detail || err.message}`)
    } finally {
      setLoading(false)
    }
  }

  const handleExport = async () => {
    if (!currentClient) {
      message.warning('请先选择客户')
      return
    }
    setDownloading(true)
    try {
      const blob = await exportKingdee({
        client_id: currentClient.id,
        date_from: dateRange?.[0],
        date_to: dateRange?.[1],
      })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `kingdee_vouchers_${dayjs().format('YYYYMMDD_HHmmss')}.xlsx`
      a.click()
      URL.revokeObjectURL(url)
      message.success('导出成功！请在金蝶快记帐中导入该文件')
    } catch (err: any) {
      message.error(`导出失败: ${err.response?.data?.detail || err.message}`)
    } finally {
      setDownloading(false)
    }
  }

  return (
    <div>
      <Typography.Title level={4}>导出到金蝶快记帐</Typography.Title>

      <Alert
        type="info"
        showIcon
        message="导出说明"
        description={
          <div>
            <p>1. 导出的 Excel 文件可直接在金蝶快记帐中导入</p>
            <p>2. 导入路径：快记帐 → 查凭证 → 更多 → 导入凭证 → 选择导出的 Excel 文件</p>
            <p>3. 确保 Excel 中的科目代码与快记帐系统中的科目一致</p>
          </div>
        }
        style={{ marginBottom: 16 }}
      />

      <Card>
        <Space direction="vertical" style={{ width: '100%' }} size="large">
          <Space>
            <Typography.Text>导出日期范围（可选）:</Typography.Text>
            <DatePicker.RangePicker
              onChange={(dates) => {
                if (dates) {
                  setDateRange([
                    dates[0]!.format('YYYY-MM-DD'),
                    dates[1]!.format('YYYY-MM-DD'),
                  ])
                } else {
                  setDateRange(null)
                }
              }}
            />
          </Space>

          <Space>
            <Button
              type="primary"
              icon={<ExportOutlined />}
              onClick={handlePreview}
              loading={loading}
            >
              预览可导出的凭证
            </Button>
            <Button
              icon={<DownloadOutlined />}
              onClick={handleExport}
              loading={downloading}
              style={{ background: '#52c41a', borderColor: '#52c41a', color: '#fff' }}
            >
              直接导出全部已确认凭证
            </Button>
          </Space>
        </Space>
      </Card>

      {preview && (
        <Card title="预览结果" style={{ marginTop: 16 }}>
          <Space direction="vertical" style={{ width: '100%' }}>
            <Typography.Text>
              客户: <Tag color="blue">{preview.client_name}</Tag>
              {' | '}
              日期范围: <Tag color="green">{preview.date_range}</Tag>
              {' | '}
              共 <strong>{preview.entry_count}</strong> 张凭证,{' '}
              <strong>{preview.line_count}</strong> 行分录
            </Typography.Text>

            <Table
              columns={[
                { title: '日期', dataIndex: 'voucher_date', key: 'date', width: 110 },
                { title: '凭证字', dataIndex: 'voucher_type', key: 'type', width: 70 },
                { title: '凭证号', dataIndex: 'voucher_number', key: 'number', width: 80,
                  render: (v: string | null) => v || '待定' },
                { title: '摘要', dataIndex: 'summary', key: 'summary' },
                { title: '分录行数', dataIndex: 'line_count', key: 'lines', width: 80 },
              ]}
              dataSource={preview.entries}
              rowKey="id"
              size="small"
              pagination={{ pageSize: 20 }}
            />
          </Space>
        </Card>
      )}
    </div>
  )
}
