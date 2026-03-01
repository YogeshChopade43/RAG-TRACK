import os
from openai import OpenAI

from dotenv import load_dotenv
load_dotenv()

client = OpenAI(
    api_key=os.getenv("OPENROUTER_API_KEY"),
    base_url="https://openrouter.ai/api/v1",
)


class GenerationService:

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

        response = client.chat.completions.create(
            model="arcee-ai/trinity-large-preview:free",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0
        )

        return response.choices[0].message.content.strip()