import logging
import re

from app.services.llm import get_llm_service

logger = logging.getLogger(__name__)


class QueryDecompositionService:
    """
    Splits multi-intent queries into independent sub-queries.
    """

    def __init__(self):
        self.llm = get_llm_service()

    # Detect if decomposition is needed
    def should_decompose(self, query: str) -> bool:
        q = query.lower()

        # simple heuristics
        if "and" in q or "or" in q or "but" in q or "also" in q or "additionally" in q:
            return True

        if q.count("?") > 1:
            return True

        return False

    # Fallback simple splitter
    def _rule_based_split(self, query: str):
        parts = re.split(r"\band\b|\?", query)
        return [p.strip() for p in parts if p.strip()]

    # LLM-based decomposition
    def _llm_decompose(self, query: str):

        prompt = f"""
                Break the following query into independent questions.

                Rules:
                - Each question should be standalone
                - Keep them short
                - Do NOT answer
                - Return each question on a new line

                Query:
                {query}
                """

        response = self.llm.chat("", prompt)

        questions = response.split("\n")

        cleaned = [q.strip("- ").strip() for q in questions if q.strip()]

        return cleaned

    def decompose(self, query: str):

        if not self.should_decompose(query):
            logger.debug("QueryDecomposition: skipped")
            return [query]

        try:
            sub_queries = self._llm_decompose(query)

            if not sub_queries:
                logger.debug("QueryDecomposition: fallback to rule-based")
                return self._rule_based_split(query)

            if len(sub_queries) < 2:
                logger.debug("QueryDecomposition: fallback to rule-based")
                return self._rule_based_split(query)

            logger.info(
                f"QueryDecomposition: original='{query}', sub_queries={sub_queries}"
            )

            return sub_queries

        except Exception as e:
            logger.error(f"QueryDecomposition failed: {e}", exc_info=True)
            return self._rule_based_split(query)
