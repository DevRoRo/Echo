from core.use_cases import GenerateConversationalAudioUseCase, GenerateTestAudioUseCase

conversational_use_case: GenerateConversationalAudioUseCase | None = None
test_audio_use_case: GenerateTestAudioUseCase | None = None


def get_conversational_use_case() -> GenerateConversationalAudioUseCase:
    if conversational_use_case is None:
        raise RuntimeError("GenerateConversationalAudioUseCase not configured")
    return conversational_use_case


def get_test_audio_use_case() -> GenerateTestAudioUseCase:
    if test_audio_use_case is None:
        raise RuntimeError("GenerateTestAudioUseCase not configured")
    return test_audio_use_case
