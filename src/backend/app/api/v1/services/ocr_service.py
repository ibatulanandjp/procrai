from io import BytesIO
from pathlib import Path
from typing import List, Tuple, Union

import fitz
import pytesseract
from fastapi import HTTPException
from PIL import Image

from ..schemas.ocr import DocumentElement, ElementType, Position


class OcrService:
    def __init__(self, ocr_engine: str = "tesseract", language: str = "eng"):
        self.ocr_engine = ocr_engine
        self.language = language

    async def extract_text(
        self, file_path: Union[Path, str]
    ) -> Tuple[List[DocumentElement], int]:
        """
        Extract text and layout information from a PDF or image file.
        """
        file_path = Path(file_path)

        try:
            if file_path.suffix.lower() in [".png", ".jpg", ".jpeg"]:
                with open(file_path, "rb") as f:
                    return await self._process_image(f.read())
            elif file_path.suffix.lower() == ".pdf":
                return await self._process_pdf(file_path)
            else:
                raise ValueError("Unsupported file type for OCR")
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to process file: {str(e)}",
            )

    async def _process_pdf(self, file_path: Path) -> Tuple[List[DocumentElement], int]:
        doc = fitz.open(file_path)
        elements = []
        page_count = len(doc)

        for page in doc:
            text_dict = page.get_text("dict")

            if text_dict["blocks"]:
                for block in text_dict["blocks"]:
                    if block.get("lines"):
                        text = " ".join(
                            span["text"]
                            for line in block["lines"]
                            for span in line["spans"]
                        )

                        elements.append(
                            DocumentElement(
                                type=ElementType.TEXT,
                                content=text.strip(),
                                position=Position(
                                    x0=block["bbox"][0],
                                    y0=block["bbox"][1],
                                    x1=block["bbox"][2],
                                    y1=block["bbox"][3],
                                    page=page.number + 1,
                                ),
                                confidence=1.0,
                                metadata={
                                    "font": block.get("font", ""),
                                    "size": block.get("size", 0),
                                    "color": block.get("color", ""),
                                },
                            )
                        )
            else:
                pix = page.get_pixmap()
                image = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                page_elements = await self._extract_elements_from_image(
                    image, page.number + 1
                )
                elements.extend(page_elements)

        return elements, page_count

    async def _process_image(
        self, image_bytes: bytes
    ) -> Tuple[List[DocumentElement], int]:
        image = Image.open(BytesIO(image_bytes)).convert("RGB")
        elements = await self._extract_elements_from_image(image, 0)
        return elements, 1

    async def _extract_elements_from_image(
        self, image: Image, page_num: int
    ) -> List[DocumentElement]:
        """
        Extract elements from an image using OCR.
        Group elements into logical blocks while preserving layout information.
        """
        MIN_CONFIDENCE = 0.5
        VERTICAL_GAP = 15

        ocr_data = pytesseract.image_to_data(
            image,
            output_type=pytesseract.Output.DICT,
            lang=self.language,
            config="--psm 6",
        )

        elements = []
        current_block = []
        current_block_confidence = []
        current_coordinates = None
        last_y = None
        last_height = None

        def _create_block_element() -> DocumentElement:
            """
            Helper function to create a DocumentElement from the current block
            """
            if not current_block:
                return None

            average_confidence = sum(current_block_confidence) / len(current_block)
            return DocumentElement(
                type=ElementType.TEXT,
                content=" ".join(current_block).strip(),
                position=current_coordinates,
                confidence=average_confidence,
                metadata={
                    "font": ocr_data["font"][0],
                    "size": ocr_data["size"][0],
                    "color": ocr_data["color"][0],
                    "word_count": len(current_block),
                },
            )

        for i in range(len(ocr_data["text"])):
            text = ocr_data["text"][i].strip()
            confidence = float(ocr_data["conf"][i])

            # Skip empty or low confidence text
            if not text or confidence <= MIN_CONFIDENCE:
                continue

            # Current words coordinates
            current_word_coordinates = Position(
                x0=ocr_data["left"][i],
                y0=ocr_data["top"][i],
                x1=ocr_data["right"][i],
                y1=ocr_data["bottom"][i],
                page=page_num,
            )

            new_block_needed = False

            if last_y is not None:
                vertical_gap = current_word_coordinates.y0 - (last_y + last_height)

                if vertical_gap > VERTICAL_GAP and current_word_coordinates.y0 < last_y:
                    new_block_needed = True

            # Add current block to elements if it exists
            if new_block_needed and current_block:
                block_element = _create_block_element()
                if block_element:
                    elements.append(block_element)
                current_block = []
                current_block_confidence = []
                current_coordinates = None

            # Add current text to block
            current_block.append(text)
            current_block_confidence.append(confidence)

        # Add last block if exists
        if current_block:
            block_element = _create_block_element()
            if block_element:
                elements.append(block_element)

        return elements


ocr_service = OcrService()
