import unittest
from datetime import datetime, timezone
from unittest.mock import MagicMock

from core.ports import AudioData, AudioRecord
from core.use_cases import (
    DeleteAudioRecordUseCase,
    GenerateConversationalAudioUseCase,
    GenerateTestAudioUseCase,
    ListAudioRecordsUseCase,
    PersistAudioRecordUseCase,
)


class TestGenerateConversationalAudioUseCase(unittest.TestCase):
    def setUp(self):
        self.text_generator = MagicMock()
        self.audio_generator = MagicMock()
        self.storage = MagicMock()

        self.use_case = GenerateConversationalAudioUseCase(
            text_generator=self.text_generator,
            audio_generator=self.audio_generator,
            storage=self.storage,
        )

    def test_execute_happy_path(self):
        self.text_generator.generate_text.return_value = "Hello world"
        self.audio_generator.generate_base64.return_value = AudioData(
            base64_string="dGVzdA==",
            mime_type="audio/wav",
        )
        self.storage.save_base64.return_value = "/tmp/audio.wav"

        result = self.use_case.execute(
            prompt="Say hello",
            voice_name="en-US-Wavenet-D",
            word_count=50,
            conversation_context="You are a helpful assistant.",
        )

        self.assertEqual(result["generated_text"], "Hello world")
        self.assertEqual(result["file_path"], "/tmp/audio.wav")

        self.text_generator.generate_text.assert_called_once_with(
            "Say hello", 50, "You are a helpful assistant."
        )
        self.audio_generator.generate_base64.assert_called_once_with(
            "Hello world", "en-US-Wavenet-D"
        )
        self.storage.save_base64.assert_called_once()

        audio_data_arg = self.storage.save_base64.call_args[0][0]
        self.assertIsInstance(audio_data_arg, AudioData)
        self.assertEqual(audio_data_arg.base64_string, "dGVzdA==")
        self.assertEqual(audio_data_arg.mime_type, "audio/wav")

    def test_execute_empty_prompt_raises_error(self):
        with self.assertRaises(ValueError) as ctx:
            self.use_case.execute(
                prompt="   ",
                voice_name="en-US-Wavenet-D",
                word_count=50,
                conversation_context="Context",
            )
        self.assertIn("empty", str(ctx.exception).lower())

        self.text_generator.generate_text.assert_not_called()
        self.audio_generator.generate_base64.assert_not_called()
        self.storage.save_base64.assert_not_called()


class TestGenerateTestAudioUseCase(unittest.TestCase):
    def setUp(self):
        self.audio_generator = MagicMock()
        self.storage = MagicMock()

        self.use_case = GenerateTestAudioUseCase(
            audio_generator=self.audio_generator,
            storage=self.storage,
        )

    def test_execute_happy_path(self):
        self.audio_generator.generate_base64.return_value = AudioData(
            base64_string="YXVkaW8=",
            mime_type="audio/mpeg",
        )
        self.storage.save_base64.return_value = "/tmp/test.mp3"

        result = self.use_case.execute(
            prompt="Test audio",
            voice_name="en-US-Wavenet-D",
        )

        self.assertEqual(result, "/tmp/test.mp3")
        self.audio_generator.generate_base64.assert_called_once_with(
            "Test audio", "en-US-Wavenet-D"
        )
        self.storage.save_base64.assert_called_once()

        audio_data_arg = self.storage.save_base64.call_args[0][0]
        self.assertIsInstance(audio_data_arg, AudioData)
        self.assertEqual(audio_data_arg.base64_string, "YXVkaW8=")
        self.assertEqual(audio_data_arg.mime_type, "audio/mpeg")

    def test_execute_empty_prompt_raises_error(self):
        with self.assertRaises(ValueError) as ctx:
            self.use_case.execute(
                prompt="",
                voice_name="en-US-Wavenet-D",
            )
        self.assertIn("empty", str(ctx.exception).lower())

        self.audio_generator.generate_base64.assert_not_called()
        self.storage.save_base64.assert_not_called()


