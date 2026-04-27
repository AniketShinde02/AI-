# Nexus 2.0 — Security Model

**Version:** 1.0  
**Last Updated:** 2025  
**Scope:** Production security architecture for Nexus 2.0 (voice-first AI assistant for Windows power users)  
**Stack:** FastAPI + Supabase + Next.js + Windows Agent + GetStream + Railway + Vercel  

---

## Table of Contents

1. [Threat Model](#1-threat-model)
2. [Authentication & Session Security](#2-authentication--session-security)
3. [Supabase RLS Policies](#3-supabase-rls-policies)
4. [API Security](#4-api-security)
5. [Windows Agent Security](#5-windows-agent-security)
6. [Browser Automation Security](#6-browser-automation-security)
7. [Secret Management](#7-secret-management)
8. [Security Checklist (Pre-Launch)](#8-security-checklist-pre-launch)

---

## 1. Threat Model

Nexus 2.0 presents an unusually broad attack surface: it combines cloud APIs, a local machine agent, browser automation, LLM inference, voice sessions, and payment webhooks. This section documents what we protect against and the residual risk posture.

### 1.1 Assets to Protect

| Asset | Sensitivity | Notes |
|---|---|---|
| User conversation turns | High | Personal, may contain credentials or PII |
| Memory items | High | Long-lived personal context |
| Output documents | High | Research reports, summaries |
| Task / tool run logs | Medium | Contains URLs, file paths, app interactions |
| Supabase service role key | Critical | Full DB bypass if leaked |
| LemonSqueezy webhook secret | High | Used to verify payment events |
| Windows agent token | High | Grants remote code execution on user's machine |
| API keys (LLMs, Deepgram, etc.) | High | Cost exposure and data access |
| User billing state (plan tier) | Medium | Quota enforcement |

### 1.2 Threat Actors

- **Curious users** — attempt to access other users' data through manipulated API calls
- **Automated attackers** — bot traffic, credential stuffing, DDoS
- **Malicious users** — prompt injection, quota abuse, Browser Use SSRF
- **Insider / compromised CI** — secret exfiltration from build pipelines
- **Third-party service compromise** — upstream provider breach affecting Nexus data

### 1.3 Threat Register

#### T1 — Unauthorized Access to User Data (IDOR / Broken Object Level Authorization)

**Attack vector:** User modifies `session_id`, `task_id`, or `memory_id` in an API request to retrieve another user's data.  
**Impact:** Full read/write of any user's conversation history, memory, tasks, and files.  
**Mitigations:**
- Supabase Row Level Security (RLS) on every table, enforcing `user_id = auth.uid()`
- FastAPI endpoint-level ownership checks (defense in depth): before any DB operation, verify the resource's `user_id` matches the authenticated user
- Never expose internal integer IDs in URLs; always use UUIDs

#### T2 — Prompt Injection Attacks

**Attack vector:** User embeds adversarial instructions in voice input or text that cause the LLM to ignore system instructions, exfiltrate data via tool calls, or perform unauthorized actions.  
**Impact:** LLM instructs Browser Use to navigate to attacker-controlled URLs, exfiltrate memory, or execute destructive Windows agent commands.  
**Mitigations:**
- System prompt is never included in user-visible context
- Tool call parameters are validated against a strict schema before dispatch (Pydantic models)
- URLs extracted by LLM responses are validated through SSRF filter before being passed to Browser Use
- Sensitive tool categories (delete, send, purchase) always require explicit human confirmation regardless of LLM instruction
- LLM tool call results are logged in `tool_runs` for audit

#### T3 — Browser Automation Abuse (Quota Bypass)

**Attack vector:** User submits many browser task requests simultaneously to exhaust quota and gain disproportionate compute.  
**Impact:** Service degradation for other users, excessive LLM/Browser Use costs.  
**Mitigations:**
- Per-user rate limit on task creation (30 req/min)
- Inngest job queue with concurrency limits per user (max 2 concurrent browser tasks per user)
- Plan-based daily task quotas enforced in `billing_usage` table
- Tasks in "running" state block new task creation above the concurrent limit

#### T4 — Windows Agent Abuse (Destructive Local Actions)

**Attack vector:** Attacker (or injected LLM instruction) sends commands to the local Windows agent to delete files, exfiltrate data, or modify system settings.  
**Impact:** Data loss on user's machine, malware installation, system compromise.  
**Mitigations:**
- Agent token shared secret required on every request
- `ActionPolicy` module blocks or requires confirmation for all destructive actions
- Registry edits and system32 access are permanently blocked
- All agent commands are logged to backend before execution
- Agent only accepts connections from `127.0.0.1` (loopback only)

#### T5 — API Abuse (DDoS / Credential Stuffing)

**Attack vector:** High-volume requests to auth endpoints (brute-force passwords) or general API endpoints (DDoS).  
**Impact:** Service unavailability, account compromise.  
**Mitigations:**
- Supabase Auth has built-in brute-force protection (CAPTCHA on suspicious patterns)
- slowapi rate limiting: 10 req/min on auth endpoints per IP
- Global rate limit: 1000 req/min per IP
- Railway's edge can be fronted by Cloudflare if needed (optional future hardening)

#### T6 — Token Theft / Session Hijacking

**Attack vector:** Attacker extracts JWT access token or refresh token from client storage.  
**Impact:** Impersonation of user, access to all their data.  
**Mitigations:**
- JWTs are stored in-memory (not localStorage) for the SPA; refresh tokens via httpOnly cookie
- Access tokens expire after 1 hour; refresh tokens after 7 days
- Supabase Auth supports refresh token rotation (each use invalidates the previous)
- HTTPS-only; HSTS header on all endpoints
- Auth cookies have `SameSite=Strict` and `Secure` flags

#### T7 — Webhook Forgery (LemonSqueezy)

**Attack vector:** Attacker sends a crafted POST to `/api/v1/billing/webhook` claiming a subscription was created, upgrading their account for free.  
**Impact:** Unauthorized plan upgrades, revenue loss.  
**Mitigations:**
- Every webhook request includes an `X-Signature` header (HMAC-SHA256 of the body using `LEMONSQUEEZY_WEBHOOK_SECRET`)
- Backend validates signature before any DB writes
- Webhook endpoint rejects any request without a valid signature with a 401
- Idempotency keys prevent replay attacks (track processed webhook event IDs)

#### T8 — SSRF via Browser Automation

**Attack vector:** User (or prompt injection) instructs Browser Use to navigate to `http://169.254.169.254/` (AWS metadata), `http://localhost/`, or internal Railway service URLs to exfiltrate cloud credentials.  
**Impact:** Cloud credential exfiltration, internal service access.  
**Mitigations:**
- All URLs passed to Browser Use are validated through `ssrf_filter()` before dispatch
- Blocked: localhost, 127.x.x.x, 10.x.x.x, 172.16-31.x.x, 192.168.x.x, 169.254.x.x, ::1
- DNS rebinding protection: resolve hostname and check IP against blocklist before connecting

---

## 2. Authentication & Session Security

### 2.1 Supabase Auth Flow

```
User submits email + password
         │
         ▼
Supabase Auth validates credentials
         │
         ├── Success ──▶ Issues: access_token (JWT, 1h TTL)
         │                       refresh_token (opaque, 7d TTL)
         │                       stored in httpOnly cookie (web) or
         │                       in-memory (SPA)
         │
         └── Failure ──▶ 401 with error code
                         (rate-limited to 10 attempts/min per IP)
```

**Access token (JWT):**
- Signed with Supabase project's RS256 private key
- Contains: `sub` (user UUID), `email`, `role`, `aud` ("authenticated"), `exp`, `iat`
- Validated by FastAPI against the Supabase JWKS endpoint

**Refresh token:**
- Opaque random string stored server-side in Supabase's auth schema
- Exchanged for a new access token + new refresh token (rotation)
- Old refresh token is immediately invalidated after use

### 2.2 FastAPI JWT Validation

Install dependencies:
```bash
pip install python-jose[cryptography] httpx
```

JWT validation dependency (place in `backend/core/auth.py`):

```python
import httpx
from fastapi import Header, HTTPException, Depends
from jose import jwt, JWTError
from functools import lru_cache
from sqlalchemy.ext.asyncio import AsyncSession
from backend.core.database import get_db
from backend.models.user import User
import os

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_JWT_SECRET = os.environ["SUPABASE_JWT_SECRET"]  # From Supabase dashboard → Settings → API


@lru_cache(maxsize=1)
def get_jwks() -> dict:
    """Fetch JWKS from Supabase. Cached in-process to avoid repeated HTTP calls."""
    resp = httpx.get(f"{SUPABASE_URL}/auth/v1/.well-known/jwks.json")
    resp.raise_for_status()
    return resp.json()


async def get_current_user(
    authorization: str = Header(...),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Validates Bearer JWT issued by Supabase Auth.
    Returns the corresponding User record or raises HTTP 401.
    """
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header format")

    token = authorization.removeprefix("Bearer ")

    try:
        payload = jwt.decode(
            token,
            SUPABASE_JWT_SECRET,
            algorithms=["HS256"],
            audience="authenticated",
        )
    except JWTError as e:
        raise HTTPException(status_code=401, detail=f"Invalid or expired token: {e}")

    user_id: str = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Token missing subject claim")

    # Load user from DB (ensures user exists and is not soft-deleted)
    user = await db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")

    return user


# Usage in routes:
# @router.get("/sessions")
# async def list_sessions(user: User = Depends(get_current_user)):
#     ...
```

**Alternative: using supabase-py for validation**

```python
from supabase import create_client
import os

supabase = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_ROLE_KEY"])

async def get_current_user_via_supabase(authorization: str = Header(...)) -> dict:
    token = authorization.removeprefix("Bearer ")
    try:
        response = supabase.auth.get_user(token)
        return response.user
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")
```

### 2.3 Refresh Token Rotation

Rotation is handled automatically by Supabase's client SDK. From the frontend:

```typescript
// frontend/lib/supabase.ts
import { createClient } from "@supabase/supabase-js";

export const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
  {
    auth: {
      // Store session in memory for SPA security (not localStorage)
      storage: {
        getItem: (key) => sessionStorage.getItem(key),
        setItem: (key, value) => sessionStorage.setItem(key, value),
        removeItem: (key) => sessionStorage.removeItem(key),
      },
      autoRefreshToken: true,   // SDK auto-refreshes before expiry
      persistSession: true,     // Persists within the tab session
      detectSessionInUrl: true, // For OAuth redirect handling
    },
  }
);
```

For server-rendered Next.js pages, set the JWT in an `httpOnly` cookie via middleware so it is never accessible to JavaScript.

### 2.4 Token Storage Rules

| Context | Access Token Storage | Refresh Token Storage | Rationale |
|---|---|---|---|
| Next.js SPA (CSR pages) | `sessionStorage` (in-memory) | `sessionStorage` | Not persisted to disk; lost on tab close |
| Next.js SSR / middleware | `httpOnly` cookie | `httpOnly` cookie | JS-inaccessible; XSS cannot steal it |
| Backend-to-backend calls | Environment variable / in-process | N/A | Service role key, never user JWT |

**Never:**
- Store tokens in `localStorage` (persists across tabs; exposed to XSS)
- Include tokens in URL query parameters (logged by servers, browsers, CDNs)
- Log tokens in any observability tool (Sentry, Langfuse, Posthog)
- Include the `SUPABASE_SERVICE_ROLE_KEY` in any frontend bundle

### 2.5 OAuth Provider Setup

For Google/GitHub OAuth via Supabase Auth:
- Configure redirect URL to `https://your-vercel-app.vercel.app/auth/callback`
- In Next.js middleware, exchange the OAuth code for a session server-side
- Never expose the OAuth client secret in the frontend

---

## 3. Supabase RLS Policies

Row Level Security is the primary data isolation mechanism. Every table that stores user data must have RLS enabled. The universal predicate is `user_id = auth.uid()`.

Enable RLS and grant access only to authenticated users. The `anon` role has no access to any user data table.

### 3.1 users table

```sql
ALTER TABLE users ENABLE ROW LEVEL SECURITY;

-- Users can only read and update their own record
-- They cannot insert (handled by Supabase Auth trigger)
-- They cannot delete (handled by service role only)
CREATE POLICY "users_self_read" ON users
  FOR SELECT TO authenticated
  USING (id = auth.uid());

CREATE POLICY "users_self_update" ON users
  FOR UPDATE TO authenticated
  USING (id = auth.uid())
  WITH CHECK (id = auth.uid());

-- Service role can do anything (used by backend for admin ops)
-- No explicit policy needed; service role bypasses RLS
```

### 3.2 sessions table

```sql
ALTER TABLE sessions ENABLE ROW LEVEL SECURITY;

CREATE POLICY "sessions_user_select" ON sessions
  FOR SELECT TO authenticated
  USING (user_id = auth.uid());

CREATE POLICY "sessions_user_insert" ON sessions
  FOR INSERT TO authenticated
  WITH CHECK (user_id = auth.uid());

CREATE POLICY "sessions_user_update" ON sessions
  FOR UPDATE TO authenticated
  USING (user_id = auth.uid())
  WITH CHECK (user_id = auth.uid());

-- Sessions are soft-deleted by updating ended_at, not hard-deleted
-- Hard deletes only via service role
```

### 3.3 conversation_turns table

```sql
ALTER TABLE conversation_turns ENABLE ROW LEVEL SECURITY;

CREATE POLICY "turns_user_select" ON conversation_turns
  FOR SELECT TO authenticated
  USING (user_id = auth.uid());

CREATE POLICY "turns_user_insert" ON conversation_turns
  FOR INSERT TO authenticated
  WITH CHECK (user_id = auth.uid());

-- Turns are append-only from the user perspective; no UPDATE or DELETE
-- Updates (e.g. corrections) go through the service role only
```

### 3.4 tasks table

```sql
ALTER TABLE tasks ENABLE ROW LEVEL SECURITY;

CREATE POLICY "tasks_user_select" ON tasks
  FOR SELECT TO authenticated
  USING (user_id = auth.uid());

CREATE POLICY "tasks_user_insert" ON tasks
  FOR INSERT TO authenticated
  WITH CHECK (user_id = auth.uid());

CREATE POLICY "tasks_user_update" ON tasks
  FOR UPDATE TO authenticated
  USING (user_id = auth.uid())
  WITH CHECK (user_id = auth.uid());

-- Cancel a task: user sets status = 'cancelled'
-- DELETE not allowed from client; service role only
```

### 3.5 tool_runs table

```sql
ALTER TABLE tool_runs ENABLE ROW LEVEL SECURITY;

-- tool_runs links to tasks; derive user via tasks join
CREATE POLICY "tool_runs_user_select" ON tool_runs
  FOR SELECT TO authenticated
  USING (
    task_id IN (
      SELECT id FROM tasks WHERE user_id = auth.uid()
    )
  );

-- INSERT and UPDATE only via service role (backend writes these)
-- Client has read-only access
```

### 3.6 memory_items table

```sql
ALTER TABLE memory_items ENABLE ROW LEVEL SECURITY;

CREATE POLICY "memory_user_select" ON memory_items
  FOR SELECT TO authenticated
  USING (user_id = auth.uid());

CREATE POLICY "memory_user_insert" ON memory_items
  FOR INSERT TO authenticated
  WITH CHECK (user_id = auth.uid());

CREATE POLICY "memory_user_update" ON memory_items
  FOR UPDATE TO authenticated
  USING (user_id = auth.uid())
  WITH CHECK (user_id = auth.uid());

CREATE POLICY "memory_user_delete" ON memory_items
  FOR DELETE TO authenticated
  USING (user_id = auth.uid());
-- Users can delete their own memories (right-to-erasure compliance)
```

### 3.7 output_documents table

```sql
ALTER TABLE output_documents ENABLE ROW LEVEL SECURITY;

CREATE POLICY "docs_user_select" ON output_documents
  FOR SELECT TO authenticated
  USING (user_id = auth.uid());

CREATE POLICY "docs_user_insert" ON output_documents
  FOR INSERT TO authenticated
  WITH CHECK (user_id = auth.uid());

CREATE POLICY "docs_user_update" ON output_documents
  FOR UPDATE TO authenticated
  USING (user_id = auth.uid())
  WITH CHECK (user_id = auth.uid());

CREATE POLICY "docs_user_delete" ON output_documents
  FOR DELETE TO authenticated
  USING (user_id = auth.uid());
```

### 3.8 billing_usage table

```sql
-- billing_usage tracks quota consumption per user per period
ALTER TABLE billing_usage ENABLE ROW LEVEL SECURITY;

-- Users can read their own usage
CREATE POLICY "billing_usage_user_select" ON billing_usage
  FOR SELECT TO authenticated
  USING (user_id = auth.uid());

-- Only the backend service role can insert/update usage records
-- No authenticated INSERT policy = client cannot write usage
-- This prevents quota manipulation
```

### 3.9 task_events table

```sql
ALTER TABLE task_events ENABLE ROW LEVEL SECURITY;

CREATE POLICY "task_events_user_select" ON task_events
  FOR SELECT TO authenticated
  USING (
    task_id IN (
      SELECT id FROM tasks WHERE user_id = auth.uid()
    )
  );

-- Events are immutable audit records; INSERT/UPDATE/DELETE via service role only
```

### 3.10 Supabase Storage RLS

For Supabase Storage buckets (user-uploaded files, output documents):

```sql
-- Create a private bucket 'user-files'
-- In Supabase Dashboard → Storage → Policies:

-- Allow authenticated users to upload to their own folder
CREATE POLICY "user_files_upload" ON storage.objects
  FOR INSERT TO authenticated
  WITH CHECK (
    bucket_id = 'user-files'
    AND (storage.foldername(name))[1] = auth.uid()::text
  );

-- Allow authenticated users to read their own files
CREATE POLICY "user_files_read" ON storage.objects
  FOR SELECT TO authenticated
  USING (
    bucket_id = 'user-files'
    AND (storage.foldername(name))[1] = auth.uid()::text
  );

-- Allow authenticated users to delete their own files
CREATE POLICY "user_files_delete" ON storage.objects
  FOR DELETE TO authenticated
  USING (
    bucket_id = 'user-files'
    AND (storage.foldername(name))[1] = auth.uid()::text
  );
```

File paths in Supabase Storage should always follow the pattern: `{user_id}/{filename}`.

---

## 4. API Security

### 4.1 Rate Limiting with slowapi

Install:
```bash
pip install slowapi
```

Setup in `backend/main.py`:

```python
from fastapi import FastAPI, Request
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

# Key function: use authenticated user ID if available, fallback to IP
def get_rate_limit_key(request: Request) -> str:
    user = getattr(request.state, "user", None)
    if user:
        return f"user:{user.id}"
    return get_remote_address(request)

limiter = Limiter(key_func=get_rate_limit_key)
app = FastAPI()
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
```

Rate limit decorators:

```python
from slowapi.util import get_remote_address
from backend.main import limiter

# Global default — applied as middleware, not per-route
# 1000 requests/minute per IP (set in Limiter default_limits)
limiter_global = Limiter(
    key_func=get_remote_address,
    default_limits=["1000/minute"],
)

# Auth endpoints — strict per-IP limit
@router.post("/auth/signup")
@limiter.limit("10/minute", key_func=get_remote_address)
async def signup(request: Request, body: SignupRequest):
    ...

@router.post("/auth/login")
@limiter.limit("10/minute", key_func=get_remote_address)
async def login(request: Request, body: LoginRequest):
    ...

# Task creation — per authenticated user
@router.post("/tasks/browser")
@limiter.limit("30/minute")
async def create_browser_task(request: Request, body: BrowserTaskRequest, user: User = Depends(get_current_user)):
    ...

# Sensitive plan changes — force re-auth, lower limit
@router.post("/billing/upgrade")
@limiter.limit("5/minute")
async def upgrade_plan(request: Request, body: UpgradeRequest, user: User = Depends(get_current_user)):
    # Require fresh JWT (issued < 5 minutes ago)
    if (datetime.utcnow() - user.last_auth_at).seconds > 300:
        raise HTTPException(status_code=403, detail="Re-authentication required for plan changes")
    ...
```

### 4.2 CORS Configuration

```python
from fastapi.middleware.cors import CORSMiddleware
import os

CORS_ALLOWED_ORIGINS = os.environ["CORS_ALLOWED_ORIGINS"].split(",")
# Example value: "https://nexus.vercel.app,https://www.nexusapp.com"

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ALLOWED_ORIGINS,  # Never use ["*"] in production
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
    max_age=600,  # Cache preflight for 10 minutes
)
```

**Never use `allow_origins=["*"]` in production.** A wildcard CORS policy allows any website to make credentialed requests to the API.

### 4.3 Input Validation

FastAPI + Pydantic handles input validation automatically. Add explicit constraints:

```python
from pydantic import BaseModel, Field, HttpUrl, validator
from typing import Optional

class BrowserTaskRequest(BaseModel):
    url: HttpUrl                          # Validates URL format
    goal: str = Field(..., max_length=2000)
    session_id: str = Field(..., min_length=36, max_length=36)  # UUID
    allowed_domains: Optional[list[str]] = Field(default=None, max_items=20)

    @validator("url")
    def validate_url_not_internal(cls, v):
        from backend.security.ssrf import is_ssrf_blocked
        if is_ssrf_blocked(str(v)):
            raise ValueError("URL targets a blocked internal address")
        return v

class TaskCancelRequest(BaseModel):
    reason: Optional[str] = Field(default=None, max_length=500)
```

### 4.4 Request Size Limits

```python
from fastapi import FastAPI
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, max_body_size: int = 1024 * 1024):  # 1MB
        super().__init__(app)
        self.max_body_size = max_body_size

    async def dispatch(self, request, call_next):
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > self.max_body_size:
            return Response(status_code=413, content="Request body too large")
        return await call_next(request)

app.add_middleware(RequestSizeLimitMiddleware, max_body_size=1_048_576)
```

### 4.5 API Versioning

All routes use the `/api/v1/` prefix:

```python
# backend/api/v1/router.py
from fastapi import APIRouter
from backend.api.v1 import auth, sessions, tasks, voice, billing, memory, documents

api_v1_router = APIRouter(prefix="/api/v1")
api_v1_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_v1_router.include_router(sessions.router, prefix="/sessions", tags=["sessions"])
api_v1_router.include_router(tasks.router, prefix="/tasks", tags=["tasks"])
api_v1_router.include_router(voice.router, prefix="/voice", tags=["voice"])
api_v1_router.include_router(billing.router, prefix="/billing", tags=["billing"])
api_v1_router.include_router(memory.router, prefix="/memory", tags=["memory"])
api_v1_router.include_router(documents.router, prefix="/documents", tags=["documents"])

app.include_router(api_v1_router)
```

### 4.6 Security Headers

```python
from starlette.middleware.base import BaseHTTPMiddleware

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        # Remove server header
        response.headers.pop("server", None)
        return response

app.add_middleware(SecurityHeadersMiddleware)
```

### 4.7 LemonSqueezy Webhook Verification

```python
import hmac
import hashlib
from fastapi import Request, HTTPException
import os

WEBHOOK_SECRET = os.environ["LEMONSQUEEZY_WEBHOOK_SECRET"]

async def verify_lemonsqueezy_webhook(request: Request) -> bytes:
    """Returns the raw body if signature is valid, raises 401 otherwise."""
    body = await request.body()
    signature = request.headers.get("X-Signature")

    if not signature:
        raise HTTPException(status_code=401, detail="Missing webhook signature")

    expected = hmac.new(
        WEBHOOK_SECRET.encode(),
        body,
        hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(expected, signature):
        raise HTTPException(status_code=401, detail="Invalid webhook signature")

    return body

@router.post("/billing/webhook")
async def billing_webhook(request: Request):
    body = await verify_lemonsqueezy_webhook(request)
    event = json.loads(body)
    event_name = event.get("meta", {}).get("event_name")
    # Idempotency: check if this event_id was already processed
    event_id = event.get("meta", {}).get("event_id")
    if await is_event_already_processed(event_id):
        return {"status": "already_processed"}
    # Handle event...
```

---

## 5. Windows Agent Security

The local Windows agent running at `http://127.0.0.1:8765` is the highest-risk component in the system: it can execute arbitrary file system operations and interact with Windows applications on the user's machine.

### 5.1 Agent Authentication

A shared secret token is generated at agent installation time and stored in the user's agent config file (`%APPDATA%\Nexus\agent_config.json`). The backend stores the same token against the user's account in the database.

**Token generation (first run):**

```python
# windows_agent/setup.py
import secrets
import json
import os

def generate_agent_token() -> str:
    """Generate a cryptographically secure agent token."""
    return secrets.token_urlsafe(32)  # 256 bits of entropy

def save_agent_config(token: str):
    config_dir = os.path.expandvars(r"%APPDATA%\Nexus")
    os.makedirs(config_dir, exist_ok=True)
    config_path = os.path.join(config_dir, "agent_config.json")
    with open(config_path, "w") as f:
        json.dump({"agent_token": token, "version": "1.0"}, f)
```

**Backend validates agent token:**

Every request from the backend to the agent includes:
```
X-Agent-Token: <token>
X-Request-ID: <uuid>   (for logging / replay detection)
```

**Agent-side validation:**

```python
# windows_agent/main.py
from fastapi import FastAPI, Header, HTTPException
import os

app = FastAPI()
AGENT_TOKEN = os.environ.get("NEXUS_AGENT_TOKEN") or load_token_from_config()

@app.middleware("http")
async def require_agent_token(request, call_next):
    # Only accept connections from localhost
    client_host = request.client.host
    if client_host not in ("127.0.0.1", "::1"):
        return Response(status_code=403, content="Forbidden: non-local connection")

    token = request.headers.get("X-Agent-Token")
    if not token or not hmac.compare_digest(token, AGENT_TOKEN):
        return Response(status_code=401, content="Unauthorized")

    return await call_next(request)
```

### 5.2 Action Policy

Create `windows_agent/policy.py`:

```python
from enum import Enum
from dataclasses import dataclass
from typing import Optional

class ActionCategory(Enum):
    # Allowed automatically, no confirmation needed
    OPEN_APP = "open_app"
    CREATE_FOLDER = "create_folder"
    TYPE_TEXT = "type_text"
    COPY_FILE = "copy_file"
    MOVE_FILE = "move_file"
    READ_FILE = "read_file"
    TAKE_SCREENSHOT = "take_screenshot"
    FOCUS_WINDOW = "focus_window"
    PRESS_KEYS = "press_keys"

    # Always require explicit user confirmation
    DELETE_FILE = "delete_file"
    DELETE_FOLDER = "delete_folder"
    SEND_MESSAGE = "send_message"          # Email, chat, etc.
    SEND_EMAIL = "send_email"
    MAKE_PURCHASE = "make_purchase"
    SUBMIT_FORM = "submit_form"
    MODIFY_SYSTEM_SETTINGS = "modify_system_settings"
    INSTALL_SOFTWARE = "install_software"
    RUN_SCRIPT = "run_script"

    # Permanently blocked — never allowed
    EDIT_REGISTRY = "edit_registry"
    ACCESS_SYSTEM32 = "access_system32"
    MODIFY_NETWORK_CONFIG = "modify_network_config"
    DISABLE_ANTIVIRUS = "disable_antivirus"
    MODIFY_HOSTS_FILE = "modify_hosts_file"
    EXECUTE_ARBITRARY_CODE = "execute_arbitrary_code"


# Confirmation-required categories
CONFIRMATION_REQUIRED = {
    ActionCategory.DELETE_FILE,
    ActionCategory.DELETE_FOLDER,
    ActionCategory.SEND_MESSAGE,
    ActionCategory.SEND_EMAIL,
    ActionCategory.MAKE_PURCHASE,
    ActionCategory.SUBMIT_FORM,
    ActionCategory.MODIFY_SYSTEM_SETTINGS,
    ActionCategory.INSTALL_SOFTWARE,
    ActionCategory.RUN_SCRIPT,
}

# Permanently blocked categories
BLOCKED = {
    ActionCategory.EDIT_REGISTRY,
    ActionCategory.ACCESS_SYSTEM32,
    ActionCategory.MODIFY_NETWORK_CONFIG,
    ActionCategory.DISABLE_ANTIVIRUS,
    ActionCategory.MODIFY_HOSTS_FILE,
    ActionCategory.EXECUTE_ARBITRARY_CODE,
}


@dataclass
class ActionRequest:
    category: ActionCategory
    action: str
    parameters: dict
    user_id: str
    task_id: str
    confirmed: bool = False   # True if user has already confirmed


class ActionPolicy:

    def is_blocked(self, action: ActionRequest) -> bool:
        """Returns True if the action is permanently blocked and must never execute."""
        return action.category in BLOCKED

    def requires_confirmation(self, action: ActionRequest) -> bool:
        """Returns True if this action needs explicit user confirmation before execution."""
        if self.is_blocked(action):
            return False  # Blocked actions don't get a confirmation prompt — just reject
        return action.category in CONFIRMATION_REQUIRED

    def can_execute(self, action: ActionRequest) -> tuple[bool, Optional[str]]:
        """
        Returns (can_execute, rejection_reason).
        can_execute is True only if the action is not blocked and
        either does not require confirmation or has been confirmed.
        """
        if self.is_blocked(action):
            return False, f"Action category '{action.category.value}' is permanently blocked"

        if self.requires_confirmation(action) and not action.confirmed:
            return False, "confirmation_required"

        return True, None
```

### 5.3 Confirmation Flow

The confirmation flow prevents the LLM or any automated process from executing destructive actions without explicit user approval:

```
Backend constructs action request
          │
          ▼
ActionPolicy.can_execute() called
          │
    ┌─────┴─────┐
    │           │
blocked    confirmation_required
    │           │
 Return       Backend returns to frontend:
 403           { "confirmation_required": true,
               "action": "delete_file",
               "parameters": { "path": "C:/Users/..." },
               "confirmation_token": "<signed JWT>" }
                │
                ▼
          Frontend shows confirm dialog:
          "Delete file C:/Users/...? [Cancel] [Confirm]"
                │
          User clicks [Confirm]
                │
                ▼
          Frontend sends:
          POST /api/v1/tasks/{id}/confirm
          { "confirmation_token": "<signed JWT>" }
                │
                ▼
          Backend verifies token, sets action.confirmed = True
          Sends confirmed request to Windows agent
                │
                ▼
          Agent executes action, logs result
```

**Signed confirmation token:**

```python
# backend/security/confirmation.py
from jose import jwt
import os
import time

CONFIRMATION_SECRET = os.environ["CONFIRMATION_TOKEN_SECRET"]

def create_confirmation_token(action: dict, ttl_seconds: int = 120) -> str:
    """Creates a short-lived signed token for a specific action."""
    payload = {
        "action": action,
        "exp": time.time() + ttl_seconds,
        "iat": time.time(),
    }
    return jwt.encode(payload, CONFIRMATION_SECRET, algorithm="HS256")

def verify_confirmation_token(token: str) -> dict:
    """Verifies and returns the action payload. Raises if invalid/expired."""
    return jwt.decode(token, CONFIRMATION_SECRET, algorithms=["HS256"])
```

### 5.4 Path Validation

Before any file operation, validate the target path:

```python
# windows_agent/security.py
import os

BLOCKED_PATHS = [
    "C:\\Windows\\System32",
    "C:\\Windows\\SysWOW64",
    "C:\\Program Files",
    "C:\\Program Files (x86)",
]

def is_path_safe(path: str) -> tuple[bool, str]:
    """Check if a file path is safe to operate on."""
    abs_path = os.path.abspath(path)

    for blocked in BLOCKED_PATHS:
        if abs_path.lower().startswith(blocked.lower()):
            return False, f"Path is in a protected system directory: {blocked}"

    # Prevent path traversal
    if ".." in path:
        return False, "Path traversal detected"

    return True, ""
```

---

## 6. Browser Automation Security

### 6.1 SSRF Prevention

All URLs passed to Browser Use must be validated before dispatch:

```python
# backend/security/ssrf.py
import ipaddress
import socket
from urllib.parse import urlparse

BLOCKED_IP_RANGES = [
    ipaddress.ip_network("127.0.0.0/8"),      # Loopback
    ipaddress.ip_network("10.0.0.0/8"),        # Private class A
    ipaddress.ip_network("172.16.0.0/12"),     # Private class B
    ipaddress.ip_network("192.168.0.0/16"),    # Private class C
    ipaddress.ip_network("169.254.0.0/16"),    # Link-local / cloud metadata
    ipaddress.ip_network("::1/128"),           # IPv6 loopback
    ipaddress.ip_network("fc00::/7"),          # IPv6 unique local
]

def is_ssrf_blocked(url: str) -> bool:
    """Returns True if the URL targets an internal/restricted address."""
    try:
        parsed = urlparse(url)
        hostname = parsed.hostname

        if not hostname:
            return True

        # Block localhost by name
        if hostname.lower() in ("localhost", "local", "internal"):
            return True

        # Resolve and check IP
        try:
            ip = ipaddress.ip_address(socket.gethostbyname(hostname))
        except socket.gaierror:
            return True  # DNS resolution failure = block

        for blocked_range in BLOCKED_IP_RANGES:
            if ip in blocked_range:
                return True

        return False

    except Exception:
        return True  # Fail closed on any error
```

### 6.2 Sensitive Browser Action Confirmation

Browser actions that cause side effects (beyond read-only browsing) require confirmation:

```python
# backend/modules/browser_task/policy.py

CONFIRMATION_REQUIRED_BROWSER_ACTIONS = {
    "form_submit",    # Any form submission
    "purchase",       # Checkout/buy flows
    "send_email",     # Composing and sending email
    "send_message",   # Chat/messaging apps
    "file_download",  # Saving files to disk
    "delete_action",  # Clicking delete/remove in web UI
}

def browser_action_requires_confirmation(action_type: str) -> bool:
    return action_type in CONFIRMATION_REQUIRED_BROWSER_ACTIONS
```

### 6.3 Data Handling Rules

- Raw HTML and full DOM dumps are **never stored** in the database
- Browser Use results are summarized by the LLM before storage
- Screenshots (if taken for debugging) are stored in Supabase Storage under the user's private folder and deleted after 24 hours
- Cookies and session data used by Browser Use are isolated per user task and cleared after task completion
- No cross-user browser profile sharing

### 6.4 Domain Allowlist / Blocklist

Users can configure a domain blocklist in their settings. The browser task module checks this before execution:

```python
async def validate_browser_task_url(url: str, user: User) -> None:
    # Check SSRF
    if is_ssrf_blocked(url):
        raise HTTPException(400, "URL is not accessible from browser automation")

    # Check user's personal blocklist
    blocked_domains = user.settings.get("browser_blocked_domains", [])
    hostname = urlparse(url).hostname or ""
    for blocked in blocked_domains:
        if hostname == blocked or hostname.endswith(f".{blocked}"):
            raise HTTPException(400, f"Domain {hostname} is in your blocklist")
```

---

## 7. Secret Management

### 7.1 Principles

1. **No hardcoded secrets** — every secret is an environment variable; the word `sk-`, `secret`, or `key` should never appear in committed code as a value
2. **Principle of least privilege** — each secret is scoped to the minimum required access
3. **Secret rotation** without downtime using blue/green key patterns
4. **Never log secrets** — Sentry, Langfuse, and Posthog must be configured to scrub sensitive fields

### 7.2 .env.example

This file is committed to the repo. It documents required variables with no values.

```env
# ============================================================
# Nexus 2.0 — Backend Environment Variables
# Copy to .env.local and fill in values for local development
# NEVER commit .env.local or any file with real values
# ============================================================

# --- Supabase ---
SUPABASE_URL=
SUPABASE_ANON_KEY=
SUPABASE_SERVICE_ROLE_KEY=
SUPABASE_JWT_SECRET=

# --- GetStream ---
GETSTREAM_API_KEY=
GETSTREAM_API_SECRET=

# --- Inngest ---
INNGEST_EVENT_KEY=
INNGEST_SIGNING_KEY=

# --- LLM Providers ---
OPENROUTER_API_KEY=
GROQ_API_KEY=
OPENAI_API_KEY=

# --- Voice / STT ---
DEEPGRAM_API_KEY=

# --- Billing ---
LEMONSQUEEZY_API_KEY=
LEMONSQUEEZY_WEBHOOK_SECRET=
LEMONSQUEEZY_STORE_ID=
LEMONSQUEEZY_PRO_VARIANT_ID=
LEMONSQUEEZY_POWER_VARIANT_ID=

# --- Storage ---
CLOUDFLARE_R2_ACCESS_KEY=
CLOUDFLARE_R2_SECRET_KEY=
CLOUDFLARE_R2_BUCKET=
CLOUDFLARE_R2_ENDPOINT=

# --- Observability ---
LANGFUSE_SECRET_KEY=
LANGFUSE_PUBLIC_KEY=
LANGFUSE_HOST=https://cloud.langfuse.com
SENTRY_DSN=

# --- Application ---
CORS_ALLOWED_ORIGINS=
CONFIRMATION_TOKEN_SECRET=
APP_ENV=development
```

```env
# ============================================================
# Nexus 2.0 — Frontend Environment Variables (.env.local)
# ============================================================

NEXT_PUBLIC_SUPABASE_URL=
NEXT_PUBLIC_SUPABASE_ANON_KEY=
NEXT_PUBLIC_API_URL=
NEXT_PUBLIC_GETSTREAM_API_KEY=
NEXT_PUBLIC_POSTHOG_KEY=
NEXT_PUBLIC_POSTHOG_HOST=https://app.posthog.com
NEXT_PUBLIC_SENTRY_DSN=
```

### 7.3 .gitignore Entries

```gitignore
# Secrets — never commit
.env
.env.local
.env.*.local
*.pem
*.key
agent_config.json
```

### 7.4 Railway Secret Management

In Railway:
1. Go to your service → **Variables** tab
2. Add each variable individually (or paste a `.env` file bulk import)
3. Variables are encrypted at rest and injected at runtime
4. Use Railway **Environments** (Production / Development) to keep values separate
5. Never put secrets in `railway.json` or `Dockerfile` as hardcoded values

### 7.5 Secret Rotation (Zero Downtime)

For rotating a secret like `OPENAI_API_KEY` without downtime:

```
Step 1: Generate new API key at the provider
Step 2: Add new key as OPENAI_API_KEY_NEW in Railway
Step 3: Update application code to try OPENAI_API_KEY_NEW, fallback to OPENAI_API_KEY
Step 4: Deploy this version
Step 5: Verify new key works (monitor Sentry for errors)
Step 6: Set OPENAI_API_KEY = (new value), remove OPENAI_API_KEY_NEW
Step 7: Deploy final version
Step 8: Revoke old key at the provider
```

For rotating `SUPABASE_SERVICE_ROLE_KEY`:
- Generate a new key in Supabase Dashboard → Settings → API
- Apply blue/green rotation as above
- Old key becomes invalid immediately after Supabase regenerates it — plan for brief overlap period

---

## 8. Security Checklist (Pre-Launch)

### Authentication & Access Control
- [ ] Supabase Auth is enabled with email/password login
- [ ] OAuth providers (Google, GitHub) configured with correct redirect URLs
- [ ] RLS enabled on ALL tables: users, sessions, conversation_turns, tasks, task_events, tool_runs, memory_items, output_documents, billing_usage
- [ ] Supabase anon key cannot read any user data table (tested manually)
- [ ] Service role key is only in backend environment — not in frontend bundle
- [ ] FastAPI JWT validation dependency applied to all authenticated routes
- [ ] JWT access token TTL set to 1 hour
- [ ] Refresh token rotation enabled in Supabase Auth settings

### API Security
- [ ] CORS restricted to production frontend domain(s) only — no wildcard
- [ ] Rate limiting active on auth endpoints (10/min per IP)
- [ ] Rate limiting active on task creation (30/min per user)
- [ ] Request body size capped at 1MB
- [ ] All routes use `/api/v1/` prefix
- [ ] Security headers middleware active (HSTS, X-Frame-Options, etc.)
- [ ] LemonSqueezy webhook signature verified on every request
- [ ] Webhook idempotency: duplicate event IDs are ignored

### Windows Agent
- [ ] Agent token generated and stored securely at install time
- [ ] Agent only listens on 127.0.0.1 (not 0.0.0.0)
- [ ] ActionPolicy blocks all BLOCKED categories
- [ ] ActionPolicy requires confirmation for all CONFIRMATION_REQUIRED categories
- [ ] Confirmation tokens are short-lived (TTL ≤ 2 minutes)
- [ ] Path validation rejects system directories and `..` traversal
- [ ] All agent commands are logged to backend before execution

### Browser Automation
- [ ] SSRF filter validates all URLs before passing to Browser Use
- [ ] Private IP ranges and cloud metadata endpoints are blocked
- [ ] Sensitive browser actions (form submit, purchase, send) require user confirmation
- [ ] Raw HTML/DOM data is not stored in the database
- [ ] Browser sessions are isolated per user task

### Secrets & Infrastructure
- [ ] No secrets hardcoded in any source file
- [ ] `.env.local` and all secret files are in `.gitignore`
- [ ] All Railway environment variables set for production
- [ ] Vercel environment variables set for production
- [ ] All API keys are scoped to minimum required permissions
- [ ] `SUPABASE_SERVICE_ROLE_KEY` is not in any frontend code or bundle

### Observability & Incident Response
- [ ] Sentry DSN configured for both backend and frontend
- [ ] Sentry configured to scrub PII (email, names, JWT tokens) from error reports
- [ ] Langfuse traces do not include raw user passwords or secret keys
- [ ] Alert configured for >10 consecutive 401 responses from a single IP (credential stuffing indicator)
- [ ] Alert configured for abnormal task creation rate (quota abuse)

### Data & Privacy
- [ ] HTTPS enforced on all endpoints (Vercel and Railway provide this automatically)
- [ ] Voice audio is not stored by default (GetStream does not persist audio unless configured)
- [ ] Users can delete their account and all associated data (right to erasure)
- [ ] Privacy policy reflects actual data practices

---

*This document should be reviewed and updated with every significant architectural change. Treat it as a living security contract for the Nexus 2.0 project.*
