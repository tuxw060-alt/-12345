export const amountUnits = ['亿', '千', '百', '十', '万', '千', '百', '十', '元', '角', '分']

const upperDigits = ['零', '壹', '贰', '叁', '肆', '伍', '陆', '柒', '捌', '玖']
const integerUnits = ['', '拾', '佰', '仟']
const sectionUnits = ['', '万', '亿']

export function normalizeAmountInput(value: string | number | null | undefined) {
  const raw = String(value ?? '').replace(/,/g, '').trim()
  if (!raw) return 0
  const parsed = Number(raw)
  if (!Number.isFinite(parsed) || parsed <= 0) return 0
  return Math.round(parsed * 100) / 100
}

export function amountToDigits(value?: number) {
  const cents = Math.round(Math.abs(value || 0) * 100)
  if (!cents) return amountUnits.map(() => '')
  const raw = String(cents).padStart(amountUnits.length, '0').slice(-amountUnits.length)
  const first = raw.search(/[1-9]/)
  return raw.split('').map((char, index) => (index < first ? '' : char))
}

function sectionToChinese(section: number) {
  let text = ''
  let zero = false
  for (let i = 0; i < 4; i += 1) {
    const digit = section % 10
    if (digit === 0) {
      zero = text.length > 0
    } else {
      if (zero) text = `零${text}`
      text = `${upperDigits[digit]}${integerUnits[i]}${text}`
      zero = false
    }
    section = Math.floor(section / 10)
  }
  return text
}

export function amountToChineseUppercase(value: number) {
  const normalized = Math.round(Math.abs(value || 0) * 100) / 100
  const yuan = Math.floor(normalized)
  const jiao = Math.floor(Math.round(normalized * 100) / 10) % 10
  const fen = Math.round(normalized * 100) % 10

  if (yuan === 0 && jiao === 0 && fen === 0) return '零元整'

  let integerText = ''
  let sectionIndex = 0
  let integer = yuan
  let needsZero = false

  while (integer > 0) {
    const section = integer % 10000
    if (section === 0) {
      needsZero = integerText.length > 0
    } else {
      let sectionText = sectionToChinese(section)
      if (needsZero) sectionText = `零${sectionText}`
      integerText = `${sectionText}${sectionUnits[sectionIndex]}${integerText}`
      needsZero = section < 1000
    }
    integer = Math.floor(integer / 10000)
    sectionIndex += 1
  }

  const decimalText = `${jiao ? `${upperDigits[jiao]}角` : ''}${fen ? `${upperDigits[fen]}分` : ''}`
  return `${integerText || '零'}元${decimalText || '整'}`
}
