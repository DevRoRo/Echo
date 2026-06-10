# Echo LTI Integration — Phase 2

## Overview

Add LTI 1.3 support to the Echo FastAPI backend, enabling Moodle to launch Echo as an external tool. LTI 1.3 is built on OAuth 2.0 + OpenID Connect: Moodle (Platform) sends signed JWTs to Echo (Tool), Echo validates them and issues stateless session tokens for subsequent API requests.

All existing Echo endpoints (`/generate-audio/`, `/ask-professor/`, `/audio-records/`) are placed behind LTI auth middleware, requiring a valid session token.

---

## Implementation Notes

### Initial Error — Mixing Libraries

During implementation I initially fell into the trap of reaching for a second library (`pyjwt` directly) instead of properly adapting `pylti1p3` for FastAPI. The fix: subclass `pylti1p3.message_launch.MessageLaunch` by overriding its single abstract method `_get_request_param(key)` — this bridges FastAPI's parsed form data into pylti1p3 without introducing any direct JWT handling.

### Decision — pylti1p3 Only

| Component | pylti1p3 class | How we use it |
|-----------|----------------|---------------|
| Registration config | `Registration` | Builder pattern to construct from our `PlatformRegistration` domain model |
| Tool config lookup | `ToolConfAbstract` | **Subclass `DbToolConf`** — reads registrations from SQLite |
| JWT validation | `MessageLaunch` | **Subclass `FastAPIMessageLaunch`** — overrides `_get_request_param(key)` to accept parsed `id_token` + `state` directly |
| OIDC state | `CacheDataStorage` | pylti1p3's built-in cache for nonce/state storage during login flow |
| Key management | `Registration.set_tool_private_key()` | Our `LtiKeyManager` generates RSA keys via `cryptography`; pylti1p3 handles JWK formatting |

`OIDCLogin` is **not used** — the login flow (generate state → redirect to Moodle) is implemented manually since `OIDCLogin` is coupled to Flask cookie services. This is simpler and more FastAPI-native.

---

## Hexagonal Architecture Map

```
┌────────────────────────────────────────────────────────┐
│                    Driving Adapters                     │
│  lti_router.py   lti_middleware.py   api_router.py     │
├────────────────────────────────────────────────────────┤
│                   Inbound Ports (core)                  │
│  RegisterPlatformUseCasePort                            │
│  ListPlatformsUseCasePort                               │
│  DeletePlatformUseCasePort                              │
│  InitiateLoginUseCasePort                               │
│  ValidateLaunchUseCasePort                              │
├────────────────────────────────────────────────────────┤
│                    Use Cases (core)                      │
│  RegisterPlatformUseCase                                │
│  ListPlatformsUseCase                                   │
│  DeletePlatformUseCase                                  │
│  InitiateLoginUseCase                                   │
│  ValidateLaunchUseCase                                  │
├────────────────────────────────────────────────────────┤
│                   Outbound Ports (core)                  │
│  PlatformRepositoryPort                                 │
│  LtiSessionRepositoryPort                               │
├────────────────────────────────────────────────────────┤
│                    Driven Adapters                       │
│  SQLitePlatformRepository                               │
│  SQLiteLtiSessionRepository                             │
│  LtiKeyManager (RSA + JWKS)                             │
│  echo.db (SQLite)                                       │
└────────────────────────────────────────────────────────┘
```

---

## Domain Models & Ports

### Value Objects (`core/ports.py`)

```python
@dataclass
class PlatformRegistration:
    id: int | None
    issuer: str
    client_id: str
    auth_login_url: str
    auth_token_url: str
    auth_keyset_url: str
    deployment_ids: list[str]
    created_at: datetime | None
    updated_at: datetime | None

@dataclass
class LtiSession:
    id: int | None
    nonce: str
    target_link_uri: str
    created_at: datetime | None
    expires_at: datetime | None
```

### Outbound Ports (`core/ports.py`)

| Port | Methods |
|------|---------|
| `PlatformRepositoryPort` | `save()`, `find_by_issuer()`, `find_by_id()`, `find_all()`, `delete_by_id()` |
| `LtiSessionRepositoryPort` | `save()`, `find_by_nonce()`, `delete_by_id()`, `clean_expired()` |

### Inbound Ports (`core/ports.py`)

