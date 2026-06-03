from google import genai
from core.ports import TextGenerationPort


class GeminiTextAdapter(TextGenerationPort):
    def __init__(self):
        self.client = genai.Client()

    def generate_text(self, prompt: str, word_count: int, conversation_context: str) -> str:
        prompt_string = (
            f"Context: {conversation_context}\n\n"
            f"{prompt}\n\n"
            f"MAX word count: {word_count}\n"
            f"TEXT MUST BE IN ENGLISH"
        )
        response = self.client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt_string,
        )

        if not response.text:
            raise RuntimeError("Gemini processed the prompt but returned no text.")

        return response.text
