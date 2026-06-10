from fastapi import FastAPI
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from adapters import dependencies
from adapters.api_router import router as audio_router
from adapters.audio_record_repository import Base, SQLiteAudioRecordRepository
from adapters.gemini_text_adapter import GeminiTextAdapter
from adapters.gemini_tts_adapter import GeminiTTSAdapter
from adapters.lti_key_manager import LtiKeyManager
from adapters.lti_middleware import LTIAuthMiddleware
from adapters.lti_router import router as lti_router
from adapters.lti_repository import SQLitePlatformRepository, SQLiteLtiSessionRepository
from adapters.storage_adapter import LocalFileSystemStorageAdapter
from core.lti_use_cases import (
    DeletePlatformUseCase,
    InitiateLoginUseCase,
    ListPlatformsUseCase,
    RegisterPlatformUseCase,
    ValidateLaunchUseCase,
)
from core.use_cases import (
    DeleteAudioRecordUseCase,
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
lti_platform_repo = SQLitePlatformRepository(audio_record_repo.engine)
lti_session_repo = SQLiteLtiSessionRepository(audio_record_repo.engine)
lti_key_manager = LtiKeyManager()

Base.metadata.create_all(audio_record_repo.engine)

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
dependencies.delete_audio_record_use_case = DeleteAudioRecordUseCase(
    repository=audio_record_repo,
)
dependencies.register_platform_use_case = RegisterPlatformUseCase(
    repository=lti_platform_repo,
)
dependencies.list_platforms_use_case = ListPlatformsUseCase(
    repository=lti_platform_repo,
)
dependencies.delete_platform_use_case = DeletePlatformUseCase(
    repository=lti_platform_repo,
)
dependencies.initiate_login_use_case = InitiateLoginUseCase(
    platform_repo=lti_platform_repo,
    session_repo=lti_session_repo,
)
dependencies.validate_launch_use_case = ValidateLaunchUseCase(
    platform_repo=lti_platform_repo,
    session_repo=lti_session_repo,
    key_manager=lti_key_manager,
)

app.add_middleware(LTIAuthMiddleware)

app.include_router(audio_router)
app.include_router(lti_router)
app.mount("/temp_audio", StaticFiles(directory="temp_audio"), name="audio")


@app.get("/")
async def root():
    return {"message": "Echo Backend is Online"}
