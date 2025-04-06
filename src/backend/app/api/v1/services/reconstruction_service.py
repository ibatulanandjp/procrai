import os
from typing import List

import pymupdf
from fastapi import HTTPException

from app.api.v1.schemas.document import DocumentElement, ElementType
from app.core.config import app_config
from app.core.logging import logger


class ReconstructionService:
    def __init__(self) -> None:
        self.output_dir = os.path.join(app_config.settings.OUTPUT_DIR)
        os.makedirs(self.output_dir, exist_ok=True)

        # Set up font path
        self.font_path = os.path.join(
            app_config.settings.FONT_DIR, "NotoSansCJKsc-Regular.otf"
        )
        if not os.path.exists(self.font_path):
            logger.error(f"Specified font file not found at {self.font_path}")
            raise RuntimeError(f"Font file not found at {self.font_path}")
        logger.info(f"Using font file: {self.font_path}")

    async def reconstruct_pdf(
        self,
        elements: List[DocumentElement],
        original_filename: str,
    ) -> str:
        """
        Reconstruct a PDF with translated text while maintaining the original layout.
        """
        try:
            logger.info(f"Starting PDF reconstruction for {original_filename}")
            logger.debug(f"Number of elements to process: {len(elements)}")

            # Create a new PDF document
            doc = pymupdf.open()
            current_page = None

            for element in elements:
                # Create a new page if the element is on a new page
                if current_page is None or element.position.page > doc.page_count:
                    current_page = doc.new_page()
                    logger.debug(f"Created new page {doc.page_count}")

                # Insert the text with original position
                if element.type == ElementType.TEXT:
                    pos_msg = (
                        f"Inserting text at position "
                        f"({element.position.x0}, {element.position.y0})"
                    )
                    logger.debug(pos_msg)
                    current_page.insert_text(
                        (element.position.x0, element.position.y0),
                        element.translated_content,
                        fontname="notosanscjksc",
                        fontsize=element.metadata.get("font_size", 11),
                        color=(0, 0, 0),
                        fontfile=self.font_path,
                    )

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
