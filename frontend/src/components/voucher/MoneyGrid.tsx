import { Input } from 'antd'
import { amountToDigits, normalizeAmountInput } from '../../utils/accountingAmount'

interface MoneyGridProps {
  amount?: number
  readonly?: boolean
  disabled?: boolean
  side?: 'debit' | 'credit'
  totalRow?: boolean
  onChange?: (amount: number) => void
}

export default function MoneyGrid({
  amount,
  readonly = false,
  disabled = false,
  side,
  totalRow = false,
  onChange,
}: MoneyGridProps) {
  const canEdit = !readonly && !disabled && Boolean(onChange)

  return (
    <div
      className={[
        'voucher-money-grid',
        side ? `voucher-money-grid-${side}` : '',
        totalRow ? 'voucher-money-grid-total' : '',
        canEdit ? 'voucher-money-grid-editable' : '',
      ].filter(Boolean).join(' ')}
    >
      {amountToDigits(amount).map((digit, index) => (
        <span key={`${index}-${digit}`}>{digit}</span>
      ))}
      {canEdit && (
        <Input
          className="voucher-money-input"
          value={amount ? amount.toFixed(2) : ''}
          inputMode="decimal"
          onChange={(event) => onChange?.(normalizeAmountInput(event.target.value))}
          onClick={(event) => event.stopPropagation()}
          placeholder="0.00"
        />
      )}
    </div>
  )
}
