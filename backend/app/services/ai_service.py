"""
AI invoice extraction using DeepSeek.

Pipeline:
  1. Extract raw text from file (PDF → PyMuPDF, Image → Tesseract OCR)
  2. Send text to DeepSeek (text model) for structuring into JSON + subject matching
"""

import json
from pathlib import Path
from typing import Any

import fitz  # PyMuPDF
import pytesseract
from PIL import Image
from openai import AsyncOpenAI
from loguru import logger

from app.config import settings

# Load the system prompt
PROMPT_PATH = Path(__file__).resolve().parent.parent / "prompts" / "invoice_extraction.txt"
SYSTEM_PROMPT = PROMPT_PATH.read_text(encoding="utf-8") if PROMPT_PATH.exists() else ""
BANK_PROMPT_PATH = Path(__file__).resolve().parent.parent / "prompts" / "bank_statement_extraction.txt"
BANK_SYSTEM_PROMPT = BANK_PROMPT_PATH.read_text(encoding="utf-8") if BANK_PROMPT_PATH.exists() else ""


def pdf_to_image(pdf_path: Path, output_dir: Path | None = None, dpi: int = 200) -> Path:
    """Render first page of PDF to PNG for preview purposes."""
    pdf_path = Path(pdf_path)
    if output_dir is None:
        output_dir = pdf_path.parent

    png_name = pdf_path.stem + "_page1.png"
    png_path = output_dir / png_name

    doc = fitz.open(str(pdf_path))
    try:
        page = doc[0]
        zoom = dpi / 72
        mat = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat, colorspace=fitz.csRGB)
        pix.save(str(png_path))
        logger.info(f"PDF rendered to {png_path} ({pix.width}x{pix.height}px)")
    finally:
        doc.close()
    return png_path


def extract_text_from_pdf(pdf_path: Path) -> str:
    """Extract text from a PDF using PyMuPDF."""
    doc = fitz.open(str(pdf_path))
    try:
        text = ""
        for page in doc:
            text += page.get_text("text") + "\n"
        # Clean up whitespace
        text = "\n".join(line.strip() for line in text.splitlines() if line.strip())
        logger.info(f"Extracted {len(text)} chars from PDF")
        return text
    finally:
        doc.close()


def extract_text_from_image(image_path: Path) -> str:
    """Extract text from an image using Tesseract OCR (Chinese + English)."""
    img = Image.open(image_path)
    # Tesseract with Chinese simplified + English
    text = pytesseract.image_to_string(img, lang="chi_sim+eng")
    text = "\n".join(line.strip() for line in text.splitlines() if line.strip())
    logger.info(f"OCR extracted {len(text)} chars from image")
    return text


def extract_text(file_path: Path) -> str:
    """Extract text from a file — PDF or image."""
    suffix = file_path.suffix.lower()
    if suffix == ".pdf":
        return extract_text_from_pdf(file_path)
    else:
        return extract_text_from_image(file_path)


