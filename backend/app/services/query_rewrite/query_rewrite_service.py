from app.services.llm.llm_service import LLMService
import re


class QueryRewriteService:
    """
    Production-grade query rewriting service.

    Responsibilities:
    - Decide if a query should be rewritten
    - Generate a retrieval-optimized query
    - Clean and validate LLM output
    - Fallback safely if rewrite fails
    """

    def __init__(self):
        self.llm = LLMService()

        # words that signal ambiguous queries
        self.pronouns = [
            "it", "this", "that",
            "he", "she", "they",
            "his", "her", "their"
        ]

        # question prefixes that usually add noise for retrieval
        self.conversational_prefix = [
            "what is", "tell me", "can you",
            "could you", "please", "explain",
            "describe", "give me"
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
            print("QueryRewrite: skipped")
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

Examples:

Question: What is his college name?
Query: college university education institute

Question: What is the CGPA?
Query: CGPA GPA grade point average education score

Question: What skills does the person have?
Query: skills technologies programming languages expertise
"""
        try:

            rewritten = self.llm.chat(system_prompt, question)

            cleaned = self._clean_output(rewritten)

            # fallback if rewrite failed
            if not cleaned or cleaned.lower() == question.lower():
                print("QueryRewrite: fallback to original")
                return question

            print(f"\nQueryRewrite")
            print(f"Original : {question}")
            print(f"Rewritten: {cleaned}\n")

            return cleaned

        except Exception as e:

            print("QueryRewrite failed:", e)

            # fallback safely
            return question