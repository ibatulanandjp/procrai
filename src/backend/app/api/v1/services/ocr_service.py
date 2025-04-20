from io import BytesIO
from pathlib import Path
from typing import List, Optional, Tuple, Union

import pymupdf
import pytesseract
from fastapi import HTTPException
from PIL import Image

from app.core.logging import logger

from ..schemas.document import DocumentElement, ElementType, Position, TextAlignment


class OcrService:
    def __init__(self, ocr_engine: str = "tesseract", language: str = "eng"):
        self.ocr_engine = ocr_engine
        self.language = language

    async def extract_text(
        self, file_path: Union[Path, str]
    ) -> Tuple[List[DocumentElement], int]:
        """
        Extract text and layout information from a PDF or image file.

        Args:
            file_path: Path to the PDF or image file
        Returns:
            Tuple[List[DocumentElement], int]: Extracted elements and page count
        """
        file_path = Path(file_path)

        try:
            logger.info(f"Starting OCR processing for file: {file_path}")
            if file_path.suffix.lower() in [".png", ".jpg", ".jpeg"]:
                logger.debug("Processing image file")
                with open(file_path, "rb") as f:
                    return await self._process_image(f.read())
            elif file_path.suffix.lower() == ".pdf":
                logger.debug("Processing PDF file")
                return await self._process_pdf(file_path)
            else:
                logger.error(f"Unsupported file type: {file_path.suffix}")
                raise ValueError("Unsupported file type for OCR")
        except Exception as e:
            logger.error(f"Failed to process file: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to process file: {str(e)}",
            )

    def _should_merge_blocks(self, block1: dict, block2: dict) -> bool:
        """
        Determine if two blocks should be merged into a paragraph.
        Basic checks for vertical spacing and font consistency.
        """
        # Extract and log text content for debugging
        text1 = " ".join(
            span["text"]
            for line in block1.get("lines", [])
            for span in line.get("spans", [])
        ).strip()
        text2 = " ".join(
            span["text"]
            for line in block2.get("lines", [])
            for span in line.get("spans", [])
        ).strip()

        logger.info("Comparing blocks for merging:")
        logger.info(f"Block 1 text: {text1}")
        logger.info(f"Block 2 text: {text2}")

        # Both must be text blocks
        if block1.get("type") != 0 or block2.get("type") != 0:
            return False

        # Get font info from first spans
        span1 = block1.get("lines", [{}])[0].get("spans", [{}])[0]
        span2 = block2.get("lines", [{}])[0].get("spans", [{}])[0]

        # Check if there is no text
        if not text1 or not text2:
            logger.info("One or both blocks have no text")
            return False

        # Check font consistency
        if span1.get("font") != span2.get("font"):
            logger.info(f"Font mismatch: {span1.get('font')} != {span2.get('font')}")
            return False

        # Font size should be similar (within 1pt)
        font_size1 = span1.get("size", 0)
        font_size2 = span2.get("size", 0)
        if abs(font_size1 - font_size2) > 1:
            logger.info(f"Font size difference too large: {font_size1} vs {font_size2}")
            return False

        # Calculate visual spacing using font metrics
        block1_height = block1["bbox"][3] - block1["bbox"][1]
        block2_height = block2["bbox"][3] - block2["bbox"][1]
        visual_spacing = block2["bbox"][1] - block1["bbox"][3]
        avg_line_height = (block1_height + block2_height) / 2
        spacing_ratio = visual_spacing / avg_line_height

        logger.info(
            f"Block analysis:\n"
            f"  Block1 top: {block1['bbox'][1]:.2f}\n"
            f"  Block1 bottom: {block1['bbox'][3]:.2f}\n"
            f"  Block1 height: {block1_height:.2f}\n"
            f"  Font size: {font_size1:.2f}\n"
            f"  Block2 top: {block2['bbox'][1]:.2f}\n"
            f"  Block2 bottom: {block2['bbox'][3]:.2f}\n"
            f"  Block2 height: {block2_height:.2f}\n"
            f"  Font size: {font_size2:.2f}\n"
            f"  Space: {visual_spacing:.2f}\n"
            f"  Line h: {avg_line_height:.2f}\n"
            f"  Ratio: {spacing_ratio:.2f}"
        )

        # Merge if spacing is less than threshold of the average line height
        if spacing_ratio > 0.6:
            logger.info(
                f"Space too large: "
                f"{visual_spacing:.2f}px > {0.6 * avg_line_height:.2f}px"
            )
            return False

        logger.info("Blocks merged based on spacing and font consistency")
        return True

    async def _process_pdf(self, file_path: Path) -> Tuple[List[DocumentElement], int]:
        """
        Process a PDF file and extract elements with layout information.

        Args:
            file_path: Path to the PDF file
        Returns:
            Tuple[List[DocumentElement], int]: Extracted elements and page count
        """
        try:
            doc = pymupdf.open(file_path)
            elements = []
            page_count = len(doc)

            logger.info(f"Processing PDF with {page_count} pages")

            for page_num in range(len(doc)):
                logger.debug(f"Processing page {page_num + 1}/{page_count}")
                page = doc[page_num]
                text_dict = page.get_text("dict")  # type: ignore

                if "blocks" in text_dict:
                    # Group blocks into paragraphs
                    current_blocks = []
                    text_blocks = [b for b in text_dict["blocks"] if b.get("type") == 0]

                    for block in text_blocks:
                        if not current_blocks or not self._should_merge_blocks(
                            current_blocks[-1], block
                        ):
                            current_blocks.append(block)
                        else:
                            # Merge with previous block
                            prev_block = current_blocks[-1]
                            # Combine lines
                            prev_block["lines"].extend(block.get("lines", []))
                            # Update bounding box
                            prev_block["bbox"] = (
                                min(prev_block["bbox"][0], block["bbox"][0]),  # x0
                                min(prev_block["bbox"][1], block["bbox"][1]),  # y0
                                max(prev_block["bbox"][2], block["bbox"][2]),  # x1
                                max(prev_block["bbox"][3], block["bbox"][3]),  # y1
                            )
                            # Update font size with max of both
                            prev_block["lines"][0]["spans"][0]["size"] = max(
                                prev_block["lines"][0]["spans"][0]["size"],
                                block["lines"][0]["spans"][0]["size"],
                            )

                    # Process merged blocks
                    for block in current_blocks:
                        if block.get("type") == 0:  # Text block
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

                                # Detect text alignment
                                text_alignment = self._detect_text_alignment(block)

                                # Detect rotation
                                rotation = self._detect_rotation(block)

                                elements.append(
                                    DocumentElement(
                                        type=ElementType.TEXT,
                                        content=text,
                                        translated_content="",
                                        position=Position(
                                            x0=float(block["bbox"][0]),
                                            y0=float(block["bbox"][1]),
                                            x1=float(block["bbox"][2]),
                                            y1=float(block["bbox"][3]),
                                            page=page_num + 1,
                                            rotation=rotation,
                                            scale=1.0,
                                            z_index=0,
                                            text_alignment=text_alignment,
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
                                            "line_count": len(lines),
                                            "word_count": len(text.split()),
                                        },
                                    )
                                )
                        # Process image blocks
                        elif block.get("type") == 1:
                            elements.append(
                                DocumentElement(
                                    type=ElementType.IMAGE,
                                    content="",  # No text content for images
                                    translated_content="",
                                    position=Position(
                                        x0=float(block["bbox"][0]),
                                        y0=float(block["bbox"][1]),
                                        x1=float(block["bbox"][2]),
                                        y1=float(block["bbox"][3]),
                                        page=page_num + 1,
                                        rotation=0.0,
                                        scale=1.0,
                                        z_index=0,
                                        text_alignment=None,
                                    ),
                                    confidence=1.0,
                                    metadata={
                                        "image_type": block.get("ext", ""),
                                        "block_type": "image",
                                    },
                                )
                            )

                else:
                    logger.warning(f"No text blocks found in page {page_num + 1}")
                    # If no text blocks, extract elements from image
                    pix = page.get_pixmap(matrix=pymupdf.Matrix(2, 2))  # type: ignore
                    image = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)

                    ocr_elements = await self._extract_elements_from_image(
                        image, page_num + 1
                    )
                    if ocr_elements:
                        elements.extend(ocr_elements)

            logger.info(f"PDF processing complete. Extracted {len(elements)} elements")
            return elements, page_count

        except Exception as e:
            logger.error(f"Failed to process PDF file: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to process PDF file: {str(e)}",
            )

    def _detect_text_alignment(self, block: dict) -> Optional[TextAlignment]:
        """
        Detect text alignment from block properties.
        """
        if not block.get("lines"):
            logger.debug("No lines found in block for text alignment detection")
            return None

        # Get the first line's x-coordinates
        first_line = block["lines"][0]
        if not first_line.get("spans"):
            logger.debug("No spans found in first line for text alignment detection")
            return None

        first_span = first_line["spans"][0]
        last_span = first_line["spans"][-1]
        left_margin = first_span["bbox"][0] - block["bbox"][0]
        right_margin = block["bbox"][2] - last_span["bbox"][2]

        # Determine alignment based on margins
        if abs(left_margin - right_margin) < 5:  # 5pt tolerance
            logger.debug("Detected center alignment")
            return TextAlignment.CENTER
        elif left_margin < right_margin:
            logger.debug("Detected left alignment")
            return TextAlignment.LEFT
        else:
            logger.debug("Detected right alignment")
            return TextAlignment.RIGHT

    def _detect_rotation(self, block: dict) -> float:
        """
        Detect text rotation from block properties.
        """
        if not block.get("lines"):
            logger.debug("No lines found in block for rotation detection")
            return 0.0

        # Get rotation from the first span
        first_line = block["lines"][0]
        if not first_line.get("spans"):
            logger.debug("No spans found in first line for rotation detection")
            return 0.0

        first_span = first_line["spans"][0]
        rotation = float(first_span.get("rotation", 0.0))
        logger.debug(f"Detected rotation: {rotation} degrees")
        return rotation

    async def _process_image(
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
            logger.info(f"Image processing complete Extracted {len(elements)} elements")
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
        current_coordinates: Optional[Position] = None
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
        block: List[Tuple[str, int]],
        block_confidence: List[float],
        coordinates: Optional[Position],
    ) -> Optional[DocumentElement]:
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
                "block_type": ("heading" if font_size > 14 else "paragraph"),
                "word_count": len(block),
                "line_count": len(text_with_lines),
                "raw_confidence": average_confidence,
            },
        )

    def _detect_text_alignment_from_coords(
        self, position: Position, block: List[Tuple[str, int]]
    ) -> Optional[TextAlignment]:
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


ocr_service = OcrService()
