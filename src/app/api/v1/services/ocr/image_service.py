from io import BytesIO
from typing import List, Tuple

import pytesseract
from fastapi import HTTPException
from PIL import Image

from app.core.config import app_config
from app.core.logging import logger

from app.api.v1.schemas.document import DocumentElement, ElementType, Position, TextAlignment


class ImageService:
    def __init__(self):
        self.language = app_config.settings.OCR_LANGUAGE

    async def process_image(
        self, image_bytes: bytes
    ) -> Tuple[List[DocumentElement], int]:
        """
        Process an image file and extract elements with layout information.

        Args:
            image_bytes: bytes
        Returns:
            Tuple[List[DocumentElement], int]: Extracted elements and page count
        """
        try:
            logger.info("Starting image processing")
            image = Image.open(BytesIO(image_bytes)).convert("RGB")
            elements = await self._extract_elements_from_image(image, 1)
            logger.info(
                f"Image processing complete. Extracted {len(elements)} elements"
            )
            return elements, 1
        except Exception as e:
            logger.error(f"Failed to process image: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to process image: {str(e)}",
            )

    async def _extract_elements_from_image(
        self, image: Image.Image, page_num: int
    ) -> List[DocumentElement]:
        """
        Extract elements from an image using OCR.
        Group elements into logical blocks while preserving layout information.

        Args:
            image: Image
            page_num: int
        Returns:
            List[DocumentElement]: Extracted elements
        """
        MIN_CONFIDENCE = 30
        VERTICAL_GAP = 15
        HORIZONTAL_GAP = 20

        logger.debug(f"Starting OCR on image with size {image.size}")
        ocr_data = pytesseract.image_to_data(
            image,
            output_type=pytesseract.Output.DICT,
            lang=self.language,
            config="--psm 6",
        )

        elements = []
        current_block = []
        current_block_confidence = []
        current_coordinates: Position | None = None
        last_y = None
        last_height = None
        last_x = None
        last_width = None

        logger.debug(f"Processing {len(ocr_data['text'])} OCR results")

        # Process each word
        for i in range(len(ocr_data["text"])):
            text = ocr_data["text"][i].strip()
            confidence = float(ocr_data["conf"][i])
            line_num = int(ocr_data["line_num"][i])

            # Skip empty or low confidence text
            if not text or confidence <= MIN_CONFIDENCE:
                # If we have a current block, add it to elements
                if current_block:
                    element = self._create_block_element(
                        current_block, current_block_confidence, current_coordinates
                    )
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
                horizontal_gap = (
                    x0 - (last_x + last_width) if last_x and last_width else 0
                )

                # Start new block if:
                # 1. Significant vertical gap (new paragraph)
                # 2. Moving upward (new column/section)
                # 3. Significant horizontal gap (new column)
                if (
                    vertical_gap > VERTICAL_GAP
                    or y0 < last_y
                    or horizontal_gap > HORIZONTAL_GAP
                ):
                    new_block_needed = True

            # Create new block if needed
            if new_block_needed and current_block:
                element = self._create_block_element(
                    current_block, current_block_confidence, current_coordinates
                )
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
                    x0=x0,
                    y0=y0,
                    x1=x0 + width,
                    y1=y0 + height,
                    page=page_num,
                    rotation=0.0,
                    scale=1.0,
                    z_index=0,
                    text_alignment=None,
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
            last_x = x0
            last_width = width

        # Add last block if exists
        if current_block:
            element = self._create_block_element(
                current_block, current_block_confidence, current_coordinates
            )
            if element:
                elements.append(element)

        logger.debug(f"Created {len(elements)} elements from image")
        return elements

    def _create_block_element(
        self,
        block: list[tuple[str, int]],
        block_confidence: list[float],
        coordinates: Position | None,
    ) -> DocumentElement | None:
        """
        Create a DocumentElement from a block of text and its metadata.

        Args:
            block: List of (text, line_number) tuples
            block_confidence: List of confidence scores for each text item
            coordinates: Position object containing block coordinates
        Returns:
            Optional[DocumentElement]: Created element or None if block is empty
        """
        if not block or coordinates is None:
            logger.debug("Skipping empty block or missing coordinates")
            return None

        # Join text preserving newlines based on line numbers
        text_with_lines = []
        current_line = []
        current_line_num = None

        for text, line_num in block:
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

        average_confidence = sum(block_confidence) / len(block_confidence)
        normalized_confidence = average_confidence / 100.0

        # Calculate approximate font size from height
        font_size = (coordinates.y1 - coordinates.y0) * 0.75

        # Detect text alignment
        text_alignment = self._detect_text_alignment_from_coords(coordinates, block)

        logger.debug(
            f"Creating block element: lines={len(text_with_lines)}, "
            f"words={len(block)}, confidence={normalized_confidence:.2f}"
        )

        return DocumentElement(
            type=ElementType.TEXT,
            content="\n".join(text_with_lines).strip(),
            translated_content="",
            position=Position(
                x0=coordinates.x0,
                y0=coordinates.y0,
                x1=coordinates.x1,
                y1=coordinates.y1,
                page=coordinates.page,
                rotation=coordinates.rotation,
                scale=coordinates.scale,
                z_index=coordinates.z_index,
                text_alignment=text_alignment,
            ),
            confidence=normalized_confidence,
            metadata={
                "font_size": font_size,
                "block_type": "heading" if font_size > 14 else "paragraph",
                "word_count": len(block),
                "line_count": len(text_with_lines),
                "raw_confidence": average_confidence,
            },
        )

    def _detect_text_alignment_from_coords(
        self, position: Position, block: list[tuple[str, int]]
    ) -> TextAlignment | None:
        """
        Detect text alignment from coordinates and block data.
        """
        if not block:
            logger.debug("No block data for text alignment detection")
            return None

        # Get the first line's x-coordinates
        first_line = [t for t, ln in block if ln == block[0][1]]
        if not first_line:
            logger.debug("No first line found for text alignment detection")
            return None

        # Calculate margins
        left_margin = position.x0
        right_margin = position.x1

        # Determine alignment based on margins
        if abs(left_margin - right_margin) < 5:  # 5pt tolerance
            logger.debug("Detected center alignment from coordinates")
            return TextAlignment.CENTER
        elif left_margin < right_margin:
            logger.debug("Detected left alignment from coordinates")
            return TextAlignment.LEFT
        else:
            logger.debug("Detected right alignment from coordinates")
            return TextAlignment.RIGHT


image_service = ImageService()
