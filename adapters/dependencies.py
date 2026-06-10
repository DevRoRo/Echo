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

conversational_use_case: GenerateConversationalAudioUseCase | None = None
test_audio_use_case: GenerateTestAudioUseCase | None = None
persist_audio_record_use_case: PersistAudioRecordUseCase | None = None
list_audio_records_use_case: ListAudioRecordsUseCase | None = None
delete_audio_record_use_case: DeleteAudioRecordUseCase | None = None

register_platform_use_case: RegisterPlatformUseCase | None = None
list_platforms_use_case: ListPlatformsUseCase | None = None
delete_platform_use_case: DeletePlatformUseCase | None = None
initiate_login_use_case: InitiateLoginUseCase | None = None
validate_launch_use_case: ValidateLaunchUseCase | None = None


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


def get_delete_audio_record_use_case() -> DeleteAudioRecordUseCase:
    if delete_audio_record_use_case is None:
        raise RuntimeError("DeleteAudioRecordUseCase not configured")
    return delete_audio_record_use_case


def get_register_platform_use_case() -> RegisterPlatformUseCase:
    if register_platform_use_case is None:
        raise RuntimeError("RegisterPlatformUseCase not configured")
    return register_platform_use_case


def get_list_platforms_use_case() -> ListPlatformsUseCase:
    if list_platforms_use_case is None:
        raise RuntimeError("ListPlatformsUseCase not configured")
    return list_platforms_use_case


def get_delete_platform_use_case() -> DeletePlatformUseCase:
    if delete_platform_use_case is None:
        raise RuntimeError("DeletePlatformUseCase not configured")
    return delete_platform_use_case


def get_initiate_login_use_case() -> InitiateLoginUseCase:
    if initiate_login_use_case is None:
        raise RuntimeError("InitiateLoginUseCase not configured")
    return initiate_login_use_case


def get_validate_launch_use_case() -> ValidateLaunchUseCase:
    if validate_launch_use_case is None:
        raise RuntimeError("ValidateLaunchUseCase not configured")
    return validate_launch_use_case
