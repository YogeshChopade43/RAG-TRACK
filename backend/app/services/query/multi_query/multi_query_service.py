from app.services.llm.llm_service import LLMService

class MultiQueryService:

    def __init__(self):
        self.llm = LLMService()

    def _decide_expansion_count(self, total_sub_queries: int) -> int:
        """
        Dynamically decide how many expansions per query.
        """

        if total_sub_queries <= 1:
            return 3   # simple query → more expansion

        elif total_sub_queries <= 3:
            return 2   # medium → moderate expansion

        else:
            return 1   # complex → minimal expansion

    def generate_queries(self, query: str, total_sub_queries: int):
        """
        Generate adaptive number of queries.
        """

        num_queries = self._decide_expansion_count(total_sub_queries)

        # if only 1 → skip LLM (optimization)
        if num_queries == 1:
            return [query]

        system_prompt = f"""
                You are a search query expansion assistant.

                Generate {num_queries} different search queries.

                Rules:
                - Keep them short (keywords)
                - Use different wording
                - Do NOT answer
                - Return each on a new line
                """

        try:
            response = self.llm.chat(system_prompt, query)

            queries = response.split("\n")

            cleaned = [
                q.strip("- ").strip()
                for q in queries
                if q.strip()
            ]

            # 🔥 FILTER BAD OUTPUTS
            filtered = []
            for q in cleaned:
                if "empty response" in q.lower():
                    continue
                if len(q.split()) <= 1:   # too short/noisy
                    continue
                filtered.append(q)

            final_queries = [query] + filtered

            # deduplicate
            final_queries = list(dict.fromkeys(final_queries))

            print("\nMultiQuery Expansion")
            print("Base Query:", query)
            print("Expanded:", final_queries)

            return final_queries[:num_queries]

        except Exception as e:
            print("MultiQuery failed:", e)
            return [query]