export type BankStatementFileType = 'excel' | 'csv' | 'pdf' | 'image' | 'unknown'

export type BankStatementProcessingMode =
  | 'excel_parser'
  | 'csv_parser'
  | 'pdf_text_parser'
  | 'pdf_ocr'
  | 'image_ocr'
  | 'unsupported'

export interface BankStatementProcessingInfo {
  fileType: BankStatementFileType
  processingMode: BankStatementProcessingMode
  useOcr: boolean
  useAi: boolean
  displayText: string
  description: string
}

export function detectBankStatementProcessingMode(file: File | string): BankStatementProcessingInfo {
  const filename = typeof file === 'string' ? file : file.name
  const ext = filename.split('.').pop()?.toLowerCase() || ''

  if (['xls', 'xlsx', 'xlsm', 'ods'].includes(ext)) {
    return {
      fileType: 'excel',
      processingMode: 'excel_parser',
      useOcr: false,
      useAi: false,
      displayText: '正在解析 Excel 流水',
      description: 'Excel 流水优先使用表格解析，不走 OCR。',
    }
  }

  if (ext === 'csv') {
    return {
      fileType: 'csv',
      processingMode: 'csv_parser',
      useOcr: false,
      useAi: false,
      displayText: '正在解析 CSV 流水',
      description: 'CSV 流水优先使用表格解析，不走 OCR。',
    }
  }

  if (ext === 'pdf') {
    return {
      fileType: 'pdf',
      processingMode: 'pdf_text_parser',
      useOcr: false,
      useAi: false,
      displayText: '正在解析 PDF 文本流水',
      description: '优先抽取 PDF 文本和表格，失败后再 OCR。',
    }
  }

  if (['jpg', 'jpeg', 'png', 'webp', 'bmp'].includes(ext)) {
    return {
      fileType: 'image',
      processingMode: 'image_ocr',
      useOcr: true,
      useAi: true,
      displayText: '正在 OCR 识别图片流水',
      description: '图片流水使用 OCR + AI 字段整理。',
    }
  }

  return {
    fileType: 'unknown',
    processingMode: 'unsupported',
    useOcr: false,
    useAi: false,
    displayText: '不支持的文件类型',
    description: '请上传 xls、xlsx、csv、pdf、jpg、jpeg、png、webp 文件。',
  }
}

