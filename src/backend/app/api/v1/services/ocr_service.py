from io import BytesIO
from pathlib import Path
from typing import Union

import fitz
import pytesseract
from PIL import Image


class OcrService:
    def __init__(self, ocr_engine: str = "tesseract", language: str = "eng"):
        self.ocr_engine = ocr_engine
        self.language = language

    """
    Extract text from a PDF file
    """

    def extract_text_from_pdf(self, file_path: Path) -> str:
        doc = fitz.open(file_path)
        extracted_text = []

        for page in doc:
            text = page.get_text("text")
            if not text.strip():
                # Perform OCR on the page
                pix = page.get_pixmap()
                image = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                text = pytesseract.image_to_string(image, lang=self.language)

            extracted_text.append(text.strip())

        return "\n".join(extracted_text)

    """
    Extract text from an image file
    """

    def extract_text_from_image(self, image_bytes: bytes) -> str:
        image = Image.open(BytesIO(image_bytes)).convert("RGB")
        text = pytesseract.image_to_string(image, lang=self.language)
        return text.strip()

    """
    Extract text from a file
    """

    def extract_text(self, file_path: Union[Path, str]) -> str:
        file_path = Path(file_path)

        if file_path.suffix.lower() in [".png", ".jpg", ".jpeg"]:
            with open(file_path, "rb") as f:
                return self.extract_text_from_image(f.read())
        elif file_path.suffix.lower() == ".pdf":
            return self.extract_text_from_pdf(file_path)
        else:
            raise ValueError("Unsupported file type for OCR")


ocr_service = OcrService()
