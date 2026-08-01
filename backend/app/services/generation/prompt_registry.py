from dataclasses import dataclass
from typing import Optional


@dataclass
class PromptTemplate:
    system_prompt: str
    user_prompt_template: str


class PromptRegistry:
    def __init__(self):
        self._prompts: dict[str, PromptTemplate] = {}

    def register(self, name: str, system_prompt: str, user_prompt_template: str) -> None:
        self._prompts[name] = PromptTemplate(
            system_prompt=system_prompt, user_prompt_template=user_prompt_template
        )

    def get(self, name: str) -> Optional[PromptTemplate]:
        return self._prompts.get(name)

    def render(self, name: str, **kwargs) -> str:
        template = self._prompts.get(name)
        if template is None:
            raise KeyError(f"Prompt template '{name}' not found in registry.")
        return template.user_prompt_template.format(**kwargs)

    def list_prompts(self) -> dict[str, PromptTemplate]:
        return dict(self._prompts)


registry = PromptRegistry()

registry.register(
    name="qa",
    system_prompt="""
        You are a document QA assistant.

        You MUST follow these rules:
        1) Answer only using the provided context
        2) If the answer is not present, say:
        "I could not find the answer in the document."
        3) Do NOT use outside knowledge
        4) Do NOT guess if the answer is not present in the context.
        5) Do NOT repeat the question or any part of the prompt.
        6) Provide only the final answer once.
    """,
    user_prompt_template="""
                Context:
                {context}

                Question:
                {question}
                """,
)

registry.register(
    name="overview",
    system_prompt="""
        You are a document QA assistant.

        The user is asking for a high-level overview or summary of the
        entire document (e.g. "what is this document about?" or
        "summarize this file").

         You MUST follow these rules:
        1) First identify what KIND of document this is and, if present,
           who or what it is about (e.g. a resume/CV for a person, a
           report, an article). State this in the first sentence.
        2) Then give a comprehensive 4-6 sentence summary covering ALL
           the main topics/sections of the document as a whole.
        3) Do NOT over-focus on a single project, section, or sentence.
        4) Treat each distinct project, section, or achievement separately;
           do NOT merge different items into one.
        5) When listing items (projects, skills, experience), use bullet
           points for clarity.
        6) Answer only using the provided context.
        7) If the answer is not present, say:
           "I could not find the answer in the document."
        8) Do NOT use outside knowledge and do NOT guess.
        9) Provide only the final answer once.
    """,
    user_prompt_template="""
                Context:
                {context}

                Question:
                {question}
                """,
)
