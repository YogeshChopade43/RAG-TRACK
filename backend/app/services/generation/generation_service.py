import re

from app.services.generation.prompt_registry import registry
from app.services.llm import get_llm_service


class GenerationService:
    def __init__(self):
        self.llm = get_llm_service()

    def build_context(self, retrieved_chunks):
        # combine top-k chunks into readable context
        return "\n\n".join(chunk["chunk_text"] for chunk in retrieved_chunks)

    def _build_prompts(self, question: str, retrieved_chunks: list, is_overview: bool = False):
        """Build system and user prompts."""
        context = self.build_context(retrieved_chunks)

        if is_overview:
            prompt_name = "overview"
        else:
            prompt_name = "qa"

        template = registry.get(prompt_name)
        system_prompt = template.system_prompt
        user_prompt = registry.render(prompt_name, context=context, question=question)
        return system_prompt, user_prompt

    def _normalize_answer(self, text: str) -> str:
        """Normalize and de-duplicate model output."""
        if not text:
            return text

        text = text.strip()
        text = re.sub(r'^(?i)answer\s*:\s*', '', text).strip()

        # Collapse exact repeated full-text outputs like repeated answer echoes.
        for repeat in range(5, 1, -1):
            if len(text) % repeat == 0:
                chunk = text[: len(text) // repeat]
                if chunk * repeat == text:
                    text = chunk.strip()
                    break

        paragraphs = [p.strip() for p in re.split(r'(?:\r?\n){2,}', text) if p.strip()]
        cleaned_paragraphs = []
        for paragraph in paragraphs:
            if not cleaned_paragraphs or paragraph != cleaned_paragraphs[-1]:
                cleaned_paragraphs.append(paragraph)

        return "\n\n".join(cleaned_paragraphs)

    def generate(self, question: str, retrieved_chunks: list, is_overview: bool = False):
        system_prompt, user_prompt = self._build_prompts(
            question, retrieved_chunks, is_overview=is_overview
        )
        raw_answer = self.llm.chat(system_prompt, user_prompt)
        return self._normalize_answer(raw_answer)
