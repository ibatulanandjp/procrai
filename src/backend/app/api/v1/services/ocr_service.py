from io import BytesIO
from pathlib import Path
from typing import List, Optional, Tuple, Union

import fitz
import pytesseract
from fastapi import HTTPException
from PIL import Image

from ..schemas.ocr import ElementType, OcrElement, Position


class OcrService:
    def __init__(self, ocr_engine: str = "tesseract", language: str = "eng"):
        self.ocr_engine = ocr_engine
        self.language = language

    async def extract_text(
        self, file_path: Union[Path, str]
    ) -> Tuple[List[OcrElement], int]:
        """
        Extract text and layout information from a PDF or image file.

        Args:
            file_path: Path to the PDF or image file
        Returns:
            Tuple[List[OcrElement], int]: Extracted elements and page count
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

    async def _process_pdf(self, file_path: Path) -> Tuple[List[OcrElement], int]:
        """
        Process a PDF file and extract elements with layout information.

        Args:
            file_path: Path to the PDF file
        Returns:
            Tuple[List[OcrElement], int]: Extracted elements and page count
        """
        try:
            doc = fitz.open(file_path)
            elements = []
            page_count = len(doc)

            for page in doc:
                text_dict = page.get_text("dict")

                if text_dict["blocks"]:
                    for block in text_dict["blocks"]:
                        # Process text block
                        if block.get("type") == 0:
                            lines = []
                            for line in block.get("lines", []):
                                line_text = " ".join(
                                    span["text"] for span in line.get("spans", [])
                                ).rstrip()
                                if line_text:
                                    lines.append(line_text)
                            text = "\n".join(lines).strip()

                            if text:
                                spans = [
                                    span
                                    for line in block.get("lines", [])
                                    for span in line.get("spans", [])
                                ]
                                font_sizes = [span.get("size", 0) for span in spans]
                                average_font_size = (
                                    sum(font_sizes) / len(font_sizes)
                                    if font_sizes
                                    else 0
                                )

                                elements.append(
                                    OcrElement(
                                        type=ElementType.TEXT,
                                        content=text,
                                        position=Position(
                                            x0=block["bbox"][0],
                                            y0=block["bbox"][1],
                                            x1=block["bbox"][2],
                                            y1=block["bbox"][3],
                                            page=page.number + 1,
                                        ),
                                        confidence=1.0,
                                        metadata={
                                            "font": (
                                                spans[0].get("font", "")
                                                if spans
                                                else ""
                                            ),
                                            "font_size": average_font_size,
                                            "block_type": (
                                                "heading"
                                                if average_font_size > 14
                                                else "paragraph"
                                            ),
                                        },
                                    )
                                )
                        # Process image blocks
                        elif block.get("type") == 1:
                            elements.append(
                                OcrElement(
                                    type=ElementType.IMAGE,
                                    content="",  # No text content for images
                                    position=Position(
                                        x0=block["bbox"][0],
                                        y0=block["bbox"][1],
                                        x1=block["bbox"][2],
                                        y1=block["bbox"][3],
                                        page=page.number + 1,
                                    ),
                                    confidence=1.0,
                                    metadata={
                                        "image_type": block.get("ext", ""),
                                        "block_type": "image",
                                    },
                                )
                            )

                else:
                    # If no text blocks, extract elements from image
                    pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
                    image = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

                    ocr_elements = await self._extract_elements_from_image(
                        image, page.number + 1
                    )
                    if ocr_elements:
                        elements.extend(ocr_elements)

            return elements, page_count

        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to process PDF file: {str(e)}",
            )

    async def _process_image(self, image_bytes: bytes) -> Tuple[List[OcrElement], int]:
        """
        Process an image file and extract elements with layout information.

        Args:
            image_bytes: bytes
        Returns:
            Tuple[List[OcrElement], int]: Extracted elements and page count
        """
        try:
            image = Image.open(BytesIO(image_bytes)).convert("RGB")
            elements = await self._extract_elements_from_image(image, 1)
            return elements, 1
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to process image: {str(e)}",
            )

    async def _extract_elements_from_image(
        self, image: Image, page_num: int
    ) -> List[OcrElement]:
        """
        Extract elements from an image using OCR.
        Group elements into logical blocks while preserving layout information.

        Args:
            image: Image
            page_num: int
        Returns:
            List[OcrElement]: Extracted elements
        """
        MIN_CONFIDENCE = 30
        VERTICAL_GAP = 5

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

        def _create_block_element() -> Optional[OcrElement]:
            if not current_block:
                return None

            # Join text preserving newlines based on line numbers
            text_with_lines = []
            current_line = []
            current_line_num = None

            for text, line_num in current_block:
                if current_line_num is None:
                    current_line_num = line_num

                if line_num != current_line_num:
                    text_with_lines.append(" ".join(current_line))
                    current_line = [text]
                    current_line_num = line_num
                else:
                    current_line.append(text)

            if current_line:
                text_with_lines.append(" ".join(current_line))

            average_confidence = sum(current_block_confidence) / len(
                current_block_confidence
            )
            normalized_confidence = average_confidence / 100.0

            # Calculate approximate font size from height
            font_size = last_height * 0.75 if last_height else 12
            return OcrElement(
                type=ElementType.TEXT,
                content="\n".join(text_with_lines).strip(),
                position=current_coordinates,
                confidence=normalized_confidence,
                metadata={
                    "font_size": font_size,
                    "block_type": ("heading" if font_size > 14 else "paragraph"),
                    "word_count": len(current_block),
                    "line_count": len(text_with_lines),
                    "raw_confidence": average_confidence,
                },
            )

        # Process each word
        for i in range(len(ocr_data["text"])):
            text = ocr_data["text"][i].strip()
            confidence = float(ocr_data["conf"][i])
            line_num = int(ocr_data["line_num"][i])

            # Skip empty or low confidence text
            if not text or confidence <= MIN_CONFIDENCE:
                # If we have a current block, add it to elements
                if current_block:
                    element = _create_block_element()
                    if element:
                        elements.append(element)
                    current_block = []
                    current_block_confidence = []
                    current_coordinates = None
                continue

            # Get coordinates
            x0 = float(ocr_data["left"][i])
            y0 = float(ocr_data["top"][i])
            width = float(ocr_data["width"][i])
            height = float(ocr_data["height"][i])

            # Check if we need to start a new block
            new_block_needed = False
            if last_y is not None:
                vertical_gap = y0 - (last_y + last_height) if last_height else 0

                # Start new block if:
                # 1. Significant vertical gap (new paragraph)
                # 2. Moving upward (new column/section)
                if vertical_gap > VERTICAL_GAP or y0 < last_y:
                    new_block_needed = True

            # Create new block if needed
            if new_block_needed and current_block:
                element = _create_block_element()
                if element:
                    elements.append(element)
                current_block = []
                current_block_confidence = []
                current_coordinates = None

            # Update block data
            current_block.append((text, line_num))
            current_block_confidence.append(confidence)

            # Update coordinates
            if current_coordinates is None:
                current_coordinates = Position(
                    x0=x0, y0=y0, x1=x0 + width, y1=y0 + height, page=page_num
                )
            else:
                # Expand block boundaries
                current_coordinates.x0 = min(current_coordinates.x0, x0)
                current_coordinates.y0 = min(current_coordinates.y0, y0)
                current_coordinates.x1 = max(current_coordinates.x1, x0 + width)
                current_coordinates.y1 = max(current_coordinates.y1, y0 + height)

            # Update tracking variables
            last_y = y0
            last_height = height

        # Add last block if exists
        if current_block:
            element = _create_block_element()
            if element:
                elements.append(element)

        return elements


ocr_service = OcrService()
