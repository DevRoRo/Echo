# Hexagonal Architecture Analysis: Echo

## Overall Assessment

The codebase demonstrates the **intent** of hexagonal architecture (ports and adapters) with a `core/` directory for business logic and an `adapters/` directory for external integrations. However, several significant deviations from the pattern undermine the architecture's goals of testability, interchangeability, and separation of concerns.

---

## Critical Flaws

### 1. Missing Inbound (Driving) Ports

The architecture defines **only outbound (driven) ports** — `TextGenerationPort`, `AudioGenerationPort`, `AudioStoragePort`. There are **zero inbound (driving) port interfaces**.

In proper hexagonal architecture:
- **Inbound ports** are abstract interfaces in the core that driving adapters (e.g., the HTTP API) depend on.
- The use cases should *implement* these inbound port interfaces.

**File:** `core/ports.py`

**Impact:** `api_router.py` imports and depends directly on concrete use case classes (`from core.use_cases import GenerateTestAudioUseCase`). This couples the driving adapter to a concrete implementation, violating the Dependency Inversion Principle. Swapping the use-case implementation is impossible without modifying the API adapter.

---

### 2. Type-Signature Mismatch in `GeminiAdapter.generate_text`

**Port contract** (`core/ports.py:6`):
```python
def generate_text(self, prompt: str, word_count: int, conversation_context: str) -> str:
```

**Adapter implementation** (`adapters/gemini_adapter.py:10`):
```python
def generate_text(self, prompt: str, word_count: str) -> str:
```

Two violations:
- `word_count` typed as `str` instead of `int` — inconsistent with the port.
- **`conversation_context` parameter is completely absent** — the adapter silently drops a parameter the port contract requires. Python's duck-typing won't catch this at compile time, but any caller that respects the port interface will break at runtime when swapping adapters.

---

### 3. `GCSStorageAdapter` Does Not Implement the Port It Claims

`AudioStoragePort` defines exactly one method:
```python
def save_base64(self, base64_string: str) -> str:
```

`GCSStorageAdapter` (which subclasses `AudioStoragePort`) does **not** have a `save_base64` method. Instead it exposes:
- `upload_ai_audio(audio_bytes: bytes, prefix: str)`
- `generate_signed_upload_url(file_extension: str, ...)`
- `delete_audio(filename: str)`

**File:** `adapters/google_storage_adapter.py`

**Impact:** `GCSStorageAdapter` is not a valid drop-in replacement for `AudioStoragePort`. It cannot be used interchangeably with `LocalFileSystemStorageAdapter`. It is never imported or wired anywhere — effectively dead code from the architecture's perspective.

---

### 4. `api_router.py` Is Both Driving Adapter and Composition Root

Dependency wiring belongs in the **composition root** (typically `main.py`). Instead, `api_router.py` directly instantiates concrete adapters:

```python
gemini_adapter = GeminiAdapter()
local_storage = LocalFileSystemStorageAdapter()
```

**File:** `adapters/api_router.py:30-31`, `44-45`

**Impact:**
- Prevents swapping adapters without modifying endpoint code (e.g., switching to GCS storage or a different LLM provider).
- Creates tight coupling between the HTTP layer and concrete infrastructure.
- Violates the principle that the composition root should be the *only* place where wiring happens.

---

### 5. Single Adapter Fulfilling Two Roles

`GeminiAdapter` implements both `AudioGenerationPort` and `TextGenerationPort`. It is then **passed twice** as both `text_generator` and `audio_generator`:

```python
use_case = GenerateConversationalAudioUseCase(
    text_generator=gemini_adapter,
    audio_generator=gemini_adapter,   # same object
    storage=local_storage
)
```

**File:** `adapters/api_router.py:49-52`

**Impact:** Violates the **Single Responsibility Principle**. Text-generation and audio-generation are conceptually distinct concerns with potentially different configuration, rate limiting, and error-handling requirements. Using a single object for both creates hidden coupling and prevents independent evolution.

---

### 6. Use Case Violates Port Contract at Call Site

At `core/use_cases.py:25`:
```python
ai_response_text = self.text_generator.generate_text(prompt, word_count)
```

The port `TextGenerationPort.generate_text` takes **three parameters** (`prompt`, `word_count`, `conversation_context`), but the use case passes only **two**.

