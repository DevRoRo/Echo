import json
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Integer, String, Text, create_engine
from sqlalchemy.orm import Session

from core.ports import (
    LtiSession,
    LtiSessionRepositoryPort,
    PlatformRegistration,
    PlatformRepositoryPort,
)

from .audio_record_repository import Base


class PlatformRegistrationModel(Base):
    __tablename__ = "lti_registrations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    issuer = Column(String(512), unique=True, nullable=False)
    client_id = Column(String(256), nullable=False)
    auth_login_url = Column(String(512), nullable=False)
    auth_token_url = Column(String(512), nullable=False)
    auth_keyset_url = Column(String(512), nullable=False)
    deployment_ids = Column(Text, nullable=False)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)


class LtiSessionModel(Base):
    __tablename__ = "lti_sessions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    nonce = Column(String(256), unique=True, nullable=False)
    target_link_uri = Column(String(512), nullable=False)
    created_at = Column(DateTime, nullable=False)
    expires_at = Column(DateTime, nullable=False)


class SQLitePlatformRepository(PlatformRepositoryPort):
    def __init__(self, engine):
        self.engine = engine

    def _to_domain(self, model: PlatformRegistrationModel) -> PlatformRegistration:
        return PlatformRegistration(
            id=model.id,
            issuer=model.issuer,
            client_id=model.client_id,
            auth_login_url=model.auth_login_url,
            auth_token_url=model.auth_token_url,
            auth_keyset_url=model.auth_keyset_url,
            deployment_ids=json.loads(model.deployment_ids),
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    def save(self, platform: PlatformRegistration) -> PlatformRegistration:
        now = datetime.now(timezone.utc)
        with Session(self.engine) as session:
            existing = session.query(PlatformRegistrationModel).filter_by(issuer=platform.issuer).first()
            if existing:
                existing.client_id = platform.client_id
                existing.auth_login_url = platform.auth_login_url
                existing.auth_token_url = platform.auth_token_url
                existing.auth_keyset_url = platform.auth_keyset_url
                existing.deployment_ids = json.dumps(platform.deployment_ids)
                existing.updated_at = now
                session.commit()
                session.refresh(existing)
                return self._to_domain(existing)
            else:
                model = PlatformRegistrationModel(
                    issuer=platform.issuer,
                    client_id=platform.client_id,
                    auth_login_url=platform.auth_login_url,
                    auth_token_url=platform.auth_token_url,
                    auth_keyset_url=platform.auth_keyset_url,
                    deployment_ids=json.dumps(platform.deployment_ids),
                    created_at=now,
                    updated_at=now,
                )
                session.add(model)
                session.commit()
                session.refresh(model)
                return self._to_domain(model)

    def find_by_issuer(self, issuer: str) -> PlatformRegistration | None:
        with Session(self.engine) as session:
            model = session.query(PlatformRegistrationModel).filter_by(issuer=issuer).first()
            if model is None:
                return None
            return self._to_domain(model)

    def find_by_id(self, platform_id: int) -> PlatformRegistration | None:
        with Session(self.engine) as session:
            model = session.query(PlatformRegistrationModel).filter_by(id=platform_id).first()
            if model is None:
                return None
            return self._to_domain(model)

    def find_all(self) -> list[PlatformRegistration]:
        with Session(self.engine) as session:
            models = session.query(PlatformRegistrationModel).order_by(PlatformRegistrationModel.created_at.desc()).all()
            return [self._to_domain(m) for m in models]

    def delete_by_id(self, platform_id: int) -> PlatformRegistration | None:
        with Session(self.engine) as session:
            model = session.query(PlatformRegistrationModel).filter_by(id=platform_id).first()
            if model is None:
                return None
            record = self._to_domain(model)
            session.delete(model)
            session.commit()
            return record


class SQLiteLtiSessionRepository(LtiSessionRepositoryPort):
    def __init__(self, engine):
        self.engine = engine

    def _to_domain(self, model: LtiSessionModel) -> LtiSession:
        return LtiSession(
            id=model.id,
            nonce=model.nonce,
            target_link_uri=model.target_link_uri,
            created_at=model.created_at,
            expires_at=model.expires_at,
        )

    def save(self, session: LtiSession) -> LtiSession:
        model = LtiSessionModel(
            nonce=session.nonce,
            target_link_uri=session.target_link_uri,
            created_at=session.created_at,
            expires_at=session.expires_at,
        )
        with Session(self.engine) as db_session:
            db_session.add(model)
            db_session.commit()
            db_session.refresh(model)
            return self._to_domain(model)

    def find_by_nonce(self, nonce: str) -> LtiSession | None:
        with Session(self.engine) as db_session:
            model = db_session.query(LtiSessionModel).filter_by(nonce=nonce).first()
            if model is None:
                return None
            return self._to_domain(model)

    def delete_by_id(self, session_id: int) -> None:
        with Session(self.engine) as db_session:
            model = db_session.query(LtiSessionModel).filter_by(id=session_id).first()
            if model:
                db_session.delete(model)
                db_session.commit()

    def clean_expired(self) -> int:
        with Session(self.engine) as db_session:
            now = datetime.now(timezone.utc)
            deleted = db_session.query(LtiSessionModel).filter(LtiSessionModel.expires_at < now).delete()
            db_session.commit()
            return deleted
