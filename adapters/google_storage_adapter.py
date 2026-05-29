import os
import uuid
import datetime
from google.cloud import storage
from google.oauth2 import service_account
from core.ports import AudioStoragePort

class GCSStorageAdapter(AudioStoragePort):
    def __init__(self):
        """
        Inicializa o cliente do Google Cloud Storage.
        As credenciais e o nome do bucket são carregados das variáveis de ambiente.
        """
        # Puxa o caminho do arquivo JSON e o nome do bucket do .env
        self.credentials_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
        self.bucket_name = os.getenv("GCS_BUCKET_NAME")

        if not self.credentials_path or not self.bucket_name:
            raise ValueError("As credenciais do GCP ou o nome do bucket não foram configurados no .env")

        # Cria o cliente de storage autenticado
        self.client = storage.Client.from_service_account_json(self.credentials_path)
        self.bucket = self.client.bucket(self.bucket_name)

    def upload_ai_audio(self, audio_bytes: bytes, prefix: str = "ai_prompts") -> str:
        """
        Faz o upload direto de bytes de áudio gerados pela IA no backend.
        
        :param audio_bytes: O conteúdo do áudio em bytes gerado pelo Gemini/TTS.
        :param prefix: Pasta lógica dentro do bucket (ex: ai_prompts).
        :return: A URL pública do arquivo armazenado.
        """
        # Gera um nome de arquivo único para evitar colisões
        unique_filename = f"{prefix}/{uuid.uuid4()}.mp3"
        
        # Cria uma referência ao "blob" (o arquivo no bucket)
        blob = self.bucket.blob(unique_filename)
        
        # Faz o upload dos bytes
        blob.upload_from_string(audio_bytes, content_type="audio/mpeg")
        
        # Retorna a URL pública (requer que o bucket tenha acesso de leitura público)
        return blob.public_url

    def generate_signed_upload_url(self, file_extension: str = "webm", prefix: str = "student_answers", expiration_minutes: int = 15) -> dict:
        """
        Gera uma URL assinada (Signed URL) para que o frontend do Next.js faça o upload
        diretamente para o Google Cloud Storage, contornando o servidor FastAPI.
        
        :param file_extension: Extensão do arquivo que será salvo (geralmente webm do MediaRecorder).
        :param prefix: Pasta lógica dentro do bucket.
        :param expiration_minutes: Tempo de validade do link gerado.
        :return: Um dicionário contendo a URL de upload e o nome do arquivo gerado.
        """
        unique_filename = f"{prefix}/{uuid.uuid4()}.{file_extension}"
        blob = self.bucket.blob(unique_filename)

        # Gera a URL que concede permissão temporária de escrita
        url = blob.generate_signed_url(
            version="v4",
            expiration=datetime.timedelta(minutes=expiration_minutes),
            method="PUT",
            content_type=f"audio/{file_extension}",
        )

        # Retornamos também o nome do arquivo para que o backend possa salvá-lo no PostgreSQL depois
        return {
            "upload_url": url,
            "filename": unique_filename,
            "public_url": f"https://storage.googleapis.com/{self.bucket_name}/{unique_filename}"
        }

    def delete_audio(self, filename: str) -> bool:
        """
        Remove um arquivo de áudio do bucket. Útil para limpeza de testes excluídos.
        """
        blob = self.bucket.blob(filename)
        if blob.exists():
            blob.delete()
            return True
        return False