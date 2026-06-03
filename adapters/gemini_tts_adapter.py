import base64
from google import genai
from google.genai import types
from core.ports import AudioData, AudioGenerationPort


class GeminiTTSAdapter(AudioGenerationPort):
    def __init__(self):
        self.client = genai.Client()

    def generate_base64(self, text: str, voice_name: str) -> AudioData:
        response = self.client.models.generate_content(
            model="gemini-3.1-flash-tts-preview",
            contents=text,
            config=types.GenerateContentConfig(
                response_modalities=["AUDIO"],
                speech_config=types.SpeechConfig(
                    voice_config=types.VoiceConfig(
                        prebuilt_voice_config=types.PrebuiltVoiceConfig(
                            voice_name=voice_name,
                        )
                    )
                ),
            ),
        )

        audio_data = None
        mime_type = "audio/wav"

        if response.candidates and response.candidates[0].content and response.candidates[0].content.parts:
            for part in response.candidates[0].content.parts:
                if part.inline_data and part.inline_data.mime_type and part.inline_data.mime_type.startswith("audio/"):
                    mime_type = part.inline_data.mime_type
                    audio_data = part.inline_data.data
                    break

        if not audio_data:
            raise RuntimeError("Gemini processed the request but returned no audio.")

        return AudioData(
            base64_string=base64.b64encode(audio_data).decode("utf-8"),
            mime_type=mime_type,
        )
