import os
from typing import List

import pymupdf
from fastapi import HTTPException

from app.api.v1.schemas.document import DocumentElement, ElementType, TextAlignment
from app.core.config import app_config
from app.core.logging import logger


class ReconstructionService:
    def __init__(self) -> None:
        self.output_dir = app_config.settings.OUTPUT_DIR
        os.makedirs(self.output_dir, exist_ok=True)

        # Set up font path for Japanese
        self.font_path = os.path.join(
            app_config.settings.FONT_DIR, "NotoSansJP-Regular.ttf"
        )
        if not os.path.exists(self.font_path):
            logger.error(f"Specified font file not found at {self.font_path}")
            raise RuntimeError(f"Font file not found at {self.font_path}")
        logger.info(f"Using font file: {self.font_path}")

    def _is_japanese_text(self, text: str) -> bool:
        """Check if text contains Japanese characters."""
        if not text:
            return False
        # Check for Japanese characters (Hiragana, Katakana, Kanji)
        for char in text:
            if (
                "\u3040" <= char <= "\u309f"  # Hiragana
                or "\u30a0" <= char <= "\u30ff"  # Katakana
                or "\u4e00" <= char <= "\u9fff"  # Kanji
            ):
                return True
        return False

    def _get_font_settings(self, text: str) -> tuple[str, str | None]:
        """Get appropriate font settings based on text content."""
        if self._is_japanese_text(text):
            return "notosansjp", self.font_path
        return "helv", None

    async def reconstruct_pdf(
        self,
        elements: List[DocumentElement],
        original_filename: str,
    ) -> str:
        """
        Reconstruct a PDF with translated text while maintaining the original layout.
        """
        try:
            logger.info(f"Started PDF reconstruction for {original_filename}")
            logger.debug(f"Number of elements to process: {len(elements)}")

            # Create a new PDF document
            doc = pymupdf.open()
            current_page = None
            height_adjustment = 0.0  # Track cumulative height adjustments

            for element in elements:
                # Create a new page if the element is on a new page
                if current_page is None or element.position.page > doc.page_count:
                    current_page = doc.new_page()  # type: ignore
                    height_adjustment = 0.0  # Reset height adjustment for new page
                    logger.debug(f"Created new page {doc.page_count}")

                # Insert the text with original position and bounding box
                if element.type == ElementType.TEXT:
                    text = element.translated_content or ""

                    # Get font size from metadata
                    font_size = element.metadata.get("font_size", 11)

                    # Get appropriate font settings
                    fontname, fontfile = self._get_font_settings(text)

                    # Map text alignment to PyMuPDF values
                    alignment_map = {
                        TextAlignment.LEFT: 0,  # TEXT_ALIGN_LEFT
                        TextAlignment.CENTER: 1,  # TEXT_ALIGN_CENTER
                        TextAlignment.RIGHT: 2,  # TEXT_ALIGN_RIGHT
                        TextAlignment.JUSTIFY: 3,  # TEXT_ALIGN_JUSTIFY
                    }
                    alignment = (
                        alignment_map[element.position.text_alignment]
                        if element.position.text_alignment
                        else 0
                    )

                    # Check if this is likely a single line of text
                    is_single_line = (
                        element.position.y1 - element.position.y0 < font_size * 1.5
                    )

                    if is_single_line:
                        logger.debug(f"Inserting text: {text}\nType: single line")
                        logger.debug(f"Position: {element.position}")
                        # For single lines, use insert_text with exact positioning
                        current_page.insert_text(
                            (
                                element.position.x0,
                                element.position.y0 + height_adjustment,
                            ),
                            text,
                            fontname=fontname,
                            fontsize=font_size,
                            fontfile=fontfile,
                            color=(0, 0, 0),
                        )
                    else:
                        logger.debug(f"Inserting text: {text}\nType: multiline")
                        logger.debug(f"Position: {element.position}")
                        # For multi-line text, use textbox with proper dimensions
                        text_box = pymupdf.Rect(
                            element.position.x0,
                            element.position.y0 + height_adjustment,
                            element.position.x1,
                            element.position.y1 + height_adjustment,
                        )

                        # Try to insert text and get required height
                        required_height = current_page.insert_textbox(
                            text_box,
                            text,
                            fontname=fontname,
                            fontsize=font_size,
                            fontfile=fontfile,
                            color=(0, 0, 0),
                            align=alignment,
                            border_width=1,
                        )

                        # If text doesn't fit (negative return value), adjust the box
                        if required_height < 0:
                            logger.warning(
                                f"Text overflow detected. Required height: {
                                    abs(required_height)
                                }"
                            )

                            # Create a new text box with adjusted height
                            adjusted_box = pymupdf.Rect(
                                element.position.x0,
                                element.position.y0 + height_adjustment,
                                element.position.x1,
                                element.position.y1
                                + height_adjustment
                                + abs(required_height),
                            )

                            logger.debug(f"Inserting text: {text}\nType: multiline")
                            logger.debug(f"Adjusted Position: {adjusted_box}")
                            # Try inserting again with adjusted box
                            current_page.insert_textbox(
                                adjusted_box,
                                text,
                                fontname=fontname,
                                fontsize=font_size,
                                fontfile=fontfile,
                                color=(0, 0, 0),
                                align=alignment,
                                border_width=1,
                            )

                            # Update height adjustment for subsequent elements
                            height_adjustment += abs(required_height)

            output_filename = f"translated_{os.path.splitext(original_filename)[0]}.pdf"
            output_path = os.path.join(self.output_dir, output_filename)

            # Save the reconstructed PDF
            doc.save(output_path)
            doc.close()
            logger.info(f"Successfully saved reconstructed PDF to {output_path}")

            return output_filename
        except Exception as e:
            logger.error(f"Error reconstructing PDF: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=500, detail=f"Error reconstructing PDF: {str(e)}"
            )
