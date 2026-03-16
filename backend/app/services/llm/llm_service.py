import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()


class LLMService:

    def __init__(self):
        self.client = OpenAI(
            api_key=os.getenv("OPENROUTER_API_KEY"),
            base_url="https://openrouter.ai/api/v1",
        )
        self.model = "arcee-ai/trinity-large-preview:free"

    def chat(self, system_prompt: str, user_prompt: str):

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0
        )

        # ---- defensive parsing ----
        if not response.choices:
            print("LLM returned no choices")
            return "The model returned no response."

        message = response.choices[0].message

        if message is None or message.content is None:
            print("LLM returned empty message:", response)
            return "The model returned an empty response."

        return message.content.strip()