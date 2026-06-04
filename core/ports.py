from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime


# --- Value Objects ---

@dataclass
class AudioData:
    base64_string: str
    mime_type: str


@dataclass
class AudioRecord:
    id: int | None
    file_path: str
    transcription: str
    conversation_context: str | None
    voice_name: str
    created_at: datetime | None


# --- Outbound (Driven) Ports ---

class TextGenerationPort(ABC):
    @abstractmethod
    def generate_text(self, prompt: str, word_count: int, conversation_context: str) -> str:
        pass


class AudioGenerationPort(ABC):
    @abstractmethod
    def generate_base64(self, text: str, voice_name: str) -> AudioData:
        pass


class AudioStoragePort(ABC):
    @abstractmethod
    def save_base64(self, audio_data: AudioData) -> str:
        pass


class AudioRecordRepositoryPort(ABC):
    @abstractmethod
    def save(self, record: AudioRecord) -> AudioRecord:
        pass

    @abstractmethod
    def find_all(
        self,
        transcription: str | None = None,
        conversation_context: str | None = None,
        voice_name: str | None = None,
    ) -> list[AudioRecord]:
        pass


# --- Inbound (Driving) Ports ---

class GenerateConversationalAudioUseCasePort(ABC):
    @abstractmethod
    def execute(self, prompt: str, voice_name: str, word_count: int, conversation_context: str) -> dict:
        pass


class GenerateTestAudioUseCasePort(ABC):
    @abstractmethod
    def execute(self, prompt: str, voice_name: str) -> str:
        pass


class PersistAudioRecordUseCasePort(ABC):
    @abstractmethod
    def execute(self, record: AudioRecord) -> AudioRecord:
        pass


class ListAudioRecordsUseCasePort(ABC):
    @abstractmethod
    def execute(
        self,
        transcription: str | None = None,
        conversation_context: str | None = None,
        voice_name: str | None = None,
    ) -> list[AudioRecord]:
        pass
