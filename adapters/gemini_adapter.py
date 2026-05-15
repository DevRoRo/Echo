import base64
from google import genai
from google.genai import types
from core.ports import AudioGenerationPort, TextGenerationPort

class GeminiAdapter(AudioGenerationPort, TextGenerationPort):
    def __init__(self):
        self.client = genai.Client()

    def generate_text(self, prompt: str) -> str:
        response = self.client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
        )
        
        if not response.text:
            raise RuntimeError("Gemini processed the prompt but returned no text.")
            
        return response.text   

    def generate_base64(self, text: str, voice_name: str) -> str:
        response = self.client.models.generate_content(
            model="gemini-3.1-flash-tts-preview",
            contents=text,
            config=types.GenerateContentConfig(
                response_modalities=["AUDIO"],
                speech_config=types.SpeechConfig(
                    voice_config=types.VoiceConfig(
                        prebuilt_voice_config=types.PrebuiltVoiceConfig(
                            voice_name=voice_name
                        )
                    )
                )
            )
        )
        
        audio_bytes = None
        if response.candidates and response.candidates[0].content.parts:
            for part in response.candidates[0].content.parts:
                if part.inline_data and part.inline_data.mime_type.startswith("audio/"):
                    audio_bytes = part.inline_data.data
                    break
                    
        if not audio_bytes:
            raise RuntimeError("Gemini processed the request but returned no audio.")

        return base64.b64encode(audio_bytes).decode("utf-8")