| Port | execute() signature |
|------|-------------------|
| `RegisterPlatformUseCasePort` | `(platform: PlatformRegistration) -> PlatformRegistration` |
| `ListPlatformsUseCasePort` | `() -> list[PlatformRegistration]` |
| `DeletePlatformUseCasePort` | `(platform_id: int) -> PlatformRegistration` |
| `InitiateLoginUseCasePort` | `(issuer, target_link_uri, login_hint, lti_message_hint) -> dict` |
| `ValidateLaunchUseCasePort` | `(id_token: str, state: str) -> dict` |

---

## Use Cases

| Use Case | Location | Logic |
|----------|----------|-------|
| `RegisterPlatformUseCase` | `core/lti_use_cases.py` | Validates fields, saves via `PlatformRepositoryPort` |
| `ListPlatformsUseCase` | `core/lti_use_cases.py` | Delegates to `PlatformRepositoryPort.find_all()` |
| `DeletePlatformUseCase` | `core/lti_use_cases.py` | Finds by ID, raises `ValueError` if not found, deletes |
| `InitiateLoginUseCase` | `core/lti_use_cases.py` | Looks up registration by `issuer`, generates nonce, saves `LtiSession`, returns Moodle's OIDC auth URL |
| `ValidateLaunchUseCase` | `core/lti_use_cases.py` | Validates nonce/session, uses `pylti1p3.MessageLaunch` to verify JWT, extracts user claims, issues stateless session JWT |

---

## LTI Launch Flow

```
Moodle (Platform)                    Echo Backend (Tool)
       │                                    │
       │  1. GET /lti/login/?               │
       │     iss=<moodle_url>               │
       │     target_link_uri=<redirect>     │
       │     login_hint=<user_id>           │
       │──────────────────────────────────►  │
       │                                    │── InitiateLoginUseCase
       │  2. Redirect to Moodle's           │   → Find PlatformRegistration by issuer
       │     OIDC auth endpoint             │   → Generate nonce, save LtiSession
       │     with nonce/state               │   → Return Moodle's auth URL
       │◄──────────────────────────────────  │
       │                                    │
       │  3. User authenticates with Moodle │
       │     (already logged in, seamless)  │
       │                                    │
       │  4. POST /lti/launch/              │
       │     id_token=<JWT>                 │
       │     state=<nonce>                  │
       │──────────────────────────────────►  │
       │                                    │── ValidateLaunchUseCase
       │  5. Redirect to frontend           │   a. Lookup session by nonce
       │     with session_token=<JWT>       │   b. Find PlatformRegistration by iss
       │◄──────────────────────────────────  │   c. pylti1p3 validates JWT signature
       │                                    │   d. Issue stateless session JWT
       │                                    │   e. Delete used LtiSession
       │                                    │
       │  6. Frontend stores session JWT    │
       │     All API calls include:         │
       │     Authorization: Bearer <JWT>    │
       │──────────────────────────────────►  │── LTIAuthMiddleware
       │                                    │   validates JWT signature,
       │                                    │   injects request.state.lti_user
```

### Session Token (Stateless JWT)

After a successful launch, Echo issues a JWT signed with its own RSA private key:

```json
{
  "sub": "<moodle_user_id>",
  "name": "John Doe",
  "email": "john@example.com",
  "roles": ["Instructor"],
  "course_id": "c1",
  "course_title": "Math 101",
  "resource_link_id": "r1",
  "exp": 1718000000
}
```

The middleware validates this JWT on every request using Echo's public key. No DB lookup needed for auth — fully stateless.

---

## Database Tables

### `lti_registrations`

| Column | Type | Constraints |
|--------|------|-------------|
| `id` | Integer | PK, auto-increment |
| `issuer` | String(512) | UNIQUE, NOT NULL |
| `client_id` | String(256) | NOT NULL |
| `auth_login_url` | String(512) | NOT NULL |
| `auth_token_url` | String(512) | NOT NULL |
| `auth_keyset_url` | String(512) | NOT NULL |
| `deployment_ids` | Text (JSON) | NOT NULL |
| `created_at` | DateTime | NOT NULL |
| `updated_at` | DateTime | NOT NULL |

### `lti_sessions`

