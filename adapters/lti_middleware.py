from jwt import decode as jwt_decode, InvalidTokenError

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from adapters.lti_key_manager import LtiKeyManager


SKIP_PATHS = {"/", "/docs", "/openapi.json", "/redoc"}
SKIP_PREFIXES = {"/lti/", "/temp_audio/"}


class LTIAuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        if path in SKIP_PATHS:
            return await call_next(request)
        for prefix in SKIP_PREFIXES:
            if path.startswith(prefix):
                return await call_next(request)

        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return JSONResponse(status_code=401, content={"detail": "Missing or invalid Authorization header"})

        token = auth_header[7:]
        key_manager = LtiKeyManager()
        public_key_pem = key_manager.get_public_key_pem()

        try:
            payload = jwt_decode(token, public_key_pem, algorithms=["RS256"])
        except InvalidTokenError:
            return JSONResponse(status_code=401, content={"detail": "Invalid or expired session token"})

        request.state.lti_user = {
            "sub": payload.get("sub", ""),
            "name": payload.get("name", ""),
            "email": payload.get("email", ""),
            "roles": payload.get("roles", []),
            "course_id": payload.get("course_id", ""),
            "course_title": payload.get("course_title", ""),
            "resource_link_id": payload.get("resource_link_id", ""),
        }

        return await call_next(request)
