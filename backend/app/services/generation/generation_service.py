from app.services.llm.llm_service_local import LLMServiceLocal


class GenerationService:
    def __init__(self):
        self.llm = LLMServiceLocal()

    def build_context(self, retrieved_chunks):
        # combine top-k chunks into readable context
        return "\n\n".join(chunk["chunk_text"] for chunk in retrieved_chunks)

    def generate(self, question: str, retrieved_chunks: list):

        context = self.build_context(retrieved_chunks)

        system_prompt = """
                You are a document QA assistant.

                You MUST follow these rules:
                1) Answer only using the provided context
                2) If the answer is not present, say:
                "I could not find the answer in the document."
                3) Do NOT use outside knowledge
                4) Do NOT guess if the answer is not present in the context.
            """

        user_prompt = f"""
                    Context:
                    {context}

                    Question:
                    {question}
                    """

        return self.llm.chat(system_prompt, user_prompt)
