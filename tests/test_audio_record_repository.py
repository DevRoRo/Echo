import tempfile
import unittest
from datetime import datetime, timezone

from core.ports import AudioRecord
from adapters.audio_record_repository import SQLiteAudioRecordRepository


class TestSQLiteAudioRecordRepository(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.tmp.close()
        self.repo = SQLiteAudioRecordRepository(db_path=self.tmp.name)

    def tearDown(self):
        import os
        self.repo.dispose()
        os.unlink(self.tmp.name)

    def test_save_and_find_all(self):
        record = AudioRecord(
            id=None,
            file_path="/tmp/audio.wav",
            transcription="Hello world",
            conversation_context="Greeting context",
            voice_name="en-US-Wavenet-D",
            created_at=datetime.now(timezone.utc),
        )
        saved = self.repo.save(record)
        self.assertIsNotNone(saved.id)
        self.assertEqual(saved.file_path, "/tmp/audio.wav")
        self.assertEqual(saved.transcription, "Hello world")
        self.assertEqual(saved.conversation_context, "Greeting context")
        self.assertEqual(saved.voice_name, "en-US-Wavenet-D")

        results = self.repo.find_all()
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].id, saved.id)

    def test_find_all_filters_by_transcription(self):
        self.repo.save(AudioRecord(
            id=None, file_path="/a.wav", transcription="Hello world",
            conversation_context=None, voice_name="v1", created_at=datetime.now(timezone.utc),
        ))
        self.repo.save(AudioRecord(
            id=None, file_path="/b.wav", transcription="Goodbye world",
            conversation_context=None, voice_name="v2", created_at=datetime.now(timezone.utc),
        ))

        results = self.repo.find_all(transcription="Hello")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].file_path, "/a.wav")

    def test_find_all_filters_by_conversation_context(self):
        self.repo.save(AudioRecord(
            id=None, file_path="/a.wav", transcription="Hi",
            conversation_context="Math class", voice_name="v1",
            created_at=datetime.now(timezone.utc),
        ))
        self.repo.save(AudioRecord(
            id=None, file_path="/b.wav", transcription="Hi",
            conversation_context="History class", voice_name="v2",
            created_at=datetime.now(timezone.utc),
        ))

        results = self.repo.find_all(conversation_context="Math")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].file_path, "/a.wav")

    def test_find_all_filters_by_voice_name(self):
        self.repo.save(AudioRecord(
            id=None, file_path="/a.wav", transcription="Hi",
            conversation_context=None, voice_name="voice-A",
            created_at=datetime.now(timezone.utc),
        ))
        self.repo.save(AudioRecord(
            id=None, file_path="/b.wav", transcription="Hi",
            conversation_context=None, voice_name="voice-B",
            created_at=datetime.now(timezone.utc),
        ))

        results = self.repo.find_all(voice_name="voice-A")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].file_path, "/a.wav")

    def test_find_all_returns_empty_when_no_match(self):
        results = self.repo.find_all(transcription="nonexistent")
        self.assertEqual(results, [])

    def test_find_all_orders_by_created_at_desc(self):
        from datetime import timedelta
        now = datetime.now(timezone.utc)
        older = self.repo.save(AudioRecord(
            id=None, file_path="/old.wav", transcription="Old",
            conversation_context=None, voice_name="v",
            created_at=now - timedelta(hours=1),
        ))
        newer = self.repo.save(AudioRecord(
            id=None, file_path="/new.wav", transcription="New",
            conversation_context=None, voice_name="v",
            created_at=now,
        ))

        results = self.repo.find_all()
        self.assertEqual(results[0].id, newer.id)
        self.assertEqual(results[1].id, older.id)

    def test_save_persists_multiple_records(self):
        self.repo.save(AudioRecord(
            id=None, file_path="/a.wav", transcription="A",
            conversation_context=None, voice_name="v",
            created_at=datetime.now(timezone.utc),
        ))
        self.repo.save(AudioRecord(
            id=None, file_path="/b.wav", transcription="B",
            conversation_context=None, voice_name="v",
            created_at=datetime.now(timezone.utc),
        ))
        self.assertEqual(len(self.repo.find_all()), 2)


if __name__ == "__main__":
    unittest.main()
