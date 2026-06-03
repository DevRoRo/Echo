import unittest
from unittest.mock import MagicMock

from core.ports import AudioData
from core.use_cases import GenerateConversationalAudioUseCase, GenerateTestAudioUseCase


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


if __name__ == "__main__":
    unittest.main()