class TestPersistAudioRecordUseCase(unittest.TestCase):
    def setUp(self):
        self.repository = MagicMock()
        self.use_case = PersistAudioRecordUseCase(repository=self.repository)

    def test_execute_saves_record(self):
        record = AudioRecord(
            id=None,
            name="test-recording",
            file_path="/tmp/audio.wav",
            transcription="Hello",
            conversation_context="Context",
            voice_name="voice-A",
            created_at=None,
        )
        expected = AudioRecord(
            id=1,
            name="test-recording",
            file_path="/tmp/audio.wav",
            transcription="Hello",
            conversation_context="Context",
            voice_name="voice-A",
            created_at=datetime.now(timezone.utc),
        )
        self.repository.save.return_value = expected

        result = self.use_case.execute(record)

        self.assertEqual(result.id, 1)
        self.assertEqual(result.name, "test-recording")
        self.assertEqual(result.file_path, "/tmp/audio.wav")
        self.repository.save.assert_called_once()

    def test_execute_sets_created_at(self):
        record = AudioRecord(
            id=None, name="n", file_path="/a.wav", transcription="Hi",
            conversation_context=None, voice_name="v", created_at=None,
        )
        self.repository.save.return_value = record

        self.use_case.execute(record)

        self.assertIsNotNone(record.created_at)

    def test_execute_empty_name_raises_error(self):
        record = AudioRecord(
            id=None, name="", file_path="/a.wav", transcription="Hi",
            conversation_context=None, voice_name="v", created_at=None,
        )
        with self.assertRaises(ValueError) as ctx:
            self.use_case.execute(record)
        self.assertIn("name", str(ctx.exception).lower())
        self.repository.save.assert_not_called()

    def test_execute_empty_file_path_raises_error(self):
        record = AudioRecord(
            id=None, name="n", file_path="", transcription="Hi",
            conversation_context=None, voice_name="v", created_at=None,
        )
        with self.assertRaises(ValueError) as ctx:
            self.use_case.execute(record)
        self.assertIn("file_path", str(ctx.exception).lower())
        self.repository.save.assert_not_called()

    def test_execute_empty_transcription_raises_error(self):
        record = AudioRecord(
            id=None, name="n", file_path="/a.wav", transcription="",
            conversation_context=None, voice_name="v", created_at=None,
        )
        with self.assertRaises(ValueError) as ctx:
            self.use_case.execute(record)
        self.assertIn("transcription", str(ctx.exception).lower())
        self.repository.save.assert_not_called()


class TestListAudioRecordsUseCase(unittest.TestCase):
    def setUp(self):
        self.repository = MagicMock()
        self.use_case = ListAudioRecordsUseCase(repository=self.repository)

    def test_execute_returns_all_records(self):
        expected = [
            AudioRecord(id=1, name="n", file_path="/a.wav", transcription="A",
                        conversation_context=None, voice_name="v",
                        created_at=datetime.now(timezone.utc)),
        ]
        self.repository.find_all.return_value = expected

        result = self.use_case.execute()

        self.assertEqual(result, expected)
        self.repository.find_all.assert_called_once_with(
            name=None,
            transcription=None,
            conversation_context=None,
            voice_name=None,
        )

    def test_execute_passes_filters(self):
        self.repository.find_all.return_value = []

        self.use_case.execute(
            name="lecture-1",
            transcription="hello",
            conversation_context="math",
            voice_name="voice-A",
        )

        self.repository.find_all.assert_called_once_with(
            name="lecture-1",
            transcription="hello",
            conversation_context="math",
            voice_name="voice-A",
        )


class TestDeleteAudioRecordUseCase(unittest.TestCase):
    def setUp(self):
        self.repository = MagicMock()
        self.use_case = DeleteAudioRecordUseCase(repository=self.repository)

    def test_execute_deletes_record(self):
        record = AudioRecord(
            id=1, name="n", file_path="/a.wav", transcription="Hi",
            conversation_context=None, voice_name="v",
            created_at=datetime.now(timezone.utc),
        )
        self.repository.find_by_id.return_value = record
        self.repository.delete_by_id.return_value = record

        result = self.use_case.execute(1)

        self.assertEqual(result.id, 1)
        self.repository.find_by_id.assert_called_once_with(1)
        self.repository.delete_by_id.assert_called_once_with(1)

    def test_execute_raises_error_when_not_found(self):
        self.repository.find_by_id.return_value = None

        with self.assertRaises(ValueError) as ctx:
            self.use_case.execute(999)
        self.assertIn("not found", str(ctx.exception).lower())
        self.repository.delete_by_id.assert_not_called()


if __name__ == "__main__":
    unittest.main()
