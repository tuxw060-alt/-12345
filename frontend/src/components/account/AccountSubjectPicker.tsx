import { useEffect, useMemo, useState } from 'react'
import { Button, Form, Input, message, Modal, Select, Space, Tag, Tooltip } from 'antd'
import { PlusOutlined, ReloadOutlined } from '@ant-design/icons'
import { createSubject, getNextSubAccountCode } from '../../api/subjects'
import type { SubjectTreeNode } from '../../types/invoice'

export type AccountSelectionSource = 'auto' | 'manual' | 'rematch' | 'new_sub_account'

export interface AccountOption {
  value: string
  label: string
  name: string
  fullName: string
  parentCode: string | null
  parentName: string | null
  isLeaf: boolean
  direction: 'debit' | 'credit'
}

export interface AppliedAccount {
  account_code: string
  account_name: string
  account_full_name: string
  parent_account_code: string | null
  parent_account_name: string | null
  auxiliary_name: string | null
  auxiliary_code: string | null
  manual_account_override: boolean
  account_selection_source: AccountSelectionSource
}

const currentParentCodes = ['1122', '1123', '1221', '2202', '2203', '2241']
const parentOptions = [
  { value: '1122', label: '1122 应收账款', name: '应收账款', category: '资产', direction: 'debit' as const },
  { value: '1123', label: '1123 预付账款', name: '预付账款', category: '资产', direction: 'debit' as const },
  { value: '1221', label: '1221 其他应收款', name: '其他应收款', category: '资产', direction: 'debit' as const },
  { value: '2202', label: '2202 应付账款', name: '应付账款', category: '负债', direction: 'credit' as const },
  { value: '2203', label: '2203 预收账款', name: '预收账款', category: '负债', direction: 'credit' as const },
  { value: '2241', label: '2241 其他应付款', name: '其他应付款', category: '负债', direction: 'credit' as const },
]

function clean(value?: string | null) {
  return (value || '').replace(/\s+/g, '').trim()
}

export function flattenSubjectTree(nodes: SubjectTreeNode[]): AccountOption[] {
  let result: AccountOption[] = []
  for (const node of nodes) {
    const parentName = node.parent_account_name || null
    const fullName = node.full_name || (parentName ? `${parentName}_${node.name}` : node.name)
    result.push({
      value: node.code,
      label: `${node.code} ${fullName}`,
      name: node.name,
      fullName,
      parentCode: node.parent_code || null,
      parentName,
      isLeaf: node.is_leaf,
      direction: node.direction === 'credit' ? 'credit' : 'debit',
    })
    if (node.children?.length) result = result.concat(flattenSubjectTree(node.children))
  }
  return result
}

export function toAppliedAccount(option: AccountOption, source: AccountSelectionSource): AppliedAccount {
  return {
    account_code: option.value,
    account_name: option.name,
    account_full_name: option.fullName,
    parent_account_code: option.parentCode,
    parent_account_name: option.parentName,
    auxiliary_name: option.parentCode ? option.name : null,
    auxiliary_code: option.parentCode ? option.value : null,
    manual_account_override: source !== 'auto',
    account_selection_source: source,
  }
}

function findRematch(options: AccountOption[], party?: string | null) {
  const target = clean(party)
  if (!target) return null
  const currentOptions = options.filter((option) => option.isLeaf && option.parentCode && currentParentCodes.includes(option.parentCode))
  return currentOptions.find((option) => option.name === party)
    || currentOptions.find((option) => clean(option.name) === target)
    || null
}

interface Props {
  value?: string | null
  subjects: SubjectTreeNode[]
  clientId?: string
  counterpartyName?: string | null
  auxiliaryName?: string | null
  manualOverride?: boolean
  disabled?: boolean
  onApply: (account: AppliedAccount) => void | Promise<void>
  onCreated?: () => void
}

