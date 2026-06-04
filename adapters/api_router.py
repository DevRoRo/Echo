from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from pydantic import BaseModel

from core.ports import AudioRecord
from core.use_cases import (
    GenerateConversationalAudioUseCase,
    GenerateTestAudioUseCase,
    ListAudioRecordsUseCase,
    PersistAudioRecordUseCase,
)
from adapters.dependencies import (
    get_conversational_use_case,
    get_list_audio_records_use_case,
    get_persist_audio_record_use_case,
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


class CreateAudioRecordRequest(BaseModel):
    file_path: str
    transcription: str
    conversation_context: str | None = None
    voice_name: str = "default"


class AudioRecordResponse(BaseModel):
    id: int
    file_path: str
    transcription: str
    conversation_context: str | None
    voice_name: str
    created_at: datetime


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


@router.post("/audio-records/", status_code=201)
async def create_audio_record(
    request: CreateAudioRecordRequest,
    use_case: PersistAudioRecordUseCase = Depends(get_persist_audio_record_use_case),
):
    try:
        print(request)
        record = AudioRecord(
            id=None,
            file_path=request.file_path,
            transcription=request.transcription,
            conversation_context=request.conversation_context,
            voice_name=request.voice_name,
            created_at=None,
        )
        saved = use_case.execute(record)
        return AudioRecordResponse(
            id=saved.id,
            file_path=saved.file_path,
            transcription=saved.transcription,
            conversation_context=saved.conversation_context,
            voice_name=saved.voice_name,
            created_at=saved.created_at,
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/audio-records/")
async def list_audio_records(
    transcription: str | None = Query(None, description="Partial match on transcription"),
    conversation_context: str | None = Query(None, description="Partial match on conversation context"),
    voice_name: str | None = Query(None, description="Exact match on voice name"),
    use_case: ListAudioRecordsUseCase = Depends(get_list_audio_records_use_case),
):
    try:
        records = use_case.execute(
            transcription=transcription,
            conversation_context=conversation_context,
            voice_name=voice_name,
        )
        return [
            AudioRecordResponse(
                id=r.id,
                file_path=r.file_path,
                transcription=r.transcription,
                conversation_context=r.conversation_context,
                voice_name=r.voice_name,
                created_at=r.created_at,
            )
            for r in records
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.options("/ask-professor/")
@router.options("/generate-audio/")
@router.options("/audio-records/")
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
