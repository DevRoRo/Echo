from datetime import datetime, timezone

from core.ports import (
    AudioData,
    AudioGenerationPort,
    AudioRecord,
    AudioRecordRepositoryPort,
    AudioStoragePort,
    DeleteAudioRecordUseCasePort,
    GenerateConversationalAudioUseCasePort,
    GenerateTestAudioUseCasePort,
    ListAudioRecordsUseCasePort,
    PersistAudioRecordUseCasePort,
    TextGenerationPort,
)


class GenerateConversationalAudioUseCase(GenerateConversationalAudioUseCasePort):
    def __init__(
        self,
        text_generator: TextGenerationPort,
        audio_generator: AudioGenerationPort,
        storage: AudioStoragePort,
    ):
        self.text_generator = text_generator
        self.audio_generator = audio_generator
        self.storage = storage

    def execute(self, prompt: str, voice_name: str, word_count: int, conversation_context: str) -> dict:
        if not prompt.strip():
            raise ValueError("The prompt cannot be empty.")

        ai_response_text = self.text_generator.generate_text(prompt, word_count, conversation_context)

        audio_data = self.audio_generator.generate_base64(ai_response_text, voice_name)

        file_path = self.storage.save_base64(audio_data)

        return {
            "generated_text": ai_response_text,
            "file_path": file_path,
        }


class GenerateTestAudioUseCase(GenerateTestAudioUseCasePort):
    def __init__(
        self,
        audio_generator: AudioGenerationPort,
        storage: AudioStoragePort,
    ):
        self.audio_generator = audio_generator
        self.storage = storage

    def execute(self, prompt: str, voice_name: str) -> str:
        if not prompt.strip():
            raise ValueError("Text for audio generation cannot be empty.")

        audio_data = self.audio_generator.generate_base64(prompt, voice_name)

        file_path = self.storage.save_base64(audio_data)

        return file_path


class PersistAudioRecordUseCase(PersistAudioRecordUseCasePort):
    def __init__(self, repository: AudioRecordRepositoryPort):
        self.repository = repository

    def execute(self, record: AudioRecord) -> AudioRecord:
        if not record.name.strip():
            raise ValueError("name cannot be empty.")
        if not record.file_path.strip():
            raise ValueError("file_path cannot be empty.")
        if not record.transcription.strip():
            raise ValueError("transcription cannot be empty.")

        record.created_at = datetime.now(timezone.utc)
        return self.repository.save(record)


class DeleteAudioRecordUseCase(DeleteAudioRecordUseCasePort):
    def __init__(self, repository: AudioRecordRepositoryPort):
        self.repository = repository

    def execute(self, record_id: int) -> AudioRecord:
        record = self.repository.find_by_id(record_id)
        if record is None:
            raise ValueError(f"AudioRecord with id {record_id} not found.")

        return self.repository.delete_by_id(record_id)


class ListAudioRecordsUseCase(ListAudioRecordsUseCasePort):
    def __init__(self, repository: AudioRecordRepositoryPort):
        self.repository = repository

    def execute(
        self,
        name: str | None = None,
        transcription: str | None = None,
        conversation_context: str | None = None,
        voice_name: str | None = None,
    ) -> list[AudioRecord]:
        return self.repository.find_all(
            name=name,
            transcription=transcription,
            conversation_context=conversation_context,
            voice_name=voice_name,
        )