**Impact:** This works coincidentally because `GeminiAdapter.generate_text` also accepts only two parameters. A different implementation of `TextGenerationPort` expecting three arguments would crash at runtime. The use case should either pass `conversation_context` or the port signature should be revised.

---

### 7. Dead Parameter in `GenerateTestAudioUseCase`

```python
def execute(self, prompt: str, voice_name: str, conversation_context: str) -> str:
```

**File:** `core/use_cases.py:50`

`conversation_context` is accepted but **never used** in the method body. This is dead code and signals confusion about the use case's contract.

---

## Medium-Severity Issues

### 8. No Tests

Hexagonal architecture is valued in part because it enables testing business logic in isolation — ports can be mocked to test use cases without infrastructure. There are zero test files in the project.

**Impact:** Neither use case can be unit-tested without spinning up actual adapters. The type mismatches described above remain undetected.

---

### 9. `LocalFileSystemStorageAdapter` Hardcodes WAV Headers

```python
with wave.open(filepath, "wb") as file:
    file.setnchannels(1)
    file.setsampwidth(2)
    file.setframerate(24000)
    file.writeframes(audio_bytes)
```

**File:** `adapters/storage_adapter.py:18-23`

**Impact:** The adapter assumes the base64-decoded bytes are raw PCM audio data. The Gemini TTS adapter may return encoded audio (MP3, etc.). This mismatch would produce corrupted or unplayable audio files.

---

### 10. No Domain Models / Entities

The core layer contains only ports and use cases — no domain models or value objects. While not strictly required, the absence of domain entities suggests anemic business logic that may become difficult to manage as complexity grows.

---

## Minor Issues

### 11. Missing `__init__.py` Files

No `__init__.py` files exist in either `core/` or `adapters/`. Python 3.3+ supports implicit namespace packages, but explicit `__init__.py` files are a best practice for reliable import behavior and tooling compatibility.

---

## Summary Table

| # | Violation | Severity | File(s) |
|---|---|---|---|
| 1 | Missing inbound (driving) ports | **Critical** | `core/ports.py` |
| 2 | Port/adapter type-signature mismatch | **High** | `core/ports.py:6`, `adapters/gemini_adapter.py:10` |
| 3 | Adapter not implementing its port interface | **High** | `adapters/google_storage_adapter.py` |
| 4 | Dependency wiring in wrong layer (not composition root) | **High** | `adapters/api_router.py:30-31,44-45` |
| 5 | Single adapter serving two ports (SRP violation) | **Medium** | `adapters/gemini_adapter.py`, `adapters/api_router.py:49-52` |
| 6 | Use case violating port contract at call site | **High** | `core/use_cases.py:25` |
| 7 | Dead parameter in use case | **Low** | `core/use_cases.py:50` |
| 8 | No tests | **Medium** | — |
| 9 | Hardcoded audio format assumptions | **Medium** | `adapters/storage_adapter.py:18-23` |
| 10 | No domain models/entities | **Low** | `core/` |
| 11 | Missing `__init__.py` files | **Low** | `core/`, `adapters/` |

---

## Recommended Fixes

1. **Add inbound port interfaces** in `core/ports.py` (e.g., `class GenerateConversationalAudioPort(ABC)`) and have the use cases implement them so the API adapter depends on abstractions.

2. **Fix `GeminiAdapter.generate_text`** to match the port signature: accept `conversation_context: str` and `word_count: int`.

3. **Make `GCSStorageAdapter` truly implement `AudioStoragePort`** with a `save_base64` method, or remove it from the codebase if it serves a different purpose.

4. **Move all dependency instantiation to `main.py`** and inject adapters into a factory or use FastAPI's dependency-override pattern.

5. **Split `GeminiAdapter`** into separate `GeminiTextAdapter` and `GeminiTTSAdapter` classes.

6. **Fix the missing `conversation_context` argument** in `GenerateConversationalAudioUseCase.execute` by either passing it through or removing it from the port.

7. **Remove the dead `conversation_context` parameter** from `GenerateTestAudioUseCase.execute`.

8. **Write unit tests** for both use cases by mocking the port interfaces.

9. **Add `__init__.py` files** to both `core/` and `adapters/` packages.

10. **Detect the actual audio format** from Gemini's response metadata instead of hardcoding WAV parameters.
