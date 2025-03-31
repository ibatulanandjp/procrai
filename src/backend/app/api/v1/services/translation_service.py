from typing import List

from fastapi import HTTPException

from app.api.v1.schemas.document import DocumentElement, ElementType
from app.api.v1.schemas.translation import (
    LanguageCode,
    TranslationRequest,
    TranslationResponse,
)
from app.core.settings import settings


class TranslationService:
    def __init__(self, model: str = "llama3.1"):
        self.model = model
        self.llm_base_url = settings.OLLAMA_BASE_URL
        self.chunk_size = 1000

    async def translate_elements(
        self, request: TranslationRequest
    ) -> TranslationResponse:
        """
        Translate a list of document elements in a context-aware manner.
        """
        try:
            # Group elements by type and proximity
            grouped_elements = self._group_elements(request.elements)

            # Translate each group
            translated_elements = []
            for group in grouped_elements:
                translated_group = await self._translate_element_group(
                    group, request.src_lang, request.target_lang
                )
                translated_elements.extend(translated_group)

            return TranslationResponse(translated_elements=translated_elements)
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Failed to translate elements: {str(e)}"
            )

    def _group_elements(
        self, elements: List[DocumentElement]
    ) -> List[List[DocumentElement]]:
        """
        Group elements based on type and proximity for context-aware translation.
        """
        if not elements:
            return []

        groups = []
        current_group = []
        last_element = None

        for element in sorted(elements, key=lambda x: (x.position.page, x.position.y0)):
            if last_element and not self._should_group_elements(last_element, element):
                if current_group:
                    groups.append(current_group)
                current_group = []

            current_group.append(element)
            last_element = element

        if current_group:
            groups.append(current_group)

        return groups

    def _should_group_elements(
        self, element1: DocumentElement, element2: DocumentElement
    ) -> bool:
        """
        Determine if two elements should be grouped together.
        """
        # Same page check
        if element1.position.page != element2.position.page:
            return False
        # Same type check
        if element1.type != element2.type:
            return False
        # Close proximity check
        vertical_gap = abs(element2.position.y0 - element1.position.y0)
        average_height = (
            (element2.position.y1 - element2.position.y0)
            + (element1.position.y1 - element1.position.y0)
        ) / 2
        return vertical_gap < average_height * 0.5

    async def _translate_element_group(
        self,
        elements: List[DocumentElement],
        src_lang: LanguageCode,
        target_lang: LanguageCode,
    ) -> List[DocumentElement]:
        """
        Translate a group of related elements together for better context.
        """
        # Skip non-text elements
        if not elements or elements[0].type not in [
            ElementType.TEXT,
            ElementType.HEADING,
            ElementType.FOOTER,
            ElementType.TABLE,
        ]:
            return elements

        # Prepare context
        context = "\n".join([element.content for element in elements])
        translated_text = await self._translate_with_context(
            context, src_lang, target_lang
        )

        # Update translated content
        for element in elements:
            element.translated_content = translated_text
        return elements
