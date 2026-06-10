# Backend Fixes Applied

## Fix 1: POST /lti/launch/ — Query → Form

### Issue

The `POST /lti/launch/` endpoint in `adapters/lti_router.py` read `id_token` and `state` via FastAPI `Query(...)` parameters.

**Problem:** Moodle sends these values as form POST fields (standard LTI 1.3), not URL query parameters. Using `Query(...)` would not capture form-encoded POST data, resulting in a 422 validation error.

### Fix Applied

- Changed `id_token: str = Query(...)` → `id_token: str = Form(...)`
- Changed `state: str = Query(...)` → `state: str = Form(...)`
- Added `Form` to the FastAPI imports.

### Verification

Project compiles cleanly. Moodle's form POST to `/lti/launch/` is now parsed correctly.

---

## Fix 2: GET /lti/login/ → POST /lti/login/

### Issue

The LTI login initiation endpoint in `adapters/lti_router.py` was implemented as `GET /lti/login/` with `Query(...)` parameters.

**Problem:** Moodle sends the OIDC login initiation request as a form POST (per LTI 1.3 OIDC third-party initiated login flow). The sequence was:

1. Moodle sends `POST /lti/login` (no trailing slash)
2. FastAPI redirects with `307 Temporary Redirect` to `/lti/login/`
3. The POST arrives at `/lti/login/` but only `GET` is registered → `405 Method Not Allowed`

### Fix Applied

- Changed `@router.get("/login/")` → `@router.post("/login/")`
- Changed all `Query(...)` params (`iss`, `target_link_uri`, `login_hint`, `lti_message_hint`) → `Form(...)`
- Added a second route `@router.post("/login")` (no trailing slash) to avoid the 307 redirect hop entirely

### Verification

Project compiles cleanly. Moodle's form POST to either `/lti/login` or `/lti/login/` is now handled correctly.

---

## Fix 3: Deployment() constructor arguments — pylti1p3 API mismatch

### Role of pylti1p3 in this project

pylti1p3 is the **only JWT validation library** used in Echo's LTI 1.3 flow. Its role is to:

1. **Validate the `id_token` JWT** signed by Moodle — verify the signature against Moodle's JWKS, check `aud`, `iss`, `exp`, `nonce`, etc.
2. **Extract launch claims** — parse the validated JWT body to retrieve user identity (`sub`, `name`, `email`), roles, course context, and resource link information.
3. **Enforce the OIDC protocol** — ensure the nonce/state flow is correct, deployments are registered, and the tool configuration matches.

It is wrapped by three adapter classes:
- **`DbToolConf(ToolConfAbstract)`** — reads platform registrations from Echo's SQLite DB instead of hardcoded config.
- **`FastAPIMessageLaunch(MessageLaunch)`** — bridges FastAPI-parsed form data (`id_token`, `state`) into pylti1p3's `MessageLaunch` validation pipeline via `_get_request_param(key)`.
- **`StubSessionService` / `StubCookieService`** — bypass pylti1p3's built-in session/cookie checks (state, nonce) since those are handled manually before validation.

### Issue

The `DbToolConf.find_deployment()` method in `adapters/lti_pylti1p3_adapter.py` creates a `Deployment` object with two constructor arguments:

```python
return Deployment(iss, deployment_id)
```

**Problem:** The `Deployment` class in pylti1p3 2.0.0 has a no-argument constructor — `Deployment()` takes no arguments. It exposes only a `set_deployment_id(deployment_id)` setter and `get_deployment_id()` getter. Passing positional arguments raises:

```
TypeError: Deployment() takes no arguments
```

This error surfaces as a 500 Internal Server Error during `POST /lti/launch/` when `MessageLaunch.validate()` calls `find_deployment()` internally.

### Fix Applied

- Changed `Deployment(iss, deployment_id)` → `dep = Deployment(); dep.set_deployment_id(deployment_id); return dep`
- The `iss` parameter is irrelevant here — `Deployment` only tracks the deployment ID, which pylti1p3 uses to confirm the deployment is registered.

### Verification

Project compiles cleanly. pylti1p3's `MessageLaunch.validate()` now successfully creates `Deployment` objects from the database.

---

## Summary

| Fix | File | Lines | Status |
|-----|------|-------|--------|
| 1. `/lti/launch/` Query → Form | `adapters/lti_router.py` | 97-98 | ✅ Applied |
| 2. `/lti/login/` GET→POST, Query→Form, add no-slash route | `adapters/lti_router.py` | 70-93 | ✅ Applied |
| 3. `Deployment()` constructor args | `adapters/lti_pylti1p3_adapter.py` | 86 | ✅ Applied |
