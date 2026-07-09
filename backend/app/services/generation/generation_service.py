import re
from typing import List

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
            system_prompt = """
                You are a document QA assistant.

                The user is asking for a high-level overview or summary of the
                entire document (e.g. "what is this document about?" or
                "summarize this file").

                You MUST follow these rules:
                1) First identify what KIND of document this is and, if present,
                   who or what it is about (e.g. a resume/CV for a person, a
                   report, an article). State this in the first sentence.
                2) Then give a balanced 2-4 sentence summary covering the main
                   topics/sections of the document as a whole.
                3) Do NOT over-focus on a single project, section, or sentence.
                4) Treat each distinct project, section, or achievement separately;
                   do NOT merge different items into one.
                5) Answer only using the provided context.
                6) If the answer is not present, say:
                   "I could not find the answer in the document."
                7) Do NOT use outside knowledge and do NOT guess.
                8) Provide only the final answer once.
            """
        else:
            system_prompt = """
                You are a document QA assistant.

                You MUST follow these rules:
                1) Answer only using the provided context
                2) If the answer is not present, say:
                "I could not find the answer in the document."
                3) Do NOT use outside knowledge
                4) Do NOT guess if the answer is not present in the context.
                5) Do NOT repeat the question or any part of the prompt.
                6) Provide only the final answer once.
            """

        user_prompt = f"""
                    Context:
                    {context}

                    Question:
                    {question}
                    """
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
