# Nexus 2.0 — Deployment Runbook

**Version:** 1.0  
**Last Updated:** 2025  
**Scope:** Complete production deployment guide for Nexus 2.0 (voice-first AI assistant)  
**Stack:** FastAPI + Railway · Next.js + Vercel · Supabase · GetStream · Inngest · Cloudflare R2 · LemonSqueezy  
**Estimated time for first deploy:** 3–4 hours  

---

## Table of Contents

1. [Infrastructure Overview](#1-infrastructure-overview)
2. [Prerequisites & Accounts](#2-prerequisites--accounts)
3. [Step 1: Supabase Setup](#3-step-1-supabase-setup)
4. [Step 2: GetStream Setup](#4-step-2-getstream-setup)
5. [Step 3: Inngest Setup](#5-step-3-inngest-setup)
6. [Step 4: Backend Deployment (Railway)](#6-step-4-backend-deployment-railway)
7. [Step 5: Frontend Deployment (Vercel)](#7-step-5-frontend-deployment-vercel)
8. [Step 6: LemonSqueezy Setup](#8-step-6-lemonsqueezy-setup)
9. [Step 7: Cloudflare R2 Setup](#9-step-7-cloudflare-r2-setup)
10. [Step 8: Observability Setup](#10-step-8-observability-setup)
11. [Step 9: Windows Agent Distribution](#11-step-9-windows-agent-distribution)
12. [Health Checks & Smoke Tests](#12-health-checks--smoke-tests)
13. [Rollback Procedures](#13-rollback-procedures)
14. [Environment Promotion](#14-environment-promotion)
15. [Ongoing Maintenance](#15-ongoing-maintenance)

---

## 1. Infrastructure Overview

### Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                         USER'S BROWSER / APP                        │
│               Next.js SPA (TypeScript + pnpm)                       │
│                     Deployed on Vercel                              │
└──────────────────────────────┬──────────────────────────────────────┘
                               │ HTTPS (REST + SSE)
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    RAILWAY: FastAPI Backend                          │
│              (modular monolith, Python, uvicorn)                    │
│   Auth · Sessions · Tasks · Memory · Billing · Voice · Research     │
└──────┬───────────────┬───────────────┬──────────────────────────────┘
       │               │               │
       │ SDK           │ HTTP          │ SDK
       ▼               ▼               ▼
┌──────────┐   ┌──────────────┐   ┌──────────────────────────────────┐
│GetStream │   │  Supabase    │   │         Inngest Cloud            │
│Video     │   │  Postgres    │   │  (background job queue)          │
│Cloud     │   │  + pgvector  │   │  Browser tasks, research jobs    │
│(WebRTC / │   │  + Auth      │   └──────────────────────────────────┘
│STT/TTS)  │   │  + Storage   │
└──────────┘   └──────┬───────┘
                      │ S3-compatible API
                      ▼
               ┌──────────────┐
               │ Cloudflare   │
               │ R2 Storage   │
               │ (10GB free)  │
               └──────────────┘

       ┌───────────────────────────────────────────┐
       │         USER'S WINDOWS MACHINE            │
       │  Windows Agent (Python → .exe)            │
       │  HTTP server: http://127.0.0.1:8765       │
       │  ← Commands from Railway backend          │
       │    (via HTTPS tunnel through Nexus API)   │
       └───────────────────────────────────────────┘

Observability (all cloud-hosted, free tiers):
  Langfuse → LLM traces
  Posthog  → Product analytics
  Sentry   → Error tracking (frontend + backend)
```

### Data Flow Summary

| Flow | Protocol | Description |
|---|---|---|
| Browser ↔ Vercel | HTTPS | Static assets, SSR pages |
| Browser ↔ Railway | HTTPS + SSE | API calls, streaming responses |
| Browser ↔ GetStream | WebRTC | Voice audio streams |
| Railway ↔ Supabase | HTTPS (pooled) | DB reads/writes via supabase-py |
| Railway ↔ GetStream | HTTPS SDK | Create voice sessions, send events |
| Railway ↔ Inngest | HTTPS | Enqueue and receive background jobs |
| Railway ↔ R2 | S3-compatible HTTPS | Upload/download files |
| Railway ↔ Windows Agent | HTTPS (via Nexus API relay) | Send commands to local agent |
| LemonSqueezy → Railway | HTTPS webhook | Payment events |

---

## 2. Prerequisites & Accounts

Create accounts in this order (most have free tiers; cost estimates are for production use):

| Service | URL | Free Tier | Paid | Purpose |
|---|---|---|---|---|
| **GitHub** | github.com | Free | — | Source code + CI/CD |
| **Supabase** | supabase.com | 500MB DB, 1GB storage | $25/mo Pro | DB + Auth + Storage |
| **Railway** | railway.app | $5/mo Starter | $5+/mo usage | FastAPI backend hosting |
| **Vercel** | vercel.com | Hobby (free) | $20/mo Pro | Next.js frontend hosting |
| **Cloudflare** | cloudflare.com | 10GB R2 free | Per-GB over 10GB | Object storage (R2) |
| **Inngest** | inngest.com | 50k runs/mo | Usage-based | Background job queue |
| **GetStream** | getstream.io | 1M msg/mo + voice | Usage-based | Voice/WebRTC infrastructure |
| **LemonSqueezy** | lemonsqueezy.com | Free (5% tx fee) | — | Billing/subscriptions |
| **Langfuse** | cloud.langfuse.com | Free (50k events/mo) | Usage-based | LLM observability |
| **Posthog** | posthog.com | Free (1M events/mo) | Usage-based | Product analytics |
| **Sentry** | sentry.io | Free (5k errors/mo) | $26/mo Team | Error tracking |

### Local Prerequisites

```bash
# Required on your development machine
node --version    # >= 18.0.0
python --version  # >= 3.11
pnpm --version    # >= 8.0.0  (install: npm i -g pnpm)
git --version     # any recent version

# CLI tools (install as needed)
pip install supabase          # Supabase Python client
npm install -g vercel         # Vercel CLI
npm install -g railway        # Railway CLI (optional but useful)
pip install pyinstaller        # For Windows agent packaging
```

### Repository Setup

```bash
# Clone the repo
git clone https://github.com/your-org/nexus.git
cd nexus

# Install backend dependencies
cd backend
pip install -r requirements.txt
cd ..

# Install frontend dependencies
cd frontend
pnpm install
cd ..
```

---

## 3. Step 1: Supabase Setup

### 3.1 Create the Project

1. Go to [supabase.com](https://supabase.com) and sign in
2. Click **New Project**
3. Enter:
   - **Project name:** `nexus-production` (or `nexus-development` for dev)
   - **Database password:** Generate a strong password and store it in your password manager
   - **Region:** Choose closest to your primary user base (e.g., `eu-west-1` for Europe, `us-east-1` for US)
4. Click **Create new project** — wait ~2 minutes for provisioning

### 3.2 Enable pgvector Extension

Once the project is ready, go to **SQL Editor** and run:

```sql
-- Enable pgvector for semantic search / memory embeddings
CREATE EXTENSION IF NOT EXISTS vector;

-- Verify installation
SELECT * FROM pg_extension WHERE extname = 'vector';
```

### 3.3 Run DB Migrations

If you have Supabase CLI set up locally:

```bash
# Install Supabase CLI
brew install supabase/tap/supabase   # macOS
# or: npm install -g supabase        # cross-platform

# Log in
supabase login

# Link to your project (get project ref from Supabase dashboard URL)
supabase link --project-ref <your-project-ref>

# Run migrations
supabase db push
```

If not using the CLI, run migrations manually in the SQL Editor. Create the tables in this order (respects foreign keys):

```sql
-- 1. Users table (extends Supabase Auth users)
CREATE TABLE users (
  id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  email VARCHAR(255) UNIQUE NOT NULL,
  display_name VARCHAR(100),
  plan VARCHAR(20) NOT NULL DEFAULT 'free',  -- 'free', 'pro', 'power'
  lemonsqueezy_customer_id VARCHAR(100),
  lemonsqueezy_subscription_id VARCHAR(100),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  settings_json JSONB DEFAULT '{}'::jsonb
);

-- 2. Sessions
CREATE TABLE sessions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  ended_at TIMESTAMPTZ,
  entry_mode VARCHAR(20) NOT NULL DEFAULT 'text',
  active_mode VARCHAR(20) NOT NULL DEFAULT 'assistant',
  metadata JSONB DEFAULT '{}'::jsonb
);
CREATE INDEX idx_sessions_user_id ON sessions(user_id);
CREATE INDEX idx_sessions_started_at ON sessions(started_at);

-- 3. Conversation turns
CREATE TABLE conversation_turns (
  id BIGSERIAL PRIMARY KEY,
  session_id UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  role VARCHAR(20) NOT NULL CHECK (role IN ('user', 'assistant')),
  input_mode VARCHAR(20) NOT NULL DEFAULT 'text',
  content TEXT NOT NULL,
  language VARCHAR(10),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  related_task_id UUID,
  metadata JSONB DEFAULT '{}'::jsonb
);
CREATE INDEX idx_turns_session_id ON conversation_turns(session_id);
CREATE INDEX idx_turns_session_created ON conversation_turns(session_id, created_at);

-- 4. Tasks
CREATE TABLE tasks (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  session_id UUID REFERENCES sessions(id),
  type VARCHAR(20) NOT NULL CHECK (type IN ('browser', 'windows', 'research', 'mixed')),
  status VARCHAR(20) NOT NULL DEFAULT 'pending'
    CHECK (status IN ('pending', 'running', 'succeeded', 'failed', 'cancelled')),
  title VARCHAR(255),
  description TEXT,
  result_summary TEXT,
  error_message TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  metadata JSONB DEFAULT '{}'::jsonb
);
CREATE INDEX idx_tasks_user_id ON tasks(user_id);
CREATE INDEX idx_tasks_user_created ON tasks(user_id, created_at);

-- 5. Task events
CREATE TABLE task_events (
  id BIGSERIAL PRIMARY KEY,
  task_id UUID NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
  event_type VARCHAR(50) NOT NULL,
  payload JSONB DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_task_events_task_id ON task_events(task_id);

-- 6. Tool runs
CREATE TABLE tool_runs (
  id BIGSERIAL PRIMARY KEY,
  task_id UUID NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
  tool_type VARCHAR(30) NOT NULL,
  tool_name VARCHAR(100),
  status VARCHAR(20) NOT NULL DEFAULT 'pending',
  requested_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  completed_at TIMESTAMPTZ,
  request_payload JSONB DEFAULT '{}'::jsonb,
  response_payload JSONB DEFAULT '{}'::jsonb,
  error_message TEXT
);
CREATE INDEX idx_tool_runs_task_id ON tool_runs(task_id);

-- 7. Memory items
CREATE TABLE memory_items (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  scope VARCHAR(20) NOT NULL CHECK (scope IN ('profile', 'session', 'task', 'global')),
  session_id UUID REFERENCES sessions(id),
  task_id UUID REFERENCES tasks(id),
  label VARCHAR(255),
  content TEXT NOT NULL,
  importance SMALLINT NOT NULL DEFAULT 3 CHECK (importance BETWEEN 1 AND 5),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  metadata JSONB DEFAULT '{}'::jsonb,
  -- pgvector column for semantic search (optional, add when implementing RAG)
  embedding vector(1536)
);
CREATE INDEX idx_memory_user_id ON memory_items(user_id);
CREATE INDEX idx_memory_user_scope ON memory_items(user_id, scope);
-- Vector index (add when embedding column is populated)
-- CREATE INDEX idx_memory_embedding ON memory_items USING ivfflat (embedding vector_cosine_ops);

-- 8. Output documents
CREATE TABLE output_documents (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  task_id UUID REFERENCES tasks(id),
  title VARCHAR(255) NOT NULL,
  content_markdown TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  metadata JSONB DEFAULT '{}'::jsonb
);
CREATE INDEX idx_docs_user_id ON output_documents(user_id);
CREATE INDEX idx_docs_task_id ON output_documents(task_id);

-- 9. Billing usage
CREATE TABLE billing_usage (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  period_start DATE NOT NULL,
  period_end DATE NOT NULL,
  browser_tasks_used INTEGER NOT NULL DEFAULT 0,
  windows_tasks_used INTEGER NOT NULL DEFAULT 0,
  voice_minutes_used INTEGER NOT NULL DEFAULT 0,
  api_calls_used INTEGER NOT NULL DEFAULT 0,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (user_id, period_start)
);
CREATE INDEX idx_billing_user_period ON billing_usage(user_id, period_start);
```

### 3.4 Enable RLS on All Tables

```sql
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE conversation_turns ENABLE ROW LEVEL SECURITY;
ALTER TABLE tasks ENABLE ROW LEVEL SECURITY;
ALTER TABLE task_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE tool_runs ENABLE ROW LEVEL SECURITY;
ALTER TABLE memory_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE output_documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE billing_usage ENABLE ROW LEVEL SECURITY;
```

Then apply the full RLS policies documented in `security_model.md` Section 3.

### 3.5 Create Supabase Auth Trigger

When a new user signs up via Supabase Auth, automatically create a record in the `users` table:

```sql
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
  INSERT INTO public.users (id, email)
  VALUES (NEW.id, NEW.email)
  ON CONFLICT (id) DO NOTHING;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE TRIGGER on_auth_user_created
  AFTER INSERT ON auth.users
  FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();
```

### 3.6 Configure Supabase Auth

In Supabase Dashboard → **Authentication** → **Settings**:

1. **Email Auth:** Enabled (default)
2. **Confirm email:** Enable for production (users must verify email)
3. **Site URL:** `https://your-vercel-app.vercel.app`
4. **Redirect URLs:** Add:
   - `https://your-vercel-app.vercel.app/auth/callback`
   - `http://localhost:3000/auth/callback` (for local dev)
5. **JWT expiry:** 3600 seconds (1 hour)
6. **Enable refresh token rotation:** Yes

For OAuth (optional):
- **Google:** Enable Google provider, add Client ID and Secret from Google Cloud Console
- **GitHub:** Enable GitHub provider, add Client ID and Secret from GitHub OAuth Apps

### 3.7 Create Storage Buckets

In Supabase Dashboard → **Storage**:

1. Create bucket: `user-files` → Private
2. Create bucket: `output-documents` → Private
3. Apply the storage RLS policies from `security_model.md` Section 3.10

### 3.8 Collect Credentials

From Supabase Dashboard → **Settings** → **API**:

```
SUPABASE_URL=https://<project-ref>.supabase.co
SUPABASE_ANON_KEY=<anon key>
SUPABASE_SERVICE_ROLE_KEY=<service role key>
SUPABASE_JWT_SECRET=<JWT secret>
```

Store these securely — do not commit them to the repo.

---

## 4. Step 2: GetStream Setup

### 4.1 Create Account and App

1. Go to [getstream.io](https://getstream.io) and sign up
2. In the dashboard, click **Create App**
3. Enter app name: `nexus-production`
4. Select server location closest to your Railway deployment region
5. Click **Create App**

### 4.2 Enable Video Features

In the app dashboard:
1. Go to **Video & Audio** → **Enable**
2. Under **Call Types**, verify `default` call type is enabled
3. Under **Recording** → leave disabled (Nexus does not store audio by default)
4. Under **Transcription** → configure if you want server-side STT fallback

### 4.3 Configure Webhook for Call Events

1. In GetStream dashboard → **Webhooks**
2. Add webhook URL: `https://<your-railway-url>.railway.app/api/v1/voice/webhook`
3. Enable events:
   - `call.created`
   - `call.ended`
   - `call.session_participant_joined`
   - `call.session_participant_left`
4. Copy the webhook secret for signature verification

### 4.4 Collect Credentials

```
GETSTREAM_API_KEY=<api key>
GETSTREAM_API_SECRET=<api secret>
```

### 4.5 Backend Integration

Install the GetStream Python SDK:

```bash
pip install getstream
```

Initialize in `backend/modules/voice/client.py`:

```python
from getstream import Stream
import os

stream_client = Stream(
    api_key=os.environ["GETSTREAM_API_KEY"],
    api_secret=os.environ["GETSTREAM_API_SECRET"],
)

async def create_voice_call(session_id: str, user_id: str) -> dict:
    """Create a GetStream voice call and return the token for the frontend."""
    call = stream_client.video.call("default", session_id)
    await call.create(data={"created_by_id": user_id})
    token = stream_client.create_call_token(user_id=user_id, call_cid=f"default:{session_id}")
    return {"call_id": session_id, "token": token}
```

---

## 5. Step 3: Inngest Setup

### 5.1 Create Account and App

1. Go to [inngest.com](https://inngest.com) and sign up
2. Click **Create App**
3. App name: `nexus-backend`
4. Language: **Python**
5. Click **Create**

### 5.2 Collect Credentials

From the Inngest dashboard → **Settings** → **API Keys**:

```
INNGEST_EVENT_KEY=<event key>
INNGEST_SIGNING_KEY=<signing key>
```

### 5.3 Backend Integration

Install:

```bash
pip install inngest
```

Initialize in `backend/inngest_client.py`:

```python
import inngest
import os

inngest_client = inngest.Inngest(
    app_id="nexus-backend",
    event_key=os.environ["INNGEST_EVENT_KEY"],
    signing_key=os.environ["INNGEST_SIGNING_KEY"],
)
```

Define functions in `backend/jobs/browser_task.py`:

```python
from backend.inngest_client import inngest_client
import inngest

@inngest_client.create_function(
    fn_id="run-browser-task",
    trigger=inngest.TriggerEvent(event="nexus/task.browser.requested"),
    concurrency=[inngest.Concurrency(limit=2, key="event.data.user_id")],
    retries=2,
)
async def run_browser_task(ctx: inngest.Context, step: inngest.Step) -> dict:
    task_id = ctx.event.data["task_id"]
    user_id = ctx.event.data["user_id"]
    goal = ctx.event.data["goal"]
    url = ctx.event.data["url"]

    result = await step.run("execute-browser-task", lambda: _execute_browser(task_id, goal, url))
    return result
```

Mount the Inngest endpoint in `backend/main.py`:

```python
from inngest.fast_api import serve
from backend.inngest_client import inngest_client
from backend.jobs import browser_task, research_task, windows_task

serve(app, inngest_client, [
    browser_task.run_browser_task,
    research_task.run_research_task,
    windows_task.run_windows_task,
])
# This creates: POST /api/inngest
```

### 5.4 Point Inngest to Backend

After backend is deployed on Railway:

1. In Inngest dashboard → **Apps** → your app
2. Click **Sync**
3. Enter your backend URL: `https://<railway-url>.railway.app/api/inngest`
4. Click **Sync App**
5. Inngest will discover your registered functions automatically

---

## 6. Step 4: Backend Deployment (Railway)

### 6.1 Create Railway Account and Project

1. Go to [railway.app](https://railway.app) and sign up with GitHub
2. Click **New Project**
3. Select **Deploy from GitHub repo**
4. Authorize Railway to access your GitHub organization
5. Select the `nexus` repository

### 6.2 Configure Root Directory

After creating the service:

1. Click on your service → **Settings** tab
2. Under **Source** → **Root Directory**: enter `backend`
3. This tells Railway to build and run from the `nexus/backend/` folder

### 6.3 Create Procfile or Configure Start Command

Create `backend/Procfile`:
```
web: uvicorn main:app --host 0.0.0.0 --port $PORT --workers 2
```

Or set in Railway dashboard → **Settings** → **Start Command**:
```bash
uvicorn main:app --host 0.0.0.0 --port $PORT --workers 2
```

For production with more traffic, use Gunicorn with uvicorn workers:
```bash
gunicorn main:app -k uvicorn.workers.UvicornWorker --workers 4 --bind 0.0.0.0:$PORT
```

### 6.4 Create requirements.txt

Ensure `backend/requirements.txt` includes all dependencies:

```txt
fastapi>=0.110.0
uvicorn[standard]>=0.27.0
gunicorn>=21.2.0
supabase>=2.4.0
python-jose[cryptography]>=3.3.0
slowapi>=0.1.9
httpx>=0.27.0
pydantic>=2.6.0
python-multipart>=0.0.9
inngest>=0.3.0
getstream>=0.1.0
boto3>=1.34.0          # For Cloudflare R2 (S3-compatible)
langfuse>=2.0.0
sentry-sdk[fastapi]>=1.40.0
browser-use>=0.1.0
openai>=1.14.0
groq>=0.4.0
```

### 6.5 Set Environment Variables

In Railway dashboard → your service → **Variables** tab, add all of the following:

```env
# Supabase
SUPABASE_URL=https://<project-ref>.supabase.co
SUPABASE_ANON_KEY=<your-anon-key>
SUPABASE_SERVICE_ROLE_KEY=<your-service-role-key>
SUPABASE_JWT_SECRET=<your-jwt-secret>

# GetStream
GETSTREAM_API_KEY=<your-api-key>
GETSTREAM_API_SECRET=<your-api-secret>

# Inngest
INNGEST_EVENT_KEY=<your-event-key>
INNGEST_SIGNING_KEY=<your-signing-key>

# LLM Providers
OPENROUTER_API_KEY=<your-openrouter-key>
GROQ_API_KEY=<your-groq-key>
OPENAI_API_KEY=<your-openai-key>

# Voice / STT
DEEPGRAM_API_KEY=<your-deepgram-key>

# Billing
LEMONSQUEEZY_API_KEY=<your-ls-key>
LEMONSQUEEZY_WEBHOOK_SECRET=<your-webhook-secret>
LEMONSQUEEZY_STORE_ID=<your-store-id>
LEMONSQUEEZY_PRO_VARIANT_ID=<pro-variant-id>
LEMONSQUEEZY_POWER_VARIANT_ID=<power-variant-id>

# Storage (Cloudflare R2)
CLOUDFLARE_R2_ACCESS_KEY=<your-r2-access-key>
CLOUDFLARE_R2_SECRET_KEY=<your-r2-secret-key>
CLOUDFLARE_R2_BUCKET=nexus-files
CLOUDFLARE_R2_ENDPOINT=https://<account-id>.r2.cloudflarestorage.com

# Observability
LANGFUSE_SECRET_KEY=<your-langfuse-secret>
LANGFUSE_PUBLIC_KEY=<your-langfuse-public>
LANGFUSE_HOST=https://cloud.langfuse.com
SENTRY_DSN=<your-backend-sentry-dsn>

# Application
CORS_ALLOWED_ORIGINS=https://your-app.vercel.app
CONFIRMATION_TOKEN_SECRET=<generate-with: python -c "import secrets; print(secrets.token_urlsafe(32))">
APP_ENV=production
```

### 6.6 Generate Railway Domain

1. In Railway → your service → **Settings** → **Networking**
2. Click **Generate Domain**
3. Note the URL: `https://<random>.railway.app`
4. This is your `NEXT_PUBLIC_API_URL` for the frontend

### 6.7 Add Health Check

Create `backend/main.py` health endpoint:

```python
@app.get("/health")
async def health_check():
    return {"status": "ok", "version": "2.0.0", "env": os.environ.get("APP_ENV", "unknown")}
```

Configure in Railway → **Settings** → **Health Check**:
- **Health Check Path:** `/health`
- **Timeout:** 10 seconds

### 6.8 View Deployment Logs

```bash
# Using Railway CLI
railway login
railway link   # select your project and service
railway logs   # stream live logs
```

Or view in Railway dashboard → your service → **Logs** tab.

### 6.9 Verify Backend is Running

```bash
curl https://<your-railway-url>.railway.app/health
# Expected: {"status": "ok", "version": "2.0.0", "env": "production"}
```

---

## 7. Step 5: Frontend Deployment (Vercel)

### 7.1 Connect Repository to Vercel

1. Go to [vercel.com](https://vercel.com) and sign in with GitHub
2. Click **Add New Project**
3. Select the `nexus` repository from GitHub
4. Click **Import**

### 7.2 Configure Project Settings

On the configuration page:
- **Framework Preset:** Next.js (auto-detected)
- **Root Directory:** `frontend`
- **Build Command:** `pnpm build` (or `next build`)
- **Output Directory:** `.next` (default)
- **Install Command:** `pnpm install`

### 7.3 Set Environment Variables

In the Vercel configuration screen → **Environment Variables** section:

```env
NEXT_PUBLIC_SUPABASE_URL=https://<project-ref>.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=<your-anon-key>
NEXT_PUBLIC_API_URL=https://<your-railway-url>.railway.app
NEXT_PUBLIC_GETSTREAM_API_KEY=<your-getstream-api-key>
NEXT_PUBLIC_POSTHOG_KEY=<your-posthog-key>
NEXT_PUBLIC_POSTHOG_HOST=https://app.posthog.com
NEXT_PUBLIC_SENTRY_DSN=<your-frontend-sentry-dsn>
```

> Important: Only use `NEXT_PUBLIC_` prefix for values that can be exposed to the browser. Never put service role keys or secrets in the frontend.

### 7.4 Deploy

Click **Deploy**. Vercel will:
1. Clone the repository
2. Install pnpm dependencies
3. Run `next build`
4. Deploy to its global edge network

Watch the build logs for errors. Typical first build takes 1–3 minutes.

### 7.5 Note the Production URL

After deployment, Vercel shows: `https://nexus-<hash>.vercel.app`

You can add a custom domain in **Settings** → **Domains**.

### 7.6 Update Supabase Auth Redirect URLs

1. Go to Supabase Dashboard → **Authentication** → **URL Configuration**
2. **Site URL:** `https://nexus-<hash>.vercel.app` (or your custom domain)
3. **Redirect URLs:** Add `https://nexus-<hash>.vercel.app/auth/callback`
4. Save changes

### 7.7 Update Railway CORS

Go back to Railway → Variables, update:
```
CORS_ALLOWED_ORIGINS=https://nexus-<hash>.vercel.app
```

If you have a custom domain: `CORS_ALLOWED_ORIGINS=https://nexus-<hash>.vercel.app,https://www.yourcustomdomain.com`

Railway will auto-redeploy when variables change.

### 7.8 Verify Frontend

Open `https://nexus-<hash>.vercel.app` in a browser. You should see the Nexus landing page / login screen.

---

## 8. Step 6: LemonSqueezy Setup

### 8.1 Create Store

1. Go to [lemonsqueezy.com](https://lemonsqueezy.com) and sign up
2. Complete store setup: store name, currency (USD), timezone
3. Complete payment processor onboarding (Stripe integration handled by LemonSqueezy)
4. Note your **Store ID** from the URL: `https://app.lemonsqueezy.com/stores/<store-id>`

### 8.2 Create Products

**Pro Plan ($15/month):**
1. Dashboard → **Products** → **Add Product**
2. Name: `Nexus Pro`
3. Type: **Subscription**
4. Price: $15.00 / month
5. Add description and features
6. Publish the product
7. Note the **Variant ID** (visible in the URL or product details)

**Power Plan ($39/month):**
1. Repeat for `Nexus Power` at $39.00/month
2. Note the **Variant ID**

Update Railway environment variables:
```
LEMONSQUEEZY_PRO_VARIANT_ID=<pro-variant-id>
LEMONSQUEEZY_POWER_VARIANT_ID=<power-variant-id>
```

### 8.3 Get API Key

In LemonSqueezy → **Settings** → **API**:
1. Create API key with name `nexus-backend`
2. Copy the key → set as `LEMONSQUEEZY_API_KEY` in Railway

### 8.4 Configure Webhook

1. LemonSqueezy → **Settings** → **Webhooks**
2. Click **Add endpoint**
3. **URL:** `https://<your-railway-url>.railway.app/api/v1/billing/webhook`
4. **Events to subscribe:**
   - `subscription_created`
   - `subscription_updated`
   - `subscription_cancelled`
   - `subscription_expired`
   - `order_created`
5. Copy the **Signing Secret** → set as `LEMONSQUEEZY_WEBHOOK_SECRET` in Railway
6. Click **Save**

### 8.5 Test Checkout (Sandbox)

LemonSqueezy provides a test mode. To test:
1. In LemonSqueezy dashboard → toggle **Test Mode** on
2. Note test variant IDs (separate from production)
3. Create a test checkout link in your frontend
4. Complete checkout with LemonSqueezy's test card numbers
5. Verify your webhook endpoint receives the `subscription_created` event

### 8.6 Backend Webhook Handler

```python
# backend/api/v1/billing.py
from fastapi import APIRouter, Request
from backend.security.webhook import verify_lemonsqueezy_webhook
from backend.modules.billing.service import handle_subscription_event
import json

router = APIRouter()

@router.post("/webhook")
async def billing_webhook(request: Request):
    body = await verify_lemonsqueezy_webhook(request)
    event = json.loads(body)
    event_name = event["meta"]["event_name"]
    event_id = event["meta"]["custom_data"].get("event_id", event["data"]["id"])

    await handle_subscription_event(event_name, event["data"], event_id)
    return {"received": True}
```

---

## 9. Step 7: Cloudflare R2 Setup

### 9.1 Create R2 Bucket

1. Go to [cloudflare.com](https://dash.cloudflare.com) and sign in
2. Navigate to **R2 Object Storage** in the sidebar
3. Click **Create bucket**
4. Name: `nexus-files`
5. Region: Automatic (Cloudflare distributes globally)
6. Click **Create bucket**

### 9.2 Create API Token

1. In R2 → **Overview** → **Manage R2 API Tokens**
2. Click **Create API Token**
3. Token name: `nexus-backend`
4. Permissions: **Object Read & Write**
5. Specify bucket: `nexus-files` (restrict to this bucket only)
6. Click **Create API Token**
7. Copy **Access Key ID** and **Secret Access Key** — shown only once

### 9.3 Get Endpoint URL

1. In R2 → **Overview**, note your **Account ID**
2. R2 endpoint: `https://<account-id>.r2.cloudflarestorage.com`

Update Railway:
```
CLOUDFLARE_R2_ACCESS_KEY=<access-key-id>
CLOUDFLARE_R2_SECRET_KEY=<secret-access-key>
CLOUDFLARE_R2_BUCKET=nexus-files
CLOUDFLARE_R2_ENDPOINT=https://<account-id>.r2.cloudflarestorage.com
```

### 9.4 Backend R2 Client

```python
# backend/storage/r2.py
import boto3
from botocore.config import Config
import os

r2_client = boto3.client(
    "s3",
    endpoint_url=os.environ["CLOUDFLARE_R2_ENDPOINT"],
    aws_access_key_id=os.environ["CLOUDFLARE_R2_ACCESS_KEY"],
    aws_secret_access_key=os.environ["CLOUDFLARE_R2_SECRET_KEY"],
    config=Config(signature_version="s3v4"),
    region_name="auto",
)

R2_BUCKET = os.environ["CLOUDFLARE_R2_BUCKET"]

async def upload_file(user_id: str, filename: str, content: bytes, content_type: str) -> str:
    key = f"{user_id}/{filename}"
    r2_client.put_object(
        Bucket=R2_BUCKET,
        Key=key,
        Body=content,
        ContentType=content_type,
    )
    return key

async def get_presigned_url(key: str, expires_in: int = 3600) -> str:
    return r2_client.generate_presigned_url(
        "get_object",
        Params={"Bucket": R2_BUCKET, "Key": key},
        ExpiresIn=expires_in,
    )
```

---

## 10. Step 8: Observability Setup

### 10.1 Langfuse (LLM Tracing)

1. Go to [cloud.langfuse.com](https://cloud.langfuse.com) and sign up
2. Create a new project: `nexus-production`
3. Go to **Settings** → **API Keys**
4. Create a new key pair — note **Secret Key** and **Public Key**

Update Railway:
```
LANGFUSE_SECRET_KEY=<secret-key>
LANGFUSE_PUBLIC_KEY=<public-key>
LANGFUSE_HOST=https://cloud.langfuse.com
```

Initialize in `backend/core/telemetry.py`:

```python
from langfuse import Langfuse
import os

langfuse = Langfuse(
    secret_key=os.environ["LANGFUSE_SECRET_KEY"],
    public_key=os.environ["LANGFUSE_PUBLIC_KEY"],
    host=os.environ.get("LANGFUSE_HOST", "https://cloud.langfuse.com"),
)

def trace_llm_call(name: str, user_id: str, input_text: str, output_text: str, model: str, tokens: dict):
    trace = langfuse.trace(name=name, user_id=user_id)
    trace.generation(
        name=name,
        model=model,
        input=input_text,
        output=output_text,
        usage={"input": tokens.get("input", 0), "output": tokens.get("output", 0)},
    )
```

### 10.2 Posthog (Product Analytics)

1. Go to [posthog.com](https://posthog.com) and sign up
2. Create a new project: `Nexus`
3. Note the **Project API Key** (starts with `phc_`)

Update Vercel frontend environment variables:
```
NEXT_PUBLIC_POSTHOG_KEY=phc_<your-key>
NEXT_PUBLIC_POSTHOG_HOST=https://app.posthog.com
```

Initialize in `frontend/lib/posthog.ts`:

```typescript
import posthog from "posthog-js";

export function initPosthog() {
  if (typeof window !== "undefined") {
    posthog.init(process.env.NEXT_PUBLIC_POSTHOG_KEY!, {
      api_host: process.env.NEXT_PUBLIC_POSTHOG_HOST,
      capture_pageview: false,  // Disable automatic pageviews for SPA
      loaded: (ph) => {
        if (process.env.NODE_ENV === "development") ph.opt_out_capturing();
      },
    });
  }
}
```

### 10.3 Sentry (Error Tracking)

**Create two Sentry projects:**

1. Go to [sentry.io](https://sentry.io) and sign up
2. Create project → **FastAPI** → Name: `nexus-backend` → note DSN
3. Create project → **Next.js** → Name: `nexus-frontend` → note DSN

**Backend Sentry:**

```python
# backend/main.py
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
import os

sentry_sdk.init(
    dsn=os.environ.get("SENTRY_DSN"),
    integrations=[FastApiIntegration(), SqlalchemyIntegration()],
    traces_sample_rate=0.1,      # 10% of transactions
    environment=os.environ.get("APP_ENV", "development"),
    # Scrub sensitive data
    before_send=lambda event, hint: scrub_sensitive_fields(event),
)

def scrub_sensitive_fields(event: dict) -> dict:
    """Remove tokens and keys from Sentry events."""
    for key in ("authorization", "x-agent-token", "password", "token"):
        if "request" in event and "headers" in event["request"]:
            event["request"]["headers"].pop(key, None)
    return event
```

Update Railway:
```
SENTRY_DSN=<backend-dsn>
```

**Frontend Sentry:**

```bash
cd frontend
pnpm add @sentry/nextjs
npx @sentry/wizard@latest -i nextjs
```

Update Vercel:
```
NEXT_PUBLIC_SENTRY_DSN=<frontend-dsn>
```

---

## 11. Step 9: Windows Agent Distribution

### 11.1 Package the Agent

The Windows agent (`nexus/windows_agent/`) must be compiled into a standalone `.exe` so users don't need Python installed.

**On a Windows machine (or Windows VM):**

```bash
# Install PyInstaller
pip install pyinstaller

# Navigate to agent directory
cd nexus/windows_agent

# Build single-file executable
pyinstaller \
  --onefile \
  --name NexusAgent \
  --add-data "policy.py;." \
  --add-data "security.py;." \
  --hidden-import=uvicorn \
  --hidden-import=fastapi \
  main.py

# Output: dist/NexusAgent.exe
```

### 11.2 Agent First-Run Setup

On first launch, the agent:

1. Generates a unique agent token (256-bit random)
2. Saves it to `%APPDATA%\Nexus\agent_config.json`
3. Displays a QR code or link for pairing with the Nexus cloud account

```python
# windows_agent/main.py
import secrets
import json
import os
import uvicorn
from fastapi import FastAPI

CONFIG_PATH = os.path.join(os.environ["APPDATA"], "Nexus", "agent_config.json")

def first_run_setup():
    os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
    token = secrets.token_urlsafe(32)
    config = {"agent_token": token, "version": "1.0", "paired": False}
    with open(CONFIG_PATH, "w") as f:
        json.dump(config, f, indent=2)

    pairing_url = f"https://nexus-app.vercel.app/pair?token={token}"
    print(f"\nTo connect this agent to your Nexus account, visit:\n{pairing_url}\n")
    return config

def load_or_create_config() -> dict:
    if not os.path.exists(CONFIG_PATH):
        return first_run_setup()
    with open(CONFIG_PATH) as f:
        return json.load(f)

if __name__ == "__main__":
    config = load_or_create_config()
    os.environ["NEXUS_AGENT_TOKEN"] = config["agent_token"]
    uvicorn.run("app:app", host="127.0.0.1", port=8765, log_level="warning")
```

### 11.3 Agent Pairing API

The backend `/api/v1/agent/pair` endpoint stores the token against the user's account:

```python
# backend/api/v1/agent.py
@router.post("/pair")
async def pair_agent(
    body: AgentPairRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Store the user's Windows agent token in their account."""
    # Encrypt token before storing
    encrypted_token = encrypt_agent_token(body.token)
    await update_user_agent_token(db, user.id, encrypted_token)
    return {"paired": True}
```

### 11.4 Auto-Update (Future)

When distributing `.exe` updates, use a GitHub Releases page as the update server. The agent checks for updates on startup:

```python
import httpx

async def check_for_updates(current_version: str):
    resp = await httpx.get(
        "https://api.github.com/repos/your-org/nexus/releases/latest"
    )
    latest = resp.json()["tag_name"].lstrip("v")
    if latest != current_version:
        print(f"Update available: v{latest}. Download at: {resp.json()['html_url']}")
```

### 11.5 Windows Startup Registration (Optional)

To start the agent automatically on Windows login:

```python
import winreg

def register_autostart():
    key = winreg.OpenKey(
        winreg.HKEY_CURRENT_USER,
        r"Software\Microsoft\Windows\CurrentVersion\Run",
        0, winreg.KEY_SET_VALUE
    )
    exe_path = os.path.abspath("NexusAgent.exe")
    winreg.SetValueEx(key, "NexusAgent", 0, winreg.REG_SZ, exe_path)
    winreg.CloseKey(key)
```

---

## 12. Health Checks & Smoke Tests

Run these after every deployment to verify the full system is operational.

### 12.1 Infrastructure Health

```bash
# 1. Backend health endpoint
curl -s https://<railway-url>.railway.app/health
# Expected: {"status": "ok", "version": "2.0.0", "env": "production"}

# 2. Frontend loads
curl -I https://<vercel-url>.vercel.app
# Expected: HTTP/2 200

# 3. Supabase connectivity
curl -s "https://<project>.supabase.co/rest/v1/" \
  -H "apikey: <anon-key>"
# Expected: {"hint":"...","details":"..."}  (any JSON response = connected)
```

### 12.2 API Integration Smoke Tests

Run these tests sequentially:

```bash
BASE_URL="https://<railway-url>.railway.app/api/v1"

# --- Test 1: User signup ---
curl -X POST "$BASE_URL/auth/signup" \
  -H "Content-Type: application/json" \
  -d '{"email": "test-smoke@example.com", "password": "TestPass123!"}' \
  | jq .
# Expected: {"user": {...}, "access_token": "..."}

# Save the token
ACCESS_TOKEN="<token-from-above>"

# --- Test 2: Create session ---
curl -X POST "$BASE_URL/sessions" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"entry_mode": "text", "active_mode": "assistant"}' \
  | jq .
# Expected: {"id": "...", "user_id": "...", "started_at": "..."}

SESSION_ID="<session-id-from-above>"

# --- Test 3: Send conversation turn ---
curl -X POST "$BASE_URL/sessions/$SESSION_ID/turns" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"content": "Hello Nexus!", "role": "user", "input_mode": "text"}' \
  | jq .
# Expected: {"id": 1, "session_id": "...", ...}

# --- Test 4: SSE stream ---
curl -N -H "Authorization: Bearer $ACCESS_TOKEN" \
  "$BASE_URL/sessions/$SESSION_ID/stream"
# Expected: data: {...} stream events

# --- Test 5: Queue browser task (requires Inngest connected) ---
curl -X POST "$BASE_URL/tasks/browser" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"session_id\": \"$SESSION_ID\", \"url\": \"https://example.com\", \"goal\": \"Get the page title\"}" \
  | jq .
# Expected: {"task_id": "...", "status": "pending"}

# --- Test 6: Voice call creation ---
curl -X POST "$BASE_URL/voice/calls" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"session_id\": \"$SESSION_ID\"}" \
  | jq .
# Expected: {"call_id": "...", "token": "..."}

# --- Test 7: Billing webhook (signature test) ---
# Use LemonSqueezy's webhook test feature in their dashboard
# Click "Send test event" → verify your endpoint responds 200
```

### 12.3 Smoke Test Checklist

- [ ] `GET /health` → 200 `{"status": "ok"}`
- [ ] `POST /api/v1/auth/signup` → creates user in Supabase Auth and users table
- [ ] `POST /api/v1/auth/login` → returns JWT access token
- [ ] `POST /api/v1/sessions` → creates session record
- [ ] `GET /api/v1/sessions/{id}/stream` → SSE connection opens
- [ ] `POST /api/v1/tasks/browser` → task created, Inngest job queued (visible in Inngest dashboard)
- [ ] `POST /api/v1/voice/calls` → GetStream call created, token returned
- [ ] LemonSqueezy webhook test → backend receives and acknowledges
- [ ] Frontend loads in browser without console errors
- [ ] Frontend Supabase auth → signup and login flow completes
- [ ] Frontend connects to backend API without CORS errors
- [ ] Sentry: no errors appearing in dashboard from smoke tests
- [ ] Langfuse: LLM traces appearing in dashboard

---

## 13. Rollback Procedures

### 13.1 Backend Rollback (Railway)

Railway keeps a full deployment history and supports instant rollbacks:

**Via Dashboard:**
1. Railway dashboard → your service → **Deployments** tab
2. Find the last known-good deployment
3. Click the three-dot menu → **Rollback to this deployment**
4. Railway will instantly switch traffic to the previous container

**Via CLI:**
```bash
railway deployments list        # View deployment history
railway deployments rollback    # Interactive rollback to selected deployment
```

Rollback completes in approximately 30 seconds (no container rebuild required).

### 13.2 Frontend Rollback (Vercel)

**Via Dashboard:**
1. Vercel dashboard → your project → **Deployments** tab
2. Find the previous good deployment
3. Click the three-dot menu → **Promote to Production**
4. Traffic instantly redirects (edge network reroutiing, no rebuild)

**Via CLI:**
```bash
vercel rollback   # Reverts to the previous production deployment
```

### 13.3 Database Migrations — Never Destructive

**Rule: Never run destructive migrations without a backup.**

**Before any migration in production:**

```bash
# 1. Take a manual snapshot in Supabase Dashboard
# Dashboard → Settings → Database → Backups → Create snapshot
# Label it: "pre-migration-YYYY-MM-DD"

# 2. Or pg_dump if you have direct DB access
pg_dump "postgresql://postgres:<password>@<host>:5432/postgres" \
  --no-owner --no-acl \
  > backup_$(date +%Y%m%d_%H%M%S).sql
```

**Migration strategy:**
1. Write migrations as **additive only** (new columns with defaults, new tables)
2. Deploy the new backend code that handles both old and new schema
3. Run the migration
4. Verify the new code works with the new schema
5. In a follow-up release, remove old code paths

**To restore from backup:**
```bash
# Restore from pg_dump
psql "postgresql://postgres:<password>@<host>:5432/postgres" < backup_20250115_120000.sql
```

For Supabase automated backups (Pro plan), restore via Dashboard → Settings → Database → Backups.

### 13.4 Inngest Rollback

Inngest jobs that are queued but not yet executed will continue with the current function code. If a bug is introduced:

1. Roll back the backend deployment (the function code is in the backend)
2. Inngest will retry failed runs against the rolled-back code
3. If jobs were corrupted, cancel them in Inngest dashboard → **Runs** → filter by function → cancel

### 13.5 Incident Response Runbook

```
1. Alert fires (Sentry, Railway logs, user reports)
2. Assess severity:
   - P1 (complete outage): all users affected
   - P2 (degraded): feature broken for subset
   - P3 (cosmetic): visual bugs, non-critical
3. For P1/P2: rollback backend and/or frontend immediately
4. Communicate via status page (optional: statuspage.io free tier)
5. Investigate root cause using Sentry, Railway logs, Langfuse traces
6. Write post-mortem after resolution
```

---

## 14. Environment Promotion

### 14.1 Environment Strategy

Use three environments: **local → staging → production**

| Environment | Supabase Project | Railway Environment | Vercel | Branch |
|---|---|---|---|---|
| Local | `nexus-dev` | N/A | `localhost:3000` | `feature/*` |
| Staging | `nexus-staging` | `staging` | Preview URL | `main` |
| Production | `nexus-production` | `production` | `nexus.yourdomain.com` | `release/*` |

### 14.2 Supabase Environment Separation

Create **separate Supabase projects** for staging and production. Never share a database between environments:

```bash
# Staging project: nexus-staging
# Production project: nexus-production

# Apply migrations to staging first
supabase link --project-ref <staging-ref>
supabase db push

# Verify on staging
# Then apply to production
supabase link --project-ref <production-ref>
supabase db push
```

### 14.3 Railway Environments

1. In Railway → your project → click **+ New Environment**
2. Create: `staging` and `production`
3. Each environment has its own set of variables and deployments
4. Configure staging to deploy from `main` branch auto-deploy
5. Configure production to deploy from `release/*` tags only (manual trigger)

```bash
# Deploy to staging
git push origin main     # Auto-deploys to Railway staging

# Deploy to production (after staging verification)
git tag v2.0.1
git push origin v2.0.1   # Triggers Railway production deploy
```

### 14.4 Vercel Preview Deployments

Vercel automatically creates a Preview deployment for every pull request:
- Preview URL: `https://nexus-git-<branch>-<org>.vercel.app`
- Uses staging environment variables
- Useful for QA and design review before merging

### 14.5 Promotion Checklist

Before promoting staging → production:

- [ ] All smoke tests pass on staging
- [ ] No critical Sentry errors in staging over the last 24 hours
- [ ] DB migrations tested on staging database
- [ ] Environment variables diff reviewed (no secrets missing in production)
- [ ] Rollback plan documented if migration is involved
- [ ] Deployment window communicated if > 30 seconds downtime expected

---

## 15. Ongoing Maintenance

### 15.1 Dependency Updates

```bash
# Backend (monthly)
pip list --outdated
pip install --upgrade <package>
# Run test suite after updates

# Frontend (monthly)
cd frontend
pnpm outdated
pnpm update
pnpm build   # Verify no build errors
```

### 15.2 Database Maintenance

```sql
-- Supabase runs VACUUM automatically, but for large tables:
VACUUM ANALYZE tasks;
VACUUM ANALYZE conversation_turns;
VACUUM ANALYZE tool_runs;

-- Monitor table sizes (run monthly):
SELECT
  schemaname,
  tablename,
  pg_size_pretty(pg_total_relation_size(schemaname || '.' || tablename)) AS size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname || '.' || tablename) DESC;
```

### 15.3 Log Retention

- Railway logs: 7 days on Starter plan (export important events to Langfuse/Sentry)
- Supabase logs: 7 days on Free plan, 30 days on Pro
- Sentry: 30 days on Free plan
- Langfuse: 30 days on Free plan

### 15.4 Cost Monitoring

Set up billing alerts for each service:

| Service | Free Limit | Alert Threshold |
|---|---|---|
| Supabase | 500MB DB, 2GB bandwidth | 80% of limit |
| Railway | $5/mo credit included | $20/mo spend |
| Vercel | 100GB bandwidth/mo | 80% of limit |
| GetStream | 10,000 MAU | 8,000 MAU |
| Inngest | 50,000 runs/mo | 40,000 runs/mo |
| Cloudflare R2 | 10GB storage, 1M Class A ops | 8GB storage |

### 15.5 Security Maintenance

- Rotate all API keys every 90 days (set calendar reminder)
- Review Sentry error trends weekly
- Review Langfuse traces for prompt injection attempts (weekly)
- Apply Python security patches within 7 days of announcement
- Run `pip audit` monthly: `pip install pip-audit && pip-audit`

### 15.6 Backup Verification

Monthly, verify backups are restorable:
1. Supabase → Settings → Backups → restore to a test project
2. Verify schema is intact and data is readable
3. Delete the test project

---

*This runbook should be kept in sync with infrastructure changes. When you add a new service or change a deployment step, update this document immediately.*
