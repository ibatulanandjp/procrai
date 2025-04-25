from collections import Counter
from pathlib import Path
from typing import List, Tuple

import pymupdf
from fastapi import HTTPException

from app.core.config import app_config
from app.core.logging import logger

from app.api.v1.schemas.document import DocumentElement, ElementType, Position, TextAlignment


class PdfService:
    def __init__(self):
        self.language = app_config.settings.OCR_LANGUAGE

    async def process_pdf(self, file_path: Path) -> Tuple[List[DocumentElement], int]:
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
                            elements.extend(self._process_text_block(block, page_num))
                        elif block.get("type") == 1:  # Image block
                            elements.append(self._process_image_block(block, page_num))

            logger.info(f"PDF processing complete. Extracted {len(elements)} elements")
            return elements, page_count

        except Exception as e:
            logger.error(f"Failed to process PDF file: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to process PDF file: {str(e)}",
            )

    def _should_merge_blocks(self, block1: dict, block2: dict) -> bool:
        """
        Determine if two blocks should be merged into a paragraph.
        Basic checks for vertical spacing and font consistency.
        """
        logger.debug("Comparing blocks for merging")

        # Both must be text blocks
        if block1.get("type") != 0 or block2.get("type") != 0:
            return False

        # Get font info from first spans
        span1 = block1.get("lines", [{}])[0].get("spans", [{}])[0]
        span2 = block2.get("lines", [{}])[0].get("spans", [{}])[0]

        # Extract and log text content for debugging
        text1 = span1.get("text", "").strip()
        text2 = span2.get("text", "").strip()

        logger.debug(f"Block 1 text: {text1}")
        logger.debug(f"Block 2 text: {text2}")

        # Check if there is no text
        if not text1 or not text2:
            logger.debug("One or both blocks have no text")
            return False

        # Check font consistency
        if span1.get("font") != span2.get("font"):
            logger.debug(f"Font mismatch: {span1.get('font')} != {span2.get('font')}")
            return False

        # Font size should be similar (within 1pt)
        font_size1 = span1.get("size", 0)
        font_size2 = span2.get("size", 0)
        if abs(font_size1 - font_size2) > 1:
            logger.debug(f"Font size difference too big: {font_size1} vs {font_size2}")
            return False

        # Calculate visual spacing using font metrics
        block1_height = block1["bbox"][3] - block1["bbox"][1]
        block2_height = block2["bbox"][3] - block2["bbox"][1]
        visual_spacing = block2["bbox"][1] - block1["bbox"][3]
        avg_line_height = (block1_height + block2_height) / 2
        spacing_ratio = visual_spacing / avg_line_height

        logger.debug(
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
        if spacing_ratio > 0.65:
            logger.debug(
                f"Space too large: "
                f"{visual_spacing:.2f}px > {0.65 * avg_line_height:.2f}px"
            )
            return False

        logger.debug("Blocks merged based on spacing and font consistency")
        return True

    def _process_text_block(self, block: dict, page_num: int) -> List[DocumentElement]:
        """Process a text block and return DocumentElements."""
        elements = []
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
            average_font_size = sum(font_sizes) / len(font_sizes) if font_sizes else 0

            # Detect text alignment
            alignments = []
            for line in block.get("lines", []):
                if line.get("spans"):
                    first_span = line["spans"][0]
                    last_span = line["spans"][-1]
                    left_margin = first_span["bbox"][0] - block["bbox"][0]
                    right_margin = block["bbox"][2] - last_span["bbox"][2]

                    if abs(left_margin - right_margin) < 2:
                        alignments.append(TextAlignment.CENTER)
                    elif left_margin < right_margin:
                        alignments.append(TextAlignment.LEFT)
                    else:
                        alignments.append(TextAlignment.RIGHT)

            alignment_counts = Counter(alignments)
            text_alignment = (
                alignment_counts.most_common(1)[0][0] if alignments else None
            )

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
                        "font": spans[0].get("font", "") if spans else "",
                        "font_size": average_font_size,
                        "block_type": (
                            "heading" if average_font_size > 14 else "paragraph"
                        ),
                        "line_count": len(lines),
                        "word_count": len(text.split()),
                    },
                )
            )
        return elements

    def _process_image_block(self, block: dict, page_num: int) -> DocumentElement:
        """Process an image block and return a DocumentElement."""
        return DocumentElement(
            type=ElementType.IMAGE,
            content="",
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

    def _detect_rotation(self, block: dict) -> float:
        """Detect text rotation from block properties."""
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


pdf_service = PdfService()
