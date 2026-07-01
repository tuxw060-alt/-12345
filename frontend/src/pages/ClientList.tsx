import { useEffect, useState } from 'react'
import {
  Card, Table, Button, Space, Typography, Tag, Modal, Form,
  Input, Select, message, Popconfirm,
} from 'antd'
import { PlusOutlined, EditOutlined, DeleteOutlined } from '@ant-design/icons'
import { listClients, createClient, updateClient, deleteClient } from '../api/clients'
import { useAppStore } from '../hooks/useAppStore'
import type { Client } from '../types/invoice'

export default function ClientList() {
  const [clients, setClients] = useState<Client[]>([])
  const [loading, setLoading] = useState(true)
  const [modalOpen, setModalOpen] = useState(false)
  const [editing, setEditing] = useState<Client | null>(null)
  const [form] = Form.useForm()
  const { currentClient, setCurrentClient, requestClientRefresh } = useAppStore()

  const fetchClients = () => {
    setLoading(true)
    listClients().then((r) => setClients(r.items)).finally(() => setLoading(false))
  }

  useEffect(() => { fetchClients() }, [])

  const handleCreate = () => {
    setEditing(null)
    form.resetFields()
    setModalOpen(true)
  }

  const handleEdit = (client: Client) => {
    setEditing(client)
    form.setFieldsValue(client)
    setModalOpen(true)
  }

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields()
      if (editing) {
        await updateClient(editing.id, values)
        message.success('已更新客户信息')
      } else {
        await createClient(values)
        message.success('已添加客户')
      }
      setModalOpen(false)
      fetchClients()
      requestClientRefresh()
    } catch (err: any) {
      message.error(`操作失败: ${err.message}`)
    }
  }

  const handleDelete = async (id: string) => {
    try {
      await deleteClient(id)
      message.success('已停用客户')
      if (currentClient?.id === id) {
        setCurrentClient(null)
      }
      fetchClients()
      requestClientRefresh()
    } catch (err: any) {
      message.error(`删除失败: ${err.message}`)
    }
  }

  const columns = [
    { title: '企业名称', dataIndex: 'name', key: 'name' },
    { title: '税号', dataIndex: 'tax_id', key: 'tax_id', render: (v: string | null) => v || '-' },
    {
      title: '纳税人类型', dataIndex: 'tax_type', key: 'tax_type',
      render: (v: string) => (
        <Tag color={v === 'general' ? 'blue' : 'default'}>
          {v === 'general' ? '一般纳税人' : '小规模纳税人'}
        </Tag>
      ),
    },
    { title: '联系人', dataIndex: 'contact_person', key: 'contact', render: (v: string | null) => v || '-' },
    { title: '电话', dataIndex: 'phone', key: 'phone', render: (v: string | null) => v || '-' },
    {
      title: '状态', dataIndex: 'is_active', key: 'active',
      render: (v: boolean) => <Tag color={v ? 'green' : 'red'}>{v ? '正常' : '已停用'}</Tag>,
    },
    {
      title: '操作', key: 'action', width: 150,
      render: (_: any, r: Client) => (
        <Space>
          <Button type="link" size="small" icon={<EditOutlined />} onClick={() => handleEdit(r)}>
            编辑
          </Button>
          <Popconfirm title="确定停用此客户?" onConfirm={() => handleDelete(r.id)}>
            <Button type="link" size="small" danger icon={<DeleteOutlined />}>停用</Button>
          </Popconfirm>
        </Space>
      ),
    },
  ]

  return (
    <div>
      <Space style={{ marginBottom: 16, width: '100%', justifyContent: 'space-between' }}>
        <Typography.Title level={4} style={{ margin: 0 }}>客户管理</Typography.Title>
        <Button type="primary" icon={<PlusOutlined />} onClick={handleCreate}>
          添加客户
        </Button>
      </Space>

      <Card>
        <Table
          columns={columns}
          dataSource={clients}
          rowKey="id"
          loading={loading}
          size="small"
        />
      </Card>

      <Modal
        title={editing ? '编辑客户' : '添加客户'}
        open={modalOpen}
        onOk={handleSubmit}
        onCancel={() => setModalOpen(false)}
        okText="保存"
        cancelText="取消"
      >
        <Form form={form} layout="vertical">
          <Form.Item name="name" label="企业名称" rules={[{ required: true, message: '请输入企业名称' }]}>
            <Input placeholder="例如: 上海XX科技有限公司" />
          </Form.Item>
          <Form.Item name="tax_id" label="纳税人识别号">
            <Input placeholder="18位统一社会信用代码" />
          </Form.Item>
          <Form.Item name="tax_type" label="纳税人类型" initialValue="small">
            <Select
              options={[
                { value: 'small', label: '小规模纳税人' },
                { value: 'general', label: '一般纳税人' },
              ]}
            />
          </Form.Item>
          <Form.Item name="contact_person" label="联系人">
            <Input />
          </Form.Item>
          <Form.Item name="phone" label="电话">
            <Input />
          </Form.Item>
          <Form.Item name="notes" label="备注">
            <Input.TextArea rows={2} />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}
