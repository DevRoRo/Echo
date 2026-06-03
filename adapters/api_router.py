from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

from pydantic import BaseModel

from core.use_cases import GenerateTestAudioUseCase, GenerateConversationalAudioUseCase
from adapters.gemini_adapter import GeminiAdapter
from adapters.storage_adapter import LocalFileSystemStorageAdapter

router = APIRouter()

# --- Schemas ---
class TextToAudioRequest(BaseModel):
    prompt: str
    voice_name: str
    conversation_context: str


class PromptToAudioRequest(BaseModel):
    prompt: str
    voice_name: str
    word_count: int
    conversation_context: str

# --- Endpoints ---

# Original Endpoint: Direct Text-to-Speech
@router.post("/generate-audio/")
async def generate_audio_endpoint(request: TextToAudioRequest):
    gemini_adapter = GeminiAdapter()
    local_storage = LocalFileSystemStorageAdapter()
    use_case = GenerateTestAudioUseCase(audio_generator=gemini_adapter, storage=local_storage)

    try:
        saved_file_path = use_case.execute(prompt=request.prompt, voice_name=request.voice_name, conversation_context=request.conversation_context)
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
        result = use_case.execute(prompt=request.prompt, voice_name=request.voice_name, word_count=request.word_count, conversation_context=request.conversation_context)
        
        return {
            "status": "success",
            "message": "AI generated a response and converted it to audio.",
            "ai_text": result["generated_text"],
            "file_path": result["file_path"]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@router.options("/ask-professor/")
@router.options("/generate-audio/")
async def cors_preflight():
    return Response(
        status_code=200,
        headers={
            "Access-Control-Allow-Origin": "http://localhost:3000",
            "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type",
            "Access-Control-Allow-Credentials": "true",
            "Access-Control-Max-Age": "600",
        },
    )
