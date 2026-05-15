import base64
import os
import uuid
import wave
from core.ports import AudioStoragePort

class LocalFileSystemStorageAdapter(AudioStoragePort):
    def __init__(self, output_dir: str = "temp_audio"):
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)

    def save_base64(self, base64_string: str) -> str:
        filename = f"{uuid.uuid4()}.wav"
        filepath = os.path.join(self.output_dir, filename)

        audio_bytes = base64.b64decode(base64_string)

        with wave.open(filepath, "wb") as file:
            file.setnchannels(1)
            file.setsampwidth(2)
            file.setframerate(24000)

            file.writeframes(audio_bytes)

        return filepath