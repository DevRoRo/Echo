from fastapi import FastAPI
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from adapters import dependencies
from adapters.api_router import router as audio_router
from adapters.audio_record_repository import SQLiteAudioRecordRepository
from adapters.gemini_text_adapter import GeminiTextAdapter
from adapters.gemini_tts_adapter import GeminiTTSAdapter
from adapters.storage_adapter import LocalFileSystemStorageAdapter
from core.use_cases import (
    GenerateConversationalAudioUseCase,
    GenerateTestAudioUseCase,
    ListAudioRecordsUseCase,
    PersistAudioRecordUseCase,
)

load_dotenv()

app = FastAPI(title="Echo API - Hexagonal")

origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

gemini_text = GeminiTextAdapter()
gemini_tts = GeminiTTSAdapter()
local_storage = LocalFileSystemStorageAdapter()
audio_record_repo = SQLiteAudioRecordRepository()

dependencies.conversational_use_case = GenerateConversationalAudioUseCase(
    text_generator=gemini_text,
    audio_generator=gemini_tts,
    storage=local_storage,
)
dependencies.test_audio_use_case = GenerateTestAudioUseCase(
    audio_generator=gemini_tts,
    storage=local_storage,
)
dependencies.persist_audio_record_use_case = PersistAudioRecordUseCase(
    repository=audio_record_repo,
)
dependencies.list_audio_records_use_case = ListAudioRecordsUseCase(
    repository=audio_record_repo,
)

app.include_router(audio_router)
app.mount("/temp_audio", StaticFiles(directory="temp_audio"), name="audio")


@app.get("/")
async def root():
    return {"message": "Echo Backend is Online"}
