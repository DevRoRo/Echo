from pydantic_settings import BaseSettings


class LTISettings(BaseSettings):
    tool_name: str = "Echo"
    tool_description: str = "AI Audio Generation for Moodle"
    launch_url: str = "http://localhost:8000/lti/launch"
    login_url: str = "http://localhost:8000/lti/login"
    jwks_url: str = "http://localhost:8000/lti/jwks"
    config_url: str = "http://localhost:8000/lti/config.json"
    default_redirect: str = "http://localhost:3000/lti/launch"
    keys_dir: str = "keys"
    session_token_expiry_seconds: int = 3600

    model_config = {"env_prefix": "LTI_"}