class AIService:
    """Service for AI-powered invoice extraction using DeepSeek (text model)."""

    def __init__(self):
        self.client = AsyncOpenAI(
            api_key=settings.deepseek_api_key,
            base_url=settings.deepseek_base_url + "/v1",
        )
        # Use the text-only model — proven to work
        self.model = "deepseek-chat"

    async def extract_invoice(
        self,
        file_path: str | Path,
        client_tax_type: str = "small",
    ) -> dict[str, Any]:
        """
        Extract invoice fields from a file (PDF or image).

        1. Extract raw text via OCR / PDF parser
        2. Send text to DeepSeek for structuring into JSON

        Args:
            file_path: Path to the invoice file.
            client_tax_type: 'general' or 'small'.

        Returns:
            Parsed JSON dict with invoice fields and AI suggestions.
        """
        file_path = Path(file_path)

        # Step 1: Extract raw text
        logger.info(f"Extracting text from: {file_path.name}")
        try:
            raw_text = extract_text(file_path)
        except Exception as e:
            logger.error(f"Text extraction failed: {e}")
            return self._error_result(f"文字提取失败: {e}")

        if not raw_text or len(raw_text) < 10:
            logger.warning("Extracted text is empty or too short")
            return self._error_result("未能从文件中提取到足够文字，请确保图片清晰或PDF包含文字层")

        # Step 2: Send to DeepSeek for structuring
        user_prompt = (
            f"请从以下OCR提取的发票文字中，提取关键字段信息。\n\n"
            f"客户纳税人类型: {'一般纳税人' if client_tax_type == 'general' else '小规模纳税人'}\n\n"
            f"=== OCR提取的文字 ===\n{raw_text}\n=== 文字结束 ==="
        )

        try:
            logger.info(f"Sending {len(raw_text)} chars to DeepSeek...")
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                max_tokens=2048,
                temperature=0.1,
            )

            result_text = response.choices[0].message.content or ""
            logger.info(f"DeepSeek response: {len(result_text)} chars")
            result = self._parse_response(result_text)
            return result

        except Exception as e:
            logger.error(f"DeepSeek API error: {e}")
            return self._error_result(f"AI识别失败: {e}")

    def _parse_response(self, raw_text: str) -> dict[str, Any]:
        """Extract JSON from the AI response."""
        text = raw_text.strip()

        if "```json" in text:
            start = text.index("```json") + 7
            end = text.index("```", start) if "```" in text[start:] else len(text)
            text = text[start:end].strip()
        elif "```" in text:
            start = text.index("```") + 3
            end = text.index("```", start) if "```" in text[start:] else len(text)
            text = text[start:end].strip()

        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            import re
            match = re.search(r'\{[\s\S]*\}', text)
            if match:
                try:
                    data = json.loads(match.group())
                except json.JSONDecodeError:
                    logger.warning(f"Failed to parse as JSON: {text[:200]}...")
                    data = {}
            else:
                logger.warning(f"No JSON found: {text[:200]}...")
                data = {}

        return {
            "invoice_direction": data.get("invoice_direction", "expense"),
            "invoice_type": data.get("invoice_type"),
            "invoice_code": data.get("invoice_code"),
            "invoice_number": data.get("invoice_number"),
            "invoice_date": data.get("invoice_date"),
            "total_amount": self._to_float(data.get("total_amount")),
            "amount": self._to_float(data.get("amount")),
            "tax_amount": self._to_float(data.get("tax_amount")),
            "vendor_name": data.get("vendor_name"),
            "vendor_tax_id": data.get("vendor_tax_id"),
            "buyer_name": data.get("buyer_name"),
            "buyer_tax_id": data.get("buyer_tax_id"),
            "item_name": data.get("item_name"),
            "remarks": data.get("remarks"),
            "suggested_subject_code": data.get("suggested_subject_code"),
            "suggested_subject_name": data.get("suggested_subject_name"),
            "subject_reason": data.get("subject_reason"),
            "is_deductible": data.get("is_deductible", False),
            "confidence": data.get("confidence", {}),
            "warnings": data.get("warnings", []),
            "raw_text": raw_text,
        }

    def _error_result(self, msg: str) -> dict[str, Any]:
        return {
            "error": msg,
            "invoice_direction": "expense",
            "invoice_type": None, "invoice_code": None, "invoice_number": None,
            "invoice_date": None, "total_amount": None, "amount": None,
            "tax_amount": None, "vendor_name": None, "vendor_tax_id": None,
            "buyer_name": None, "buyer_tax_id": None, "item_name": None,
            "remarks": None, "suggested_subject_code": None,
            "suggested_subject_name": None, "subject_reason": None,
            "is_deductible": False, "confidence": {}, "warnings": [],
        }

    async def extract_bank_statement(self, statement_text: str) -> dict[str, Any]:
        """Extract bank statement transactions and subject suggestions."""
        if not statement_text or len(statement_text.strip()) < 10:
            return {"error": "流水内容为空或文本过短，无法识别"}

        user_prompt = (
            "请从以下银行流水内容中提取交易明细，并推荐会计科目。\n\n"
            f"=== 银行流水内容 ===\n{statement_text[:24000]}\n=== 内容结束 ==="
        )

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": BANK_SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                max_tokens=4096,
                temperature=0.1,
            )
            result_text = response.choices[0].message.content or ""
            data = self._parse_json_object(result_text)
            transactions = data.get("transactions")
            if not isinstance(transactions, list):
                return {"error": "AI未返回有效的流水明细", "raw": data}
            return data
        except Exception as e:
            logger.error(f"Bank statement AI extraction failed: {e}")
            return {"error": f"银行流水AI识别失败: {e}"}

    def _parse_json_object(self, raw_text: str) -> dict[str, Any]:
        """Extract a JSON object from an AI response."""
        text = raw_text.strip()
        if "```json" in text:
            start = text.index("```json") + 7
            end = text.index("```", start) if "```" in text[start:] else len(text)
            text = text[start:end].strip()
        elif "```" in text:
            start = text.index("```") + 3
            end = text.index("```", start) if "```" in text[start:] else len(text)
            text = text[start:end].strip()

        try:
            return json.loads(text)
        except json.JSONDecodeError:
            import re
            match = re.search(r"\{[\s\S]*\}", text)
            if match:
                try:
                    return json.loads(match.group())
                except json.JSONDecodeError:
                    pass
        return {}

    @staticmethod
    def _to_float(value: Any) -> float | None:
        if value is None:
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            import re
            if isinstance(value, str):
                cleaned = re.sub(r'[^\d.\-]', '', value)
                try:
                    return float(cleaned) if cleaned else None
                except ValueError:
                    pass
            return None


# Singleton
ai_service = AIService()
