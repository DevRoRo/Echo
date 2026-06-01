from core.ports import AudioGenerationPort, AudioStoragePort, TextGenerationPort

class GenerateConversationalAudioUseCase:
    def __init__(
        self, 
        text_generator: TextGenerationPort,
        audio_generator: AudioGenerationPort, 
        storage: AudioStoragePort
    ):
        self.text_generator = text_generator
        self.audio_generator = audio_generator
        self.storage = storage

    def execute(self, prompt: str, voice_name: str, word_count: int, conversation_context: str) -> dict:
        """
        The Business Logic Workflow:
        1. AI generates a text response based on the student's prompt.
        2. AI converts that specific text into audio.
        3. The system saves the audio to storage.
        """
        if not prompt.strip():
            raise ValueError("The prompt cannot be empty.")
            
        # 1. Think (Generate Text)
        ai_response_text = self.text_generator.generate_text(prompt, word_count)
        
        # 2. Speak (Generate Audio)
        base64_audio = self.audio_generator.generate_base64(ai_response_text, voice_name)
        
        # 3. Save (Store Audio)
        file_path = self.storage.save_base64(base64_audio)
        
        # Return both the text (useful for chat logs) and the audio file path
        return {
            "generated_text": ai_response_text,
            "file_path": file_path
        }

class GenerateTestAudioUseCase:
    # Dependency Injection: We pass the adapters into the core logic
    def __init__(
        self, 
        audio_generator: AudioGenerationPort, 
        storage: AudioStoragePort
    ):
        
        self.audio_generator = audio_generator
        self.storage = storage

    def execute(self, prompt: str, voice_name: str, conversation_context: str) -> str:
        """
        The Business Logic:
        1. Request audio generation.
        2. Save the resulting audio.
        3. Return the location of the saved file.
        """
        if not prompt.strip():
            raise ValueError("Text for audio generation cannot be empty.")
            
        # Call Port 1
        base64_audio = self.audio_generator.generate_base64(prompt, voice_name)
        
        # Call Port 2
        file_path = self.storage.save_base64(base64_audio)
        
        return file_path