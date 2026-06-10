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
    name: str
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
    def find_by_id(self, record_id: int) -> AudioRecord | None:
        pass

    @abstractmethod
    def delete_by_id(self, record_id: int) -> AudioRecord | None:
        pass

    @abstractmethod
    def find_all(
        self,
        name: str | None = None,
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
        name: str | None = None,
        transcription: str | None = None,
        conversation_context: str | None = None,
        voice_name: str | None = None,
    ) -> list[AudioRecord]:
        pass


class DeleteAudioRecordUseCasePort(ABC):
    @abstractmethod
    def execute(self, record_id: int) -> AudioRecord:
        pass


# --- LTI Value Objects ---

@dataclass
class PlatformRegistration:
    id: int | None
    issuer: str
    client_id: str
    auth_login_url: str
    auth_token_url: str
    auth_keyset_url: str
    deployment_ids: list[str]
    created_at: datetime | None
    updated_at: datetime | None


@dataclass
class LtiSession:
    id: int | None
    nonce: str
    target_link_uri: str
    created_at: datetime | None
    expires_at: datetime | None


# --- LTI Outbound (Driven) Ports ---

class PlatformRepositoryPort(ABC):
    @abstractmethod
    def save(self, platform: PlatformRegistration) -> PlatformRegistration:
        pass

    @abstractmethod
    def find_by_issuer(self, issuer: str) -> PlatformRegistration | None:
        pass

    @abstractmethod
    def find_by_id(self, platform_id: int) -> PlatformRegistration | None:
        pass

    @abstractmethod
    def find_all(self) -> list[PlatformRegistration]:
        pass

    @abstractmethod
    def delete_by_id(self, platform_id: int) -> PlatformRegistration | None:
        pass


class LtiSessionRepositoryPort(ABC):
    @abstractmethod
    def save(self, session: LtiSession) -> LtiSession:
        pass

    @abstractmethod
    def find_by_nonce(self, nonce: str) -> LtiSession | None:
        pass

    @abstractmethod
    def delete_by_id(self, session_id: int) -> None:
        pass

    @abstractmethod
    def clean_expired(self) -> int:
        pass


# --- LTI Inbound (Driving) Ports ---

class RegisterPlatformUseCasePort(ABC):
    @abstractmethod
    def execute(self, platform: PlatformRegistration) -> PlatformRegistration:
        pass


class ListPlatformsUseCasePort(ABC):
    @abstractmethod
    def execute(self) -> list[PlatformRegistration]:
        pass


class DeletePlatformUseCasePort(ABC):
    @abstractmethod
    def execute(self, platform_id: int) -> PlatformRegistration:
        pass


class InitiateLoginUseCasePort(ABC):
    @abstractmethod
    def execute(self, issuer: str, target_link_uri: str, login_hint: str, lti_message_hint: str = "") -> dict:
        pass


class ValidateLaunchUseCasePort(ABC):
    @abstractmethod
    def execute(self, id_token: str, state: str) -> dict:
        pass
