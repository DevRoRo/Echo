from fastapi import APIRouter, Depends, Form, HTTPException, Query
from fastapi.responses import JSONResponse, RedirectResponse
from pydantic import BaseModel

from core.ports import PlatformRegistration
from core.lti_use_cases import (
    DeletePlatformUseCase,
    InitiateLoginUseCase,
    ListPlatformsUseCase,
    RegisterPlatformUseCase,
    ValidateLaunchUseCase,
)
from adapters.dependencies import (
    get_delete_platform_use_case,
    get_initiate_login_use_case,
    get_list_platforms_use_case,
    get_register_platform_use_case,
    get_validate_launch_use_case,
)
from adapters.lti_key_manager import LtiKeyManager
from config.lti_settings import LTISettings

router = APIRouter(prefix="/lti")


class RegisterPlatformRequest(BaseModel):
    issuer: str
    client_id: str
    auth_login_url: str
    auth_token_url: str
    auth_keyset_url: str
    deployment_ids: list[str]


class PlatformResponse(BaseModel):
    id: int
    issuer: str
    client_id: str
    auth_login_url: str
    auth_token_url: str
    auth_keyset_url: str
    deployment_ids: list[str]


@router.get("/config.json")
async def lti_config():
    settings = LTISettings()
    return {
        "title": settings.tool_name,
        "description": settings.tool_description,
        "target_link_uri": settings.launch_url,
        "oidc_initiation_url": settings.login_url,
        "redirect_uris": [settings.default_redirect],
        "claims": ["sub", "name", "email", "roles"],
        "messages": [
            {
                "type": "LtiResourceLinkRequest",
                "target_link_uri": settings.launch_url,
                "label": "Echo Audio",
            }
        ],
    }


@router.get("/jwks")
async def lti_jwks():
    key_manager = LtiKeyManager()
    return JSONResponse(content=key_manager.get_jwks())


@router.post("/login")
@router.post("/login/")
async def lti_login(
    iss: str = Form(...),
    target_link_uri: str = Form(...),
    login_hint: str = Form(...),
    lti_message_hint: str = Form(default=""),
    use_case: InitiateLoginUseCase = Depends(get_initiate_login_use_case),
):
    try:
        result = use_case.execute(
            issuer=iss,
            target_link_uri=target_link_uri,
            login_hint=login_hint,
            lti_message_hint=lti_message_hint,
        )
        return RedirectResponse(url=result["redirect_url"])
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/launch/")
async def lti_launch(
    id_token: str = Form(...),
    state: str = Form(...),
    use_case: ValidateLaunchUseCase = Depends(get_validate_launch_use_case),
):
    try:
        result = use_case.execute(id_token=id_token, state=state)
        settings = LTISettings()
        redirect = f"{settings.default_redirect}?session_token={result['session_token']}"
        print(redirect)
        return RedirectResponse(url=redirect)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/register/")
async def register_platform(
    request: RegisterPlatformRequest,
    use_case: RegisterPlatformUseCase = Depends(get_register_platform_use_case),
):
    try:
        platform = PlatformRegistration(
            id=None,
            issuer=request.issuer,
            client_id=request.client_id,
            auth_login_url=request.auth_login_url,
            auth_token_url=request.auth_token_url,
            auth_keyset_url=request.auth_keyset_url,
            deployment_ids=request.deployment_ids,
            created_at=None,
            updated_at=None,
        )
        saved = use_case.execute(platform)
        return PlatformResponse(
            id=saved.id,
            issuer=saved.issuer,
            client_id=saved.client_id,
            auth_login_url=saved.auth_login_url,
            auth_token_url=saved.auth_token_url,
            auth_keyset_url=saved.auth_keyset_url,
            deployment_ids=saved.deployment_ids,
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/registrations/")
async def list_platforms(
    use_case: ListPlatformsUseCase = Depends(get_list_platforms_use_case),
):
    try:
        platforms = use_case.execute()
        return [
            PlatformResponse(
                id=p.id,
                issuer=p.issuer,
                client_id=p.client_id,
                auth_login_url=p.auth_login_url,
                auth_token_url=p.auth_token_url,
                auth_keyset_url=p.auth_keyset_url,
                deployment_ids=p.deployment_ids,
            )
            for p in platforms
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/registrations/{platform_id}")
async def delete_platform(
    platform_id: int,
    use_case: DeletePlatformUseCase = Depends(get_delete_platform_use_case),
):
    try:
        deleted = use_case.execute(platform_id)
        return PlatformResponse(
            id=deleted.id,
            issuer=deleted.issuer,
            client_id=deleted.client_id,
            auth_login_url=deleted.auth_login_url,
            auth_token_url=deleted.auth_token_url,
            auth_keyset_url=deleted.auth_keyset_url,
            deployment_ids=deleted.deployment_ids,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
