from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from core.use_cases import GenerateTestAudioUseCase, GenerateConversationalAudioUseCase
from adapters.gemini_adapter import GeminiAdapter
from adapters.storage_adapter import LocalFileSystemStorageAdapter

router = APIRouter()

# --- Schemas ---
class TextToAudioRequest(BaseModel):
    text: str
    voice_name: str = "Kore"

class PromptToAudioRequest(BaseModel):
    prompt: str
    voice_name: str = "Kore"

# --- Endpoints ---

# Original Endpoint: Direct Text-to-Speech
@router.post("/generate-audio/")
async def generate_audio_endpoint(request: TextToAudioRequest):
    gemini_adapter = GeminiAdapter()
    local_storage = LocalFileSystemStorageAdapter()
    use_case = GenerateTestAudioUseCase(audio_generator=gemini_adapter, storage=local_storage)

    try:
        saved_file_path = use_case.execute(text=request.text, voice_name=request.voice_name)
        return {"status": "success", "file_path": saved_file_path}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# NEW Endpoint: Prompt -> AI Text -> Audio
@router.post("/ask-professor/")
async def ask_professor_endpoint(request: PromptToAudioRequest):
    # 1. Instantiate adapters
    gemini_adapter = GeminiAdapter()
    local_storage = LocalFileSystemStorageAdapter()

    # 2. Inject adapters into the new Conversational Use Case
    # Notice we pass gemini_adapter twice, as it fulfills both AI ports!
    use_case = GenerateConversationalAudioUseCase(
        text_generator=gemini_adapter,
        audio_generator=gemini_adapter,
        storage=local_storage
    )

    try:
        # 3. Execute workflow
        result = use_case.execute(prompt=request.prompt, voice_name=request.voice_name)
        
        return {
            "status": "success",
            "message": "AI generated a response and converted it to audio.",
            "ai_text": result["generated_text"],
            "file_path": result["file_path"]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))