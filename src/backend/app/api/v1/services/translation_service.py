from typing import List

import httpx
from fastapi import HTTPException

from app.api.v1.schemas.translation import LanguageCode
from app.core.settings import settings


class TranslationService:
    def __init__(self, model: str = "llama3.1"):
        self.model = model
        self.llm_base_url = settings.OLLAMA_BASE_URL
        self.chunk_size = 1000

    async def translate(
        self,
        text: str,
        src_lang: LanguageCode = LanguageCode.ENGLISH,
        target_lang: LanguageCode = LanguageCode.JAPANESE,
    ) -> str:
        if not text.strip():
            return ""

        chunks = self._chunk_text(text)
        translated_chunks = [
            await self._translate_chunk(chunk, src_lang, target_lang)
            for chunk in chunks
        ]
        return "\n\n".join(translated_chunks)

    def _chunk_text(self, text: str) -> List[str]:
        paragraphs = text.split("\n\n")
        chunks = []
        current_chunk = []
        current_length = 0

        for paragraph in paragraphs:
            if current_length + len(paragraph) > self.chunk_size:
                if current_chunk:
                    chunks.append("\n\n".join(current_chunk))
                current_chunk = [paragraph]
                current_length = len(paragraph)
            else:
                current_chunk.append(paragraph)
                current_length += len(paragraph)

        if current_chunk:
            chunks.append("\n\n".join(current_chunk))

        return chunks

    async def _translate_chunk(
        self,
        chunk: str,
        src_lang: LanguageCode = LanguageCode.ENGLISH,
        target_lang: LanguageCode = LanguageCode.JAPANESE,
    ) -> str:
        prompt = f"""
        Translate the following text from {src_lang} to {target_lang}.
        Preserve the original formatting and structure.
        Just translate the text, do not add any additional text or information.
        Text to translate:
        {chunk}
        """

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.llm_base_url}/api/generate",
                    json={
                        "model": self.model,
                        "prompt": prompt,
                        "stream": False,
                    },
                )
                response.raise_for_status()
                return response.json()["response"].strip()
        except httpx.HTTPError as e:
            raise HTTPException(
                status_code=500, detail=f"Translation service unavailable: {str(e)}"
            )
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Failed to translate text: {str(e)}"
            )
