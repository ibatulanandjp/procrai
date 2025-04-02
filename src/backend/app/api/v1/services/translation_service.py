from typing import List

import httpx
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

        translated_elements = []
        for i, element in enumerate(elements):
            # Get context from nearby elements
            start_idx = max(0, i - 2)
            end_idx = min(len(elements), i + 3)
            context_elements = elements[start_idx:end_idx]

            # Build context string
            context = "\n".join(
                "..." if j == i else e.content
                for j, e in enumerate(context_elements, start=start_idx)
            )

            print("content to translate", element.content)
            # Translate with context
            translated_content = await self._translate_text_with_context(
                element.content, src_lang, target_lang, context
            )
            print("translated_content", translated_content)

            # Create translated element
            translated_element = element.model_copy()
            translated_element.translated_content = translated_content
            translated_elements.append(translated_element)

        return translated_elements

    async def _translate_text_with_context(
        self,
        text: str,
        src_lang: LanguageCode,
        target_lang: LanguageCode,
        context: str,
    ) -> str:
        """
        Translate text with context for better accuracy.
        """
        prompt = f"""
        You are a professional document translator.
        Your goal is to translate the given text accurately while preserving meaning
        and tone from {src_lang} to {target_lang}.

        Context for better translation:
        {context}

        Original text (to translate):
        {text}

        ### Response Format:
        Provide only the translated text without any additional explanations.
        """

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.llm_base_url}/api/generate",
                    json={
                        "model": self.model,
                        "prompt": prompt,
                        "temperature": 0.0,
                        "stream": False,
                    },
                )
                response.raise_for_status()
                result = response.json()
                if "error" in result:
                    raise ValueError(f"Ollama error: {result['error']}")
                if "response" not in result:
                    raise ValueError("No response from Ollama")
                print("result", result)
                return result["response"].strip()
        except httpx.HTTPError as e:
            raise HTTPException(
                status_code=502, detail=f"Translation service error: {str(e)}"
            )
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Failed to translate text: {str(e)}"
            )
