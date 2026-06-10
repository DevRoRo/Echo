from typing import Any

from pylti1p3.cookie import CookieService
from pylti1p3.deployment import Deployment
from pylti1p3.message_launch import MessageLaunch
from pylti1p3.registration import Registration
from pylti1p3.request import Request
from pylti1p3.session import SessionService
from pylti1p3.tool_config import ToolConfAbstract

from core.ports import PlatformRegistration, PlatformRepositoryPort


class _StubRequest(Request):
    def is_secure(self) -> bool:
        return True

    def get_param(self, key: str) -> str:
        return ""

    @property
    def session(self):
        return {}


class StubSessionService(SessionService):
    """Minimal session service — state/nonce validation is handled manually
    before calling FastAPIMessageLaunch.validate()."""

    def __init__(self):
        super().__init__(_StubRequest())

    def check_state_is_valid(self, state: str, id_token_hash: str) -> bool:
        return True

    def check_nonce(self, nonce: str) -> bool:
        return True

    def save_nonce(self, nonce: str) -> None:
        pass


class StubCookieService(CookieService):
    def get_cookie(self, name: str) -> str | None:
        return None

    def set_cookie(self, name: str, value: str | int, exp: int = 3600) -> None:
        pass


class DbToolConf(ToolConfAbstract):
    def __init__(self, platform_repo: PlatformRepositoryPort, private_key: str, public_key: str):
        super().__init__()
        self._platform_repo = platform_repo
        self._private_key = private_key
        self._public_key = public_key
        self.set_iss_has_one_client("*")

    def _platform_to_registration(self, platform: PlatformRegistration) -> Registration:
        reg = Registration()
        reg.set_issuer(platform.issuer)
        reg.set_client_id(platform.client_id)
        reg.set_auth_login_url(platform.auth_login_url)
        reg.set_auth_token_url(platform.auth_token_url)
        reg.set_key_set_url(platform.auth_keyset_url)
        reg.set_tool_private_key(self._private_key)
        return reg

    def find_registration_by_issuer(self, iss: str, *args, **kwargs) -> Registration:
        platform = self._platform_repo.find_by_issuer(iss)
        if platform is None:
            raise ValueError(f"No platform registration found for issuer: {iss}")
        return self._platform_to_registration(platform)

    def find_registration_by_params(self, iss: str, client_id: str, *args, **kwargs) -> Registration:
        platform = self._platform_repo.find_by_issuer(iss)
        if platform is None:
            raise ValueError(f"No platform registration found for issuer: {iss}")
        return self._platform_to_registration(platform)

    def find_deployment(self, iss: str, deployment_id: str) -> Deployment | None:
        platform = self._platform_repo.find_by_issuer(iss)
        if platform is None:
            return None
        if deployment_id in platform.deployment_ids:
            dep = Deployment()
            dep.set_deployment_id(deployment_id)
            return dep
        return None

    def find_deployment_by_params(self, iss: str, deployment_id: str, client_id: str, *args, **kwargs) -> Deployment | None:
        return self.find_deployment(iss, deployment_id)


class FastAPIMessageLaunch(MessageLaunch):
    def __init__(
        self,
        id_token: str,
        state: str,
        tool_config: ToolConfAbstract,
    ):
        self._params = {"id_token": id_token, "state": state}
        super().__init__(
            request=self,
            tool_config=tool_config,
            session_service=StubSessionService(),
            cookie_service=StubCookieService(),
        )

    def _get_request_param(self, key: str) -> str:
        return self._params[key]