| Column | Type | Constraints |
|--------|------|-------------|
| `id` | Integer | PK, auto-increment |
| `nonce` | String(256) | UNIQUE, NOT NULL |
| `target_link_uri` | String(512) | NOT NULL |
| `created_at` | DateTime | NOT NULL |
| `expires_at` | DateTime | NOT NULL |

---

## API Endpoints

| Method | Path | Use Case | Auth | Purpose |
|--------|------|----------|------|---------|
| `GET` | `/lti/config.json` | — | None | Tool registration JSON for Moodle |
| `GET` | `/lti/jwks` | — | None | Public keys in JWK format |
| `GET` | `/lti/login/` | `InitiateLoginUseCase` | None | OIDC login initiation |
| `POST` | `/lti/launch/` | `ValidateLaunchUseCase` | None | LTI launch — validates JWT, issues session |
| `POST` | `/lti/register/` | `RegisterPlatformUseCase` | None | Register a Moodle platform |
| `GET` | `/lti/registrations/` | `ListPlatformsUseCase` | None | List registered platforms |
| `DELETE` | `/lti/registrations/{id}` | `DeletePlatformUseCase` | None | Remove a registration |

---

## Auth Middleware

`LTIAuthMiddleware` applies to all routes **except**:
- `/lti/*` — LTI endpoints must be public for OIDC flow
- `/` — Health check
- `/temp_audio/*` — Static audio files (accessible via direct URL)

**Behavior:**
- Checks `Authorization: Bearer <session_jwt>` header
- Validates JWT signature using Echo's RSA public key
- Extracts claims and injects `request.state.lti_user` with `sub`, `name`, `roles`, `course_id`, `course_title`
- Returns `401` on missing, expired, or invalid token

---

## File Manifest

```
Echo/
├── core/
│   ├── ports.py                       # + LTI domain models + ports
│   └── lti_use_cases.py               # NEW: LTI use cases
├── config/
│   └── lti_settings.py                # NEW: LTI configuration
├── adapters/
│   ├── lti_repository.py              # NEW: Platform + Session SQLite repos
│   ├── lti_key_manager.py             # NEW: RSA key generation + JWKS
│   ├── lti_router.py                  # NEW: LTI API endpoints
│   ├── lti_middleware.py              # NEW: Auth middleware
│   └── dependencies.py                # + LTI dependency providers
├── keys/
│   ├── private.key                    # Generated on first run
│   └── public.key                     # Generated on first run
├── main.py                            # + Wire LTI, add middleware
├── requirements.txt                   # + pylti1p3
├── LTI_INTEGRATION.md                 # This file
└── tests/
    ├── test_lti_repository.py         # NEW: Platform + Session repo tests
    ├── test_lti_use_cases.py          # NEW: Use case tests
    └── test_lti_middleware.py         # NEW: Middleware tests
```

---

## Tests

| Test File | Tests |
|-----------|-------|
| `tests/test_lti_repository.py` | PlatformRepository CRUD + find_by_issuer; SessionRepository CRUD + clean_expired + find_by_nonce |
| `tests/test_lti_use_cases.py` | RegisterPlatformUseCase, ListPlatformsUseCase, DeletePlatformUseCase, InitiateLoginUseCase, ValidateLaunchUseCase — all with mocked repositories + mocked pylti1p3 |
| `tests/test_lti_middleware.py` | No token → 401, invalid token → 401, expired token → 401, valid token → passes with lti_user injected |

---

## Moodle Registration Steps (Post-Implementation)

1. Start Echo: `uvicorn main:app`
2. Open `http://localhost:8080` as admin
3. Site administration → Plugins → Activity modules → External tool → Manage tools
4. Configure Echo manually:
   - Tool name: `Echo`
   - Tool URL: `http://localhost:3000`
   - LTI version: `LTI 1.3`
   - Public key type: `Keyset URL`
   - Public keyset: `http://localhost:8000/lti/jwks`
   - Initiate login URL: `http://localhost:8000/lti/login`
   - Redirection URI(s): `http://localhost:3000/lti/launch`
5. Save → Moodle provides: `issuer`, `client_id`, `keyset_url`, `deployment_id`
6. Register in Echo: `POST /lti/register/` with those details
7. Add External tool activity in a course → select Echo
8. Click the Echo link → full LTI launch flow executes
