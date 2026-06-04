from core.use_cases import (
    GenerateConversationalAudioUseCase,
    GenerateTestAudioUseCase,
    ListAudioRecordsUseCase,
    PersistAudioRecordUseCase,
)

conversational_use_case: GenerateConversationalAudioUseCase | None = None
test_audio_use_case: GenerateTestAudioUseCase | None = None
persist_audio_record_use_case: PersistAudioRecordUseCase | None = None
list_audio_records_use_case: ListAudioRecordsUseCase | None = None


def get_conversational_use_case() -> GenerateConversationalAudioUseCase:
    if conversational_use_case is None:
        raise RuntimeError("GenerateConversationalAudioUseCase not configured")
    return conversational_use_case


def get_test_audio_use_case() -> GenerateTestAudioUseCase:
    if test_audio_use_case is None:
        raise RuntimeError("GenerateTestAudioUseCase not configured")
    return test_audio_use_case


def get_persist_audio_record_use_case() -> PersistAudioRecordUseCase:
    if persist_audio_record_use_case is None:
        raise RuntimeError("PersistAudioRecordUseCase not configured")
    return persist_audio_record_use_case


def get_list_audio_records_use_case() -> ListAudioRecordsUseCase:
    if list_audio_records_use_case is None:
        raise RuntimeError("ListAudioRecordsUseCase not configured")
    return list_audio_records_use_case
