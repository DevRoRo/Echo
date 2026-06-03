from abc import ABC, abstractmethod
from dataclasses import dataclass


# --- Value Objects ---

@dataclass
class AudioData:
    base64_string: str
    mime_type: str


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


# --- Inbound (Driving) Ports ---

class GenerateConversationalAudioUseCasePort(ABC):
    @abstractmethod
    def execute(self, prompt: str, voice_name: str, word_count: int, conversation_context: str) -> dict:
        pass


class GenerateTestAudioUseCasePort(ABC):
    @abstractmethod
    def execute(self, prompt: str, voice_name: str) -> str:
        pass
