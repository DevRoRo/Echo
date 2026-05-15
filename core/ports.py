from abc import ABC, abstractmethod

# PORT 1: How we generate text (LLM)
class TextGenerationPort(ABC):
    @abstractmethod
    def generate_text(self, prompt: str) -> str:
        """Must accept a prompt and return the AI-generated text response."""
        pass

# PORT 2: How we generate audio
class AudioGenerationPort(ABC):
    @abstractmethod
    def generate_base64(self, text: str, voice_name: str) -> str:
        """Must return a base64 encoded audio string."""
        pass

# PORT 3: How we store audio
class AudioStoragePort(ABC):
    @abstractmethod
    def save_base64(self, base64_string: str) -> str:
        """Must save the string to a file/cloud and return the file path/URL."""
        pass