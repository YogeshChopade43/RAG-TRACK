import logging
import re

from app.services.llm import get_llm_service

logger = logging.getLogger(__name__)


class QueryRewriteService:
    def __init__(self):
        self.llm = get_llm_service()

        # words that signal ambiguous queries
        self.pronouns = [
            "it",
            "this",
            "that",
            "he",
            "she",
            "they",
            "his",
            "her",
            "their",
        ]

        # question prefixes that usually add noise for retrieval
        self.conversational_prefix = [
            "what is",
            "tell me",
            "can you",
            "could you",
            "please",
            "explain",
            "describe",
            "give me",
        ]

    # ---------------------------------------------------------
    # Rewrite Decision Logic
    # ---------------------------------------------------------
    def should_rewrite(self, question: str) -> bool:
        """
        Decide whether a question needs rewriting.
        Avoid unnecessary LLM calls.
        """

        q = question.lower().strip()

        # very short queries
        if len(q.split()) <= 3:
            return True

        # contains pronouns
        if any(p in q for p in self.pronouns):
            return True

        # conversational phrasing
        if any(q.startswith(prefix) for prefix in self.conversational_prefix):
            return True

        return False

    # ---------------------------------------------------------
    # Output cleaning
    # ---------------------------------------------------------
    def _clean_output(self, text: str) -> str:
        """
        Clean LLM output into pure keyword query.
        """

        if not text:
            return ""

        # remove common prefixes
        text = re.sub(r"(?i)^query\s*:\s*", "", text)

        # remove quotes
        text = text.strip().strip('"').strip("'")

        # collapse whitespace
        text = re.sub(r"\s+", " ", text)

        return text.strip()

    # ---------------------------------------------------------
    # Rewrite function
    # ---------------------------------------------------------
    def rewrite(self, question: str) -> str:
        """
        Rewrite query for better retrieval.
        """

        if not self.should_rewrite(question):
            logger.debug("QueryRewrite: skipped")
            return question

        system_prompt = """
            You are a search query optimizer for a document retrieval system.

            Convert the user's question into a concise keyword-style search query.

            Instructions:
            - Remove conversational phrasing like "what is", "tell me", etc.
            - Replace pronouns like "his", "her", "it" with a generic reference if needed
            - Expand important concepts with synonyms
            - Return only keywords separated by spaces
            - Do NOT answer the question
            - Do NOT return a sentence
            """
        try:
            rewritten = self.llm.chat(system_prompt, question)

            cleaned = self._clean_output(rewritten)

            # fallback if rewrite failed
            if not cleaned or cleaned.lower() == question.lower():
                logger.debug("QueryRewrite: fallback to original")
                return question

            logger.info(f"QueryRewrite: '{question}' -> '{cleaned}'")

            return cleaned

        except Exception as e:
            logger.error(f"QueryRewrite failed: {e}", exc_info=True)

            # fallback safely
            return question
