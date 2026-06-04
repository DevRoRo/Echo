import base64
import os
import uuid
import wave
from core.ports import AudioData, AudioStoragePort

MIME_TO_EXT = {
    "audio/wav": ".wav",
    "audio/mpeg": ".mp3",
    "audio/mp3": ".mp3",
    "audio/ogg": ".ogg",
    "audio/webm": ".webm",
    "audio/mp4": ".mp4",
}


class LocalFileSystemStorageAdapter(AudioStoragePort):
    def __init__(self, output_dir: str = "temp_audio"):
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)

    def save_base64(self, audio_data: AudioData) -> str:
        filename = f"{uuid.uuid4()}.wav"
        filepath = os.path.join(self.output_dir, filename)

        audio_bytes = base64.b64decode(audio_data.base64_string)
        with wave.open(filepath, "wb") as f:
            f.setnchannels(1)
            f.setsampwidth(2)
            f.setframerate(24000)

            f.writeframes(audio_bytes)

        return filepath
