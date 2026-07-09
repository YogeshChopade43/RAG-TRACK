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
    def is_overview_question(self, question: str) -> bool:
        """
        Detect document-overview / summary questions.

        These questions are about the document as a whole (e.g.
        "what is this document about?", "summarize this file").
        They should NOT be rewritten into generic keyword queries,
        otherwise the document reference gets lost ("any document").

        Specific questions like "what does the document say about X?" are
        intentionally NOT treated as overview questions.
        """
        q = question.lower().strip()

        # Explicit summary keywords always count
        if any(
            m in q
            for m in ["summar", "summary", "overview", "tl;dr", "gist", "main idea", "main point"]
        ):
            return True

        # Whole-document "about" patterns
        about_patterns = [
            "what is this document about",
            "what is the document about",
            "what is this file about",
            "what is this doc about",
            "what is this paper about",
            "what is this resume about",
            "what is this cv about",
            "what is this pdf about",
            "what's this document about",
            "what's the document about",
            "what's this file about",
            "what's this doc about",
            "what is the doc about",
            "what's the doc about",
            "what is this about",
            "what's this about",
            "tell me about this document",
            "tell me about this file",
            "tell me about this pdf",
        ]
        return any(p in q for p in about_patterns)

    def should_rewrite(self, question: str) -> bool:
        """
        Decide whether a question needs rewriting.
        Avoid unnecessary LLM calls.
        """

        q = question.lower().strip()

        # Overview questions about the document itself are self-contained:
        # do NOT rewrite them (prevents "the doc" -> "any document").
        if self.is_overview_question(question):
            return False

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
            - Replace third-person pronouns like "his", "her", "they" with a generic
              reference ONLY when they refer to a person/entity outside the document.
            - NEVER replace references to the document itself (e.g. "the doc",
              "this document", "this file") with "any document" or "the document".
              Keep them as "this document".
            - Expand important concepts with synonyms
            - Return only keywords separated by spaces
            - Do NOT answer the question
            - Do NOT return a sentence
            """
        try:
            rewritten = self.llm.chat(system_prompt, question)

            cleaned = self._clean_output(rewritten)

            # fallback if rewrite failed or it became a generic/unhelpful query
            if (
                not cleaned
                or cleaned.lower() == question.lower()
                or "any document" in cleaned.lower()
                or cleaned.lower() in ("the document", "this document", "document")
            ):
                logger.debug("QueryRewrite: fallback to original")
                return question

            logger.info(f"QueryRewrite: '{question}' -> '{cleaned}'")

            return cleaned

        except Exception as e:
            logger.error(f"QueryRewrite failed: {e}", exc_info=True)

            # fallback safely
            return question
