from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel

from core.use_cases import GenerateConversationalAudioUseCase, GenerateTestAudioUseCase
from adapters.dependencies import (
    get_conversational_use_case,
    get_test_audio_use_case,
)

router = APIRouter()


class TextToAudioRequest(BaseModel):
    prompt: str
    voice_name: str
    conversation_context: str


class PromptToAudioRequest(BaseModel):
    prompt: str
    voice_name: str
    word_count: int
    conversation_context: str


@router.post("/generate-audio/")
async def generate_audio_endpoint(
    request: TextToAudioRequest,
    use_case: GenerateTestAudioUseCase = Depends(get_test_audio_use_case),
):
    try:
        saved_file_path = use_case.execute(
            prompt=request.prompt,
            voice_name=request.voice_name,
        )
        return {"status": "success", "file_path": saved_file_path}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ask-professor/")
async def ask_professor_endpoint(
    request: PromptToAudioRequest,
    use_case: GenerateConversationalAudioUseCase = Depends(get_conversational_use_case),
):
    try:
        result = use_case.execute(
            prompt=request.prompt,
            voice_name=request.voice_name,
            word_count=request.word_count,
            conversation_context=request.conversation_context,
        )
        return {
            "status": "success",
            "message": "AI generated a response and converted it to audio.",
            "ai_text": result["generated_text"],
            "file_path": result["file_path"],
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
