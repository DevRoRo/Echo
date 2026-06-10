import os
from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String, Text, create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from core.ports import AudioRecord, AudioRecordRepositoryPort

DB_PATH = os.getenv("AUDIO_RECORDS_DB_PATH", "echo.db")


class Base(DeclarativeBase):
    pass


class AudioRecordModel(Base):
    __tablename__ = "audio_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(256), nullable=False)
    file_path = Column(String(512), nullable=False)
    transcription = Column(Text, nullable=False)
    conversation_context = Column(Text, nullable=True)
    voice_name = Column(String(128), nullable=False)
    created_at = Column(DateTime, nullable=False)


class SQLiteAudioRecordRepository(AudioRecordRepositoryPort):
    def __init__(self, db_path: str = DB_PATH):
        self.engine = create_engine(f"sqlite:///{db_path}", echo=False)
        Base.metadata.create_all(self.engine)
        self.SessionLocal = sessionmaker(bind=self.engine)

    def dispose(self):
        self.engine.dispose()

    def _to_domain(self, model: AudioRecordModel) -> AudioRecord:
        return AudioRecord(
            id=model.id,
            name=model.name,
            file_path=model.file_path,
            transcription=model.transcription,
            conversation_context=model.conversation_context,
            voice_name=model.voice_name,
            created_at=model.created_at,
        )

    def save(self, record: AudioRecord) -> AudioRecord:
        model = AudioRecordModel(
            name=record.name,
            file_path=record.file_path,
            transcription=record.transcription,
            conversation_context=record.conversation_context,
            voice_name=record.voice_name,
            created_at=record.created_at,
        )
        with Session(self.engine) as session:
            session.add(model)
            session.commit()
            session.refresh(model)
            return self._to_domain(model)

    def find_by_id(self, record_id: int) -> AudioRecord | None:
        with Session(self.engine) as session:
            model = session.query(AudioRecordModel).filter_by(id=record_id).first()
            if model is None:
                return None
            return self._to_domain(model)

    def delete_by_id(self, record_id: int) -> AudioRecord | None:
        with Session(self.engine) as session:
            model = session.query(AudioRecordModel).filter_by(id=record_id).first()
            if model is None:
                return None
            record = self._to_domain(model)
            session.delete(model)
            session.commit()
            return record

    def find_all(
        self,
        name: str | None = None,
        transcription: str | None = None,
        conversation_context: str | None = None,
        voice_name: str | None = None,
    ) -> list[AudioRecord]:
        with Session(self.engine) as session:
            query = session.query(AudioRecordModel)
            if name:
                query = query.filter(AudioRecordModel.name.ilike(f"%{name}%"))
            if transcription:
                query = query.filter(AudioRecordModel.transcription.ilike(f"%{transcription}%"))
            if conversation_context:
                query = query.filter(AudioRecordModel.conversation_context.ilike(f"%{conversation_context}%"))
            if voice_name:
                query = query.filter(AudioRecordModel.voice_name == voice_name)
            query = query.order_by(AudioRecordModel.created_at.desc())
            return [self._to_domain(m) for m in query.all()]
