import base64
import os
import uuid
import datetime
from google.cloud import storage
from core.ports import AudioData, AudioStoragePort

MIME_TO_EXT = {
    "audio/wav": ".wav",
    "audio/mpeg": ".mp3",
    "audio/mp3": ".mp3",
    "audio/ogg": ".ogg",
    "audio/webm": ".webm",
    "audio/mp4": ".mp4",
}


class GCSStorageAdapter(AudioStoragePort):
    def __init__(self):
        self.credentials_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
        self.bucket_name = os.getenv("GCS_BUCKET_NAME")

        if not self.credentials_path or not self.bucket_name:
            raise ValueError("GCP credentials or bucket name not configured in .env")

        self.client = storage.Client.from_service_account_json(self.credentials_path)
        self.bucket = self.client.bucket(self.bucket_name)

    def save_base64(self, audio_data: AudioData) -> str:
        ext = MIME_TO_EXT.get(audio_data.mime_type, ".wav")
        unique_filename = f"ai_prompts/{uuid.uuid4()}{ext}"

        audio_bytes = base64.b64decode(audio_data.base64_string)
        content_type = audio_data.mime_type if audio_data.mime_type.startswith("audio/") else "audio/mpeg"

        blob = self.bucket.blob(unique_filename)
        blob.upload_from_string(audio_bytes, content_type=content_type)

        return blob.public_url

    def upload_ai_audio(self, audio_bytes: bytes, prefix: str = "ai_prompts") -> str:
        unique_filename = f"{prefix}/{uuid.uuid4()}.mp3"
        blob = self.bucket.blob(unique_filename)
        blob.upload_from_string(audio_bytes, content_type="audio/mpeg")
        return blob.public_url

    def generate_signed_upload_url(
        self, file_extension: str = "webm", prefix: str = "student_answers", expiration_minutes: int = 15
    ) -> dict:
        unique_filename = f"{prefix}/{uuid.uuid4()}.{file_extension}"
        blob = self.bucket.blob(unique_filename)

        url = blob.generate_signed_url(
            version="v4",
            expiration=datetime.timedelta(minutes=expiration_minutes),
            method="PUT",
            content_type=f"audio/{file_extension}",
        )

        return {
            "upload_url": url,
            "filename": unique_filename,
            "public_url": f"https://storage.googleapis.com/{self.bucket_name}/{unique_filename}",
        }

    def delete_audio(self, filename: str) -> bool:
        blob = self.bucket.blob(filename)
        if blob.exists():
            blob.delete()
            return True
        return False
