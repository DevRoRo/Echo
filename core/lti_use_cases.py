import uuid
from datetime import datetime, timedelta, timezone

from core.ports import (
    DeletePlatformUseCasePort,
    InitiateLoginUseCasePort,
    ListPlatformsUseCasePort,
    LtiSession,
    LtiSessionRepositoryPort,
    PlatformRegistration,
    PlatformRepositoryPort,
    RegisterPlatformUseCasePort,
    ValidateLaunchUseCasePort,
)

from adapters.lti_key_manager import LtiKeyManager
from adapters.lti_pylti1p3_adapter import DbToolConf, FastAPIMessageLaunch
from config.lti_settings import LTISettings


class RegisterPlatformUseCase(RegisterPlatformUseCasePort):
    def __init__(self, repository: PlatformRepositoryPort):
        self.repository = repository

    def execute(self, platform: PlatformRegistration) -> PlatformRegistration:
        if not platform.issuer.strip():
            raise ValueError("issuer cannot be empty.")
        if not platform.client_id.strip():
            raise ValueError("client_id cannot be empty.")
        return self.repository.save(platform)


class ListPlatformsUseCase(ListPlatformsUseCasePort):
    def __init__(self, repository: PlatformRepositoryPort):
        self.repository = repository

    def execute(self) -> list[PlatformRegistration]:
        return self.repository.find_all()


class DeletePlatformUseCase(DeletePlatformUseCasePort):
    def __init__(self, repository: PlatformRepositoryPort):
        self.repository = repository

    def execute(self, platform_id: int) -> PlatformRegistration:
        platform = self.repository.find_by_id(platform_id)
        if platform is None:
            raise ValueError(f"Platform with id {platform_id} not found.")
        return self.repository.delete_by_id(platform_id)


class InitiateLoginUseCase(InitiateLoginUseCasePort):
    def __init__(
        self,
        platform_repo: PlatformRepositoryPort,
        session_repo: LtiSessionRepositoryPort,
        settings: LTISettings | None = None,
    ):
        self.platform_repo = platform_repo
        self.session_repo = session_repo
        self.settings = settings or LTISettings()

    def execute(self, issuer: str, target_link_uri: str, login_hint: str, lti_message_hint: str = "") -> dict:
        platform = self.platform_repo.find_by_issuer(issuer)
        if platform is None:
            raise ValueError(f"No platform registered for issuer: {issuer}")

        nonce = uuid.uuid4().hex
        now = datetime.now(timezone.utc)

        session = LtiSession(
            id=None,
            nonce=nonce,
            target_link_uri=target_link_uri,
            created_at=now,
            expires_at=now + timedelta(minutes=5),
        )
        self.session_repo.save(session)

        from urllib.parse import urlencode, urlparse, parse_qs, urlunparse

        parsed = urlparse(platform.auth_login_url)
        params = parse_qs(parsed.query, keep_blank_values=True)
        params.update({
            "response_type": ["id_token"],
            "scope": ["openid"],
            "response_mode": ["form_post"],
            "client_id": [platform.client_id],
            "redirect_uri": [self.settings.launch_url],
            "state": [nonce],
            "nonce": [uuid.uuid4().hex],
            "login_hint": [login_hint],
            "lti_message_hint": [lti_message_hint],
        })
        new_query = urlencode(params, doseq=True)
        redirect_url = urlunparse(parsed._replace(query=new_query))

        return {"redirect_url": redirect_url, "state": nonce}


class ValidateLaunchUseCase(ValidateLaunchUseCasePort):
    def __init__(
        self,
        platform_repo: PlatformRepositoryPort,
        session_repo: LtiSessionRepositoryPort,
        key_manager: LtiKeyManager,
        settings: LTISettings | None = None,
    ):
        self.platform_repo = platform_repo
        self.session_repo = session_repo
        self.key_manager = key_manager
        self.settings = settings or LTISettings()

    def execute(self, id_token: str, state: str) -> dict:
        lti_session = self.session_repo.find_by_nonce(state)
        if lti_session is None:
            raise ValueError("Invalid state: session not found.")
        if lti_session.expires_at.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
            raise ValueError("Session has expired.")

        tool_conf = DbToolConf(
            platform_repo=self.platform_repo,
            private_key=self.key_manager.get_private_key_pem(),
            public_key=self.key_manager.get_public_key_pem(),
        )

        launch = FastAPIMessageLaunch(
            id_token=id_token,
            state=state,
            tool_config=tool_conf,
        )
        launch.validate()

        jwt_body = launch.get_launch_data()
        user_id = jwt_body.get("sub", "")
        name = jwt_body.get("name", "")
        email = jwt_body.get("email", "")
        roles = jwt_body.get(
            "https://purl.imsglobal.org/spec/lti/claim/roles", []
        )
        context = jwt_body.get(
            "https://purl.imsglobal.org/spec/lti/claim/context", {}
        )
        resource_link = jwt_body.get(
            "https://purl.imsglobal.org/spec/lti/claim/resource_link", {}
        )

        self.session_repo.delete_by_id(lti_session.id)

        session_token = self.key_manager.get_private_key_pem()

        from jwt import encode as jwt_encode

        token_payload = {
            "sub": user_id,
            "name": name,
            "email": email,
            "roles": roles,
            "course_id": context.get("id", ""),
            "course_title": context.get("title", ""),
            "resource_link_id": resource_link.get("id", ""),
            "exp": datetime.now(timezone.utc) + timedelta(seconds=self.settings.session_token_expiry_seconds),
        }
        private_key = self.key_manager.get_private_key_pem()
        token = jwt_encode(token_payload, private_key, algorithm="RS256")

        return {
            "session_token": token,
            "user_id": user_id,
            "name": name,
            "roles": roles,
            "course_id": context.get("id", ""),
            "course_title": context.get("title", ""),
            "target_link_uri": lti_session.target_link_uri,
        }