export default function AccountSubjectPicker({
  value,
  subjects,
  clientId,
  counterpartyName,
  auxiliaryName,
  manualOverride,
  disabled,
  onApply,
  onCreated,
}: Props) {
  const options = useMemo(() => flattenSubjectTree(subjects), [subjects])
  const [modalOpen, setModalOpen] = useState(false)
  const [saving, setSaving] = useState(false)
  const [form] = Form.useForm()

  useEffect(() => {
    if (modalOpen && clientId) {
      handleParentChange(form.getFieldValue('parent_code') || '2241')
    }
  }, [modalOpen, clientId])

  const applyOption = async (code: string, source: AccountSelectionSource) => {
    const option = options.find((item) => item.value === code)
    if (!option) return
    if (currentParentCodes.includes(option.value) || !option.isLeaf) {
      message.warning('请具体选择下级明细科目，不能直接选择父级往来科目。')
      return
    }
    await onApply(toAppliedAccount(option, source))
  }

  const handleRematch = async () => {
    const run = async () => {
      const option = findRematch(options, counterpartyName || auxiliaryName)
      if (!option) {
        message.warning('没有找到可匹配的老账套明细科目')
        return
      }
      await onApply(toAppliedAccount(option, 'rematch'))
      message.success(`已匹配 ${option.label}`)
    }
    if (manualOverride) {
      Modal.confirm({
        title: '覆盖人工选择?',
        content: '该行已手动选择科目，重新匹配会覆盖人工选择，是否继续？',
        onOk: run,
      })
    } else {
      await run()
    }
  }

  const handleParentChange = async (parentCode: string) => {
    if (!clientId) return
    const next = await getNextSubAccountCode(parentCode, clientId)
    form.setFieldsValue({ code: next.next_code })
  }

  const handleCreate = async () => {
    if (!clientId) {
      message.error('请先选择客户')
      return
    }
    const values = await form.validateFields()
    const parent = parentOptions.find((item) => item.value === values.parent_code)
    if (!parent) return
    setSaving(true)
    try {
      const fullName = `${parent.name}_${values.name}`
      await createSubject({
        client_id: clientId,
        code: values.code,
        name: values.name,
        full_name: fullName,
        level: 2,
        parent_code: parent.value,
        parent_account_name: parent.name,
        category: parent.category,
        direction: parent.direction,
        is_leaf: true,
        created_from: 'manual_new_sub_account',
      })
      const option: AccountOption = {
        value: values.code,
        label: `${values.code} ${fullName}`,
        name: values.name,
        fullName,
        parentCode: parent.value,
        parentName: parent.name,
        isLeaf: true,
        direction: parent.direction,
      }
      await onApply(toAppliedAccount(option, 'new_sub_account'))
      message.success(`已新增并使用 ${values.code} ${values.name}`)
      setModalOpen(false)
      form.resetFields()
      onCreated?.()
    } catch (err: any) {
      message.error(err.response?.data?.detail || `新增失败: ${err.message}`)
    } finally {
      setSaving(false)
    }
  }

  return (
    <Space.Compact style={{ width: '100%' }}>
      <Select
        showSearch
        value={value || undefined}
        placeholder="选择科目"
        disabled={disabled}
        style={{ width: '100%' }}
        optionLabelProp="label"
        onChange={(code) => applyOption(code, 'manual')}
        filterOption={(input, option) =>
          String(option?.label || '').includes(input)
          || String(option?.value || '').includes(input)
          || clean(String(option?.label || '')).includes(clean(input))
        }
        options={options.map((option) => ({
          value: option.value,
          label: option.label,
          disabled: currentParentCodes.includes(option.value) || !option.isLeaf,
        }))}
        optionRender={(option) => (
          <div style={{ lineHeight: 1.5 }}>
            <span>{option.label}</span>
          </div>
        )}
      />
      <Tooltip title="新增明细科目">
        <Button icon={<PlusOutlined />} disabled={disabled} onClick={() => setModalOpen(true)} />
      </Tooltip>
      <Tooltip title="重新匹配当前行">
        <Button icon={<ReloadOutlined />} disabled={disabled} onClick={handleRematch} />
      </Tooltip>
      <Modal
        title="新增明细科目"
        open={modalOpen}
        confirmLoading={saving}
        onOk={handleCreate}
        onCancel={() => setModalOpen(false)}
      >
        <Form form={form} layout="vertical" initialValues={{ parent_code: '2241', type: '个人' }}>
          <Form.Item name="parent_code" label="父级科目" rules={[{ required: true }]}>
            <Select options={parentOptions} onChange={handleParentChange} />
          </Form.Item>
          <Form.Item name="name" label="名称" rules={[{ required: true, message: '请输入名称' }]}>
            <Input placeholder="例如：李四" />
          </Form.Item>
          <Form.Item name="code" label="编码" rules={[{ required: true, message: '请输入编码' }]}>
            <Input placeholder="选择父级后自动生成，可手动修改" />
          </Form.Item>
          <Form.Item name="type" label="类型">
            <Select options={['客户', '供应商', '个人', '其他'].map((item) => ({ value: item, label: item }))} />
          </Form.Item>
        </Form>
      </Modal>
    </Space.Compact>
  )
}
