# Nexus 2.0 — Monetization Model

**Version:** 1.0  
**Last Updated:** 2025  
**Stack:** FastAPI + Supabase + Inngest + LemonSqueezy + Next.js/Vercel

---

## Table of Contents

1. [Overview & Strategy](#1-overview--strategy)
2. [Tier Definitions](#2-tier-definitions)
3. [DB Schema for Billing](#3-db-schema-for-billing)
4. [Quota Middleware Design](#4-quota-middleware-design)
5. [Usage Tracking](#5-usage-tracking)
6. [LemonSqueezy Integration](#6-lemonsqueezy-integration)
7. [Upgrade Prompt UX Design](#7-upgrade-prompt-ux-design)
8. [Priority Queue Logic](#8-priority-queue-logic)
9. [Revenue Projections](#9-revenue-projections)

---

## 1. Overview & Strategy

### Why This Tier Structure Makes Sense for a Voice AI Assistant

Nexus 2.0 operates in a category where perceived value is tightly coupled to task completion speed, breadth of capability, and reliability. Users who experience the product working — actually automating their browser, controlling Windows, running research tasks — will pay. The monetization model is designed around that insight: get them hooked on the free tier, then make the limits feel real.

**Three-tier structure rationale:**

| Tier | Purpose | Price Anchor |
|---|---|---|
| Free | Acquisition engine — zero friction to try | $0 — no card required |
| Pro | Bread-and-butter revenue — power users who use daily | $15/mo — less than Netflix |
| Power | High-LTV segment — professionals and teams | $39/mo — less than one hour of consulting |

The limits are calibrated so that a casual user stays on Free indefinitely, a daily driver hits Pro limits within 1–2 weeks, and a professional/power user hits Power limits within 1 week of Pro. This creates natural upgrade pressure without artificial paywalling.

### Free Tier as Acquisition Engine

The Free tier exists for one reason: **acquire users with zero friction and let the product sell itself**.

- No credit card required at signup
- 20 normal tasks/month = enough to prove the product works (~1 task/weekday)
- 5 browser automation tasks = enough for a WOW moment (watching the browser execute autonomously)
- English-only and no research mode = clear functional gap that power users will notice

The product is inherently viral in demos — watching an AI control your browser or Windows desktop is share-worthy. Free tier users who become advocates are worth more than their $0 revenue suggests.

**Free → Pro trigger:** Users will naturally hit the 5 browser task limit in under a week if they're genuinely using the product. That moment is the primary upgrade trigger.

### Upgrade Triggers

Upgrade prompts appear at these moments:

1. **Hard quota hit** — User attempts a task and is blocked (HTTP 402). The error response includes a checkout URL.
2. **80% quota warning** — When usage reaches 80% of monthly limit, the API response includes an `X-Quota-Warning` header. The frontend surfaces a soft banner: *"You've used 16/20 tasks this month. Upgrade to Pro for 200."*
3. **Feature gate** — User attempts to enable Research Mode (free: disabled) or switches language to non-English. Response explains the feature is Pro+.
4. **End of month summary** — Email sent on the 28th if the user is on Free and has hit >60% usage.
5. **Post-task upsell** — After a particularly long task completes (>30s), surface: *"This task ran faster for Pro users with priority queue. Upgrade?"*

### LTV Estimates at Each Tier

Assumptions: monthly churn of 8% for Pro, 4% for Power (Power users are more invested).

| Tier | Monthly Revenue | Avg. Months Retained | LTV |
|---|---|---|---|
| Free | $0 | — | $0 direct / $5–$30 referral value |
| Pro ($15/mo) | $15 | ~12.5 months | **~$187** |
| Power ($39/mo) | $39 | ~25 months | **~$975** |

At 5% LemonSqueezy transaction fee, net revenue per Pro user/month is $14.25. Net Power: $37.05.

**CAC target:** Keep blended CAC under $15 (= 1 month of Pro). With a free tier that converts organically, this is achievable if the product is genuinely good.

---

## 2. Tier Definitions

### Full Feature Comparison

| Feature | Free | Pro ($15/mo) | Power ($39/mo) |
|---|---|---|---|
| Normal tasks/month | 20 | 200 | Unlimited |
| Browser automation tasks/month | 5 | 50 | 500 |
| Voice mode | ✅ | ✅ | ✅ |
| Languages | English only | All | All |
| Research mode | ❌ | Basic | Full |
| Task priority | Standard (0) | High (5) | Highest (10) |
| Memory retention | 30 days | 1 year | Unlimited |
| Max task execution time | 60 seconds | 5 minutes | 15 minutes |
| Concurrent tasks | 1 | 2 | 5 |
| API access | ❌ | ❌ | ✅ |
| Support | Community (Discord) | Email (48h SLA) | Priority (8h SLA) |
| Custom wake word | ❌ | ❌ | ✅ |
| Export task history | ❌ | ✅ | ✅ |
| Webhook notifications | ❌ | ❌ | ✅ |
| Team seats | 1 | 1 | Up to 3 (future) |

### Plan Limits as Constants (Python)

```python
# app/core/plan_limits.py

from dataclasses import dataclass
from typing import Optional


@dataclass
class PlanLimits:
    normal_tasks_per_month: Optional[int]       # None = unlimited
    browser_tasks_per_month: Optional[int]
    research_tasks_per_month: Optional[int]
    max_execution_seconds: int
    concurrent_tasks: int
    memory_retention_days: Optional[int]        # None = unlimited
    priority: int                               # Inngest job priority
    languages: list[str]                        # ["en"] or ["*"]
    research_mode: str                          # "none" | "basic" | "full"
    api_access: bool


PLAN_LIMITS: dict[str, PlanLimits] = {
    "free": PlanLimits(
        normal_tasks_per_month=20,
        browser_tasks_per_month=5,
        research_tasks_per_month=0,
        max_execution_seconds=60,
        concurrent_tasks=1,
        memory_retention_days=30,
        priority=0,
        languages=["en"],
        research_mode="none",
        api_access=False,
    ),
    "pro": PlanLimits(
        normal_tasks_per_month=200,
        browser_tasks_per_month=50,
        research_tasks_per_month=20,
        max_execution_seconds=300,
        concurrent_tasks=2,
        memory_retention_days=365,
        priority=5,
        languages=["*"],
        research_mode="basic",
        api_access=False,
    ),
    "power": PlanLimits(
        normal_tasks_per_month=None,
        browser_tasks_per_month=500,
        research_tasks_per_month=None,
        max_execution_seconds=900,
        concurrent_tasks=5,
        memory_retention_days=None,
        priority=10,
        languages=["*"],
        research_mode="full",
        api_access=True,
    ),
}
```

---

## 3. DB Schema for Billing

All billing state lives in Supabase Postgres. No external billing database is used — LemonSqueezy is the source of truth for payment events, but Nexus mirrors the minimal state needed for quota enforcement.

### Users Table Additions

```sql
-- Migration: add billing columns to users table
-- File: supabase/migrations/20250101000001_add_billing_to_users.sql

ALTER TABLE users ADD COLUMN IF NOT EXISTS
    plan VARCHAR(20) NOT NULL DEFAULT 'free'
    CHECK (plan IN ('free', 'pro', 'power'));

ALTER TABLE users ADD COLUMN IF NOT EXISTS
    plan_updated_at TIMESTAMPTZ;

ALTER TABLE users ADD COLUMN IF NOT EXISTS
    plan_expires_at TIMESTAMPTZ;   -- null = never (monthly rolling)

ALTER TABLE users ADD COLUMN IF NOT EXISTS
    lemon_squeezy_customer_id VARCHAR(100) UNIQUE;

ALTER TABLE users ADD COLUMN IF NOT EXISTS
    lemon_squeezy_subscription_id VARCHAR(100) UNIQUE;

ALTER TABLE users ADD COLUMN IF NOT EXISTS
    lemon_squeezy_variant_id VARCHAR(100);   -- which product variant

ALTER TABLE users ADD COLUMN IF NOT EXISTS
    billing_email VARCHAR(255);              -- may differ from auth email

-- Index for webhook lookups
CREATE INDEX IF NOT EXISTS idx_users_ls_customer
    ON users(lemon_squeezy_customer_id)
    WHERE lemon_squeezy_customer_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_users_ls_subscription
    ON users(lemon_squeezy_subscription_id)
    WHERE lemon_squeezy_subscription_id IS NOT NULL;
```

### billing_usage Table

```sql
-- Migration: create billing_usage table
-- File: supabase/migrations/20250101000002_create_billing_usage.sql

CREATE TABLE IF NOT EXISTS billing_usage (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    metric          VARCHAR(50) NOT NULL
                    CHECK (metric IN ('task_run', 'browser_task', 'research_task')),
    period          CHAR(7) NOT NULL,  -- format: YYYY-MM (e.g. '2025-01')
    count           INTEGER NOT NULL DEFAULT 0,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- One row per user/metric/period
    CONSTRAINT uq_billing_usage_user_metric_period
        UNIQUE (user_id, metric, period)
);

-- Index for fast quota checks
CREATE INDEX IF NOT EXISTS idx_billing_usage_user_period
    ON billing_usage(user_id, period);

-- Row-level security: users can only read their own usage
ALTER TABLE billing_usage ENABLE ROW LEVEL SECURITY;

CREATE POLICY billing_usage_select_own ON billing_usage
    FOR SELECT
    USING (auth.uid() = user_id);

-- Only backend service role can write
CREATE POLICY billing_usage_insert_service ON billing_usage
    FOR ALL
    USING (auth.role() = 'service_role');
```

### Helper Function: Atomic Increment

```sql
-- Atomic upsert function to increment usage counter
-- Called by the Inngest worker after task completion

CREATE OR REPLACE FUNCTION increment_billing_usage(
    p_user_id   UUID,
    p_metric    VARCHAR(50),
    p_period    CHAR(7)
) RETURNS void AS $$
BEGIN
    INSERT INTO billing_usage (user_id, metric, period, count)
    VALUES (p_user_id, p_metric, p_period, 1)
    ON CONFLICT (user_id, metric, period)
    DO UPDATE SET
        count      = billing_usage.count + 1,
        updated_at = NOW();
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;
```

---

## 4. Quota Middleware Design

Quota enforcement is implemented as a FastAPI dependency, not middleware, because it needs access to request-specific context (task type, authenticated user). It's injected at the route level for any endpoint that creates tasks.

### Full Implementation

```python
# app/dependencies/quota.py

from __future__ import annotations

import calendar
from datetime import datetime
from typing import Literal

from fastapi import Depends, HTTPException, Request, Response
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.plan_limits import PLAN_LIMITS
from app.db.session import get_db
from app.models.user import User
from app.dependencies.auth import get_current_user


TaskType = Literal["normal", "browser", "research"]

METRIC_MAP: dict[TaskType, str] = {
    "normal":   "task_run",
    "browser":  "browser_task",
    "research": "research_task",
}

LIMIT_FIELD_MAP: dict[TaskType, str] = {
    "normal":   "normal_tasks_per_month",
    "browser":  "browser_tasks_per_month",
    "research": "research_tasks_per_month",
}


class QuotaExceededError(HTTPException):
    """HTTP 402 with structured quota exceeded payload."""
    pass


async def check_quota(
    task_type: TaskType,
    request: Request,
    response: Response,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """
    Raises HTTP 402 if the user has hit their monthly limit for task_type.
    Adds X-Quota-Warning header if usage is >= 80% of limit.

    Designed to be used as a FastAPI dependency:

        @router.post("/tasks")
        async def create_task(
            body: CreateTaskRequest,
            _quota: None = Depends(lambda req, res, u, db: check_quota("browser", req, res, u, db)),
        ):
            ...
    """
    plan = user.plan or "free"
    limits = PLAN_LIMITS[plan]
    limit_field = LIMIT_FIELD_MAP[task_type]
    limit: int | None = getattr(limits, limit_field)

    # Unlimited plan — skip quota check
    if limit is None:
        return

    # Zero limit (e.g., free user trying research) — immediate block
    if limit == 0:
        _raise_quota_exceeded(task_type, 0, 0, plan)

    # Current period: YYYY-MM
    period = datetime.utcnow().strftime("%Y-%m")
    metric = METRIC_MAP[task_type]

    # Fetch current usage count
    result = await db.execute(
        text("""
            SELECT COALESCE(count, 0) AS count
            FROM billing_usage
            WHERE user_id = :user_id
              AND metric   = :metric
              AND period   = :period
        """),
        {"user_id": str(user.id), "metric": metric, "period": period},
    )
    row = result.fetchone()
    current_count: int = row.count if row else 0

    # Hard quota exceeded
    if current_count >= limit:
        _raise_quota_exceeded(task_type, current_count, limit, plan)

    # Soft warning: >= 80% used
    warning_threshold = int(limit * 0.8)
    if current_count >= warning_threshold:
        remaining = limit - current_count
        response.headers["X-Quota-Warning"] = (
            f"usage={current_count};limit={limit};remaining={remaining};"
            f"metric={metric};period={period}"
        )


def _raise_quota_exceeded(
    task_type: TaskType,
    current_count: int,
    limit: int,
    current_plan: str,
) -> None:
    """Build and raise a structured 402 response."""
    type_labels = {
        "normal":   ("normal task", "normal_tasks"),
        "browser":  ("browser automation task", "browser_tasks"),
        "research": ("research task", "research_tasks"),
    }
    label, key = type_labels[task_type]

    raise HTTPException(
        status_code=402,
        detail={
            "error": "quota_exceeded",
            "message": (
                f"You've used all {limit} {label}s this month "
                f"on the {current_plan.title()} plan."
                if limit > 0
                else f"Research mode is not available on the {current_plan.title()} plan."
            ),
            "current_plan": current_plan,
            "current_usage": current_count,
            "limit": limit,
            "upgrade_url": "https://nexus.app/upgrade",
            "plan_comparison": {
                "pro": {
                    key: PLAN_LIMITS["pro"].__dict__.get(
                        LIMIT_FIELD_MAP[task_type], 0
                    ),
                    "price": "$15/mo",
                },
                "power": {
                    key: PLAN_LIMITS["power"].__dict__.get(
                        LIMIT_FIELD_MAP[task_type], "Unlimited"
                    ),
                    "price": "$39/mo",
                },
            },
        },
    )
```

### Using the Dependency in Routes

```python
# app/api/v1/tasks.py

from fastapi import APIRouter, Depends
from app.dependencies.quota import check_quota
from app.dependencies.auth import get_current_user

router = APIRouter(prefix="/tasks", tags=["tasks"])


def browser_quota_dep(
    request: Request,
    response: Response,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    return check_quota("browser", request, response, user, db)


@router.post("/browser", status_code=202)
async def create_browser_task(
    body: CreateBrowserTaskRequest,
    user: User = Depends(get_current_user),
    _quota: None = Depends(browser_quota_dep),
    db: AsyncSession = Depends(get_db),
):
    """Create a browser automation task. Quota enforced before task creation."""
    ...
```

---

## 5. Usage Tracking

### Core Principle

Usage is tracked **after a task completes successfully**, not when it's submitted. This prevents charging quota for tasks that fail immediately (e.g., invalid input). Retried tasks count as one usage unit — the counter increments once per user-initiated task, not per Inngest function attempt.

### Tracking via Inngest (Async, Non-Blocking)

After a task function completes, the Inngest worker sends a `nexus/usage.increment` event. This keeps usage tracking completely decoupled from the task execution path.

```python
# Inside any Inngest task function, after successful completion:

async def handle_browser_task(ctx: inngest.Context, step: inngest.Step) -> dict:
    task_id = ctx.event.data["task_id"]
    user_id = ctx.event.data["user_id"]

    # ... execute task ...
    result = await step.run("execute-browser-task", _execute_browser)

    # After success, track usage asynchronously
    await step.send_event(
        "track-usage",
        inngest.Event(
            name="nexus/usage.increment",
            data={
                "user_id": user_id,
                "metric": "browser_task",
                "task_id": task_id,
            },
        ),
    )

    return result
```

### Usage Increment Function

```python
# services/inngest_functions/usage_tracking.py

@inngest_client.create_function(
    fn_id="nexus/usage-increment",
    trigger=inngest.TriggerEvent(event="nexus/usage.increment"),
    retries=5,  # Retry aggressively — missed increments cause billing errors
)
async def handle_usage_increment(
    ctx: inngest.Context, step: inngest.Step
) -> dict:
    """
    Atomically increment billing_usage for a completed task.
    Runs asynchronously — never blocks the task response to client.
    """
    data = ctx.event.data
    user_id: str = data["user_id"]
    metric: str = data["metric"]
    period = datetime.utcnow().strftime("%Y-%m")

    async def _increment():
        async with get_async_db_session() as db:
            await db.execute(
                text("SELECT increment_billing_usage(:user_id, :metric, :period)"),
                {"user_id": user_id, "metric": metric, "period": period},
            )
            await db.commit()
        return {"incremented": True, "user_id": user_id, "metric": metric}

    result = await step.run("increment-db", _increment)
    return result
```

### Period Reset Logic

There is no active reset job. Usage is scoped by `period = YYYY-MM`. A new month naturally starts a new row with `count = 0`. This means:

- No cron job needed
- No risk of accidentally resetting mid-period
- Historical usage data is preserved (useful for analytics)
- Old rows can be archived/deleted after 13 months if storage is a concern

```sql
-- Optional: cleanup job (run via pg_cron monthly, retain 13 months)
DELETE FROM billing_usage
WHERE period < TO_CHAR(NOW() - INTERVAL '13 months', 'YYYY-MM');
```

### Usage API Endpoint

```python
# app/api/v1/users.py

@router.get("/me/usage")
async def get_my_usage(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UsageResponse:
    """
    Returns current period usage stats and limits for the authenticated user.
    Used by the frontend to render usage bars and quota warnings.
    """
    period = datetime.utcnow().strftime("%Y-%m")
    plan = user.plan or "free"
    limits = PLAN_LIMITS[plan]

    result = await db.execute(
        text("""
            SELECT metric, count
            FROM billing_usage
            WHERE user_id = :user_id AND period = :period
        """),
        {"user_id": str(user.id), "period": period},
    )
    rows = {row.metric: row.count for row in result.fetchall()}

    # Days remaining in period
    now = datetime.utcnow()
    last_day = calendar.monthrange(now.year, now.month)[1]
    days_remaining = last_day - now.day

    return UsageResponse(
        period=period,
        days_remaining=days_remaining,
        plan=plan,
        usage={
            "normal_tasks": {
                "used":  rows.get("task_run", 0),
                "limit": limits.normal_tasks_per_month,
            },
            "browser_tasks": {
                "used":  rows.get("browser_task", 0),
                "limit": limits.browser_tasks_per_month,
            },
            "research_tasks": {
                "used":  rows.get("research_task", 0),
                "limit": limits.research_tasks_per_month,
            },
        },
    )
```

---

## 6. LemonSqueezy Integration

LemonSqueezy is chosen as the primary billing provider because:
- No monthly platform fee (only 5% per transaction)
- Handles global tax compliance automatically (EU VAT, US sales tax)
- Clean hosted checkout (no PCI scope for Nexus)
- Good webhook reliability
- Works well for indie/bootstrapped projects at early scale

### Step 1: LemonSqueezy Dashboard Setup

1. Create a **Store** in the LemonSqueezy dashboard
2. Create two **Products** (subscriptions):
   - **Nexus Pro** → Monthly variant at $15/mo, Annual at $144/yr (2 months free)
   - **Nexus Power** → Monthly at $39/mo, Annual at $374/yr (2 months free)
3. Note the **Variant IDs** for each product variant — these map to your plan names
4. Create a **Webhook** pointing to `https://api.nexus.app/api/v1/billing/webhook`
   - Events to subscribe: `subscription_created`, `subscription_updated`, `subscription_cancelled`, `subscription_expired`, `subscription_payment_success`, `subscription_payment_failed`

### Step 2: Environment Variables

```bash
# .env
LEMONSQUEEZY_API_KEY=your_api_key_here
LEMONSQUEEZY_WEBHOOK_SECRET=your_webhook_secret_here
LEMONSQUEEZY_STORE_ID=12345

# Variant IDs from dashboard
LEMONSQUEEZY_PRO_MONTHLY_VARIANT_ID=111111
LEMONSQUEEZY_PRO_ANNUAL_VARIANT_ID=111112
LEMONSQUEEZY_POWER_MONTHLY_VARIANT_ID=222221
LEMONSQUEEZY_POWER_ANNUAL_VARIANT_ID=222222
```

### Step 3: Generate Checkout URL

```python
# app/api/v1/billing.py

import httpx
from fastapi import APIRouter, Depends, HTTPException
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.core.config import settings

router = APIRouter(prefix="/billing", tags=["billing"])


class CheckoutRequest(BaseModel):
    plan: Literal["pro", "power"]
    billing_period: Literal["monthly", "annual"] = "monthly"


@router.post("/checkout")
async def create_checkout(
    body: CheckoutRequest,
    user: User = Depends(get_current_user),
) -> dict:
    """
    Generate a LemonSqueezy hosted checkout URL for the requested plan.
    Returns the URL for the frontend to redirect to.
    """
    variant_map = {
        ("pro",   "monthly"): settings.LS_PRO_MONTHLY_VARIANT_ID,
        ("pro",   "annual"):  settings.LS_PRO_ANNUAL_VARIANT_ID,
        ("power", "monthly"): settings.LS_POWER_MONTHLY_VARIANT_ID,
        ("power", "annual"):  settings.LS_POWER_ANNUAL_VARIANT_ID,
    }
    variant_id = variant_map.get((body.plan, body.billing_period))
    if not variant_id:
        raise HTTPException(400, "Invalid plan/period combination")

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "https://api.lemonsqueezy.com/v1/checkouts",
            headers={
                "Authorization": f"Bearer {settings.LEMONSQUEEZY_API_KEY}",
                "Accept":        "application/vnd.api+json",
                "Content-Type":  "application/vnd.api+json",
            },
            json={
                "data": {
                    "type": "checkouts",
                    "attributes": {
                        "checkout_data": {
                            "email":       user.email,
                            "custom": {
                                "user_id": str(user.id),   # passed back in webhook
                            },
                        },
                        "product_options": {
                            "redirect_url": f"{settings.FRONTEND_URL}/dashboard?upgraded=true",
                        },
                    },
                    "relationships": {
                        "store": {
                            "data": {"type": "stores", "id": settings.LS_STORE_ID}
                        },
                        "variant": {
                            "data": {"type": "variants", "id": str(variant_id)}
                        },
                    },
                }
            },
        )
        resp.raise_for_status()

    checkout_url = resp.json()["data"]["attributes"]["url"]
    return {"checkout_url": checkout_url}
```

### Step 4: Webhook Handler

```python
# app/api/v1/billing.py (continued)

import hashlib
import hmac
from fastapi import Request

VARIANT_TO_PLAN: dict[str, str] = {
    str(settings.LS_PRO_MONTHLY_VARIANT_ID):   "pro",
    str(settings.LS_PRO_ANNUAL_VARIANT_ID):    "pro",
    str(settings.LS_POWER_MONTHLY_VARIANT_ID): "power",
    str(settings.LS_POWER_ANNUAL_VARIANT_ID):  "power",
}


@router.post("/webhook")
async def lemonsqueezy_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Handle LemonSqueezy subscription lifecycle webhooks.
    Verified via HMAC-SHA256 signature on the raw request body.
    """
    raw_body = await request.body()
    _verify_webhook_signature(request, raw_body)

    payload = await request.json()
    event_name: str = payload["meta"]["event_name"]
    data = payload["data"]
    attributes = data["attributes"]

    # Extract user_id from custom checkout data
    user_id: str | None = (
        payload.get("meta", {})
               .get("custom_data", {})
               .get("user_id")
    )

    handlers = {
        "subscription_created":        _handle_subscription_created,
        "subscription_updated":        _handle_subscription_updated,
        "subscription_cancelled":      _handle_subscription_cancelled,
        "subscription_expired":        _handle_subscription_expired,
        "subscription_payment_success": _handle_payment_success,
        "subscription_payment_failed":  _handle_payment_failed,
    }

    handler = handlers.get(event_name)
    if handler:
        await handler(user_id, data, attributes, db)

    return {"received": True}


def _verify_webhook_signature(request: Request, body: bytes) -> None:
    """Verify X-Signature header using HMAC-SHA256."""
    signature = request.headers.get("X-Signature", "")
    expected = hmac.new(
        settings.LEMONSQUEEZY_WEBHOOK_SECRET.encode(),
        body,
        hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(signature, expected):
        raise HTTPException(status_code=401, detail="Invalid webhook signature")


async def _handle_subscription_created(
    user_id: str, data: dict, attributes: dict, db: AsyncSession
) -> None:
    """Upgrade user plan when subscription is created."""
    variant_id = str(attributes["variant_id"])
    plan = VARIANT_TO_PLAN.get(variant_id, "pro")
    subscription_id = str(data["id"])
    customer_id = str(attributes["customer_id"])

    await db.execute(
        text("""
            UPDATE users SET
                plan                         = :plan,
                plan_updated_at              = NOW(),
                plan_expires_at              = NULL,
                lemon_squeezy_subscription_id = :sub_id,
                lemon_squeezy_customer_id    = :cust_id,
                lemon_squeezy_variant_id     = :variant_id
            WHERE id = :user_id
        """),
        {
            "plan": plan,
            "sub_id": subscription_id,
            "cust_id": customer_id,
            "variant_id": variant_id,
            "user_id": user_id,
        },
    )
    await db.commit()


async def _handle_subscription_cancelled(
    user_id: str, data: dict, attributes: dict, db: AsyncSession
) -> None:
    """
    When cancelled, set plan_expires_at to end of billing period.
    User retains Pro/Power access until expiry — don't downgrade immediately.
    """
    ends_at = attributes.get("ends_at")  # ISO8601 string from LemonSqueezy

    await db.execute(
        text("""
            UPDATE users SET
                plan_expires_at = :expires_at,
                plan_updated_at = NOW()
            WHERE id = :user_id
        """),
        {"expires_at": ends_at, "user_id": user_id},
    )
    await db.commit()
    # Schedule a job to downgrade to 'free' at plan_expires_at
    # This is handled by a nightly Inngest cron function


async def _handle_subscription_expired(
    user_id: str, data: dict, attributes: dict, db: AsyncSession
) -> None:
    """Hard downgrade to free when subscription fully expires."""
    await db.execute(
        text("""
            UPDATE users SET
                plan                          = 'free',
                plan_updated_at               = NOW(),
                plan_expires_at               = NULL,
                lemon_squeezy_subscription_id = NULL,
                lemon_squeezy_variant_id      = NULL
            WHERE id = :user_id
        """),
        {"user_id": user_id},
    )
    await db.commit()


async def _handle_subscription_updated(
    user_id: str, data: dict, attributes: dict, db: AsyncSession
) -> None:
    """Handle plan change (upgrade/downgrade between Pro and Power)."""
    variant_id = str(attributes["variant_id"])
    new_plan = VARIANT_TO_PLAN.get(variant_id, "pro")

    await db.execute(
        text("""
            UPDATE users SET
                plan                     = :plan,
                plan_updated_at          = NOW(),
                lemon_squeezy_variant_id = :variant_id
            WHERE id = :user_id
        """),
        {"plan": new_plan, "variant_id": variant_id, "user_id": user_id},
    )
    await db.commit()


async def _handle_payment_success(
    user_id: str, data: dict, attributes: dict, db: AsyncSession
) -> None:
    """Renewal payment succeeded — extend plan_expires_at if set."""
    # If plan was pending expiry (cancelled but paid), re-activate
    await db.execute(
        text("""
            UPDATE users SET plan_expires_at = NULL
            WHERE id = :user_id AND plan_expires_at IS NOT NULL
        """),
        {"user_id": user_id},
    )
    await db.commit()


async def _handle_payment_failed(
    user_id: str, data: dict, attributes: dict, db: AsyncSession
) -> None:
    """Payment failed — LemonSqueezy will retry. Log for monitoring."""
    # Don't downgrade immediately. LemonSqueezy retries over 3-7 days.
    # If subscription_expired fires after retries, we downgrade then.
    pass  # Add alerting/logging here
```

---

## 7. Upgrade Prompt UX Design

### When to Show Upgrade Prompts

| Trigger | Channel | Copy |
|---|---|---|
| Hard quota hit | API 402 response + frontend modal | "You've hit your Free plan limit" |
| 80% usage warning | `X-Quota-Warning` header → soft banner | "You're almost out of browser tasks (4/5)" |
| Feature gate (research, language) | Inline tooltip | "Research mode is available on Pro+" |
| 28th of month, >60% usage | Email (from LemonSqueezy or Postmark) | "Running low? Upgrade before month end" |
| Post-long-task | Toast notification | "Priority queue makes this 2x faster on Pro" |

### Error Response Schema

When a user hits quota, the API returns HTTP 402 with this body:

```json
{
  "error": "quota_exceeded",
  "message": "You've used all 5 browser tasks this month on the Free plan.",
  "current_plan": "free",
  "current_usage": 5,
  "limit": 5,
  "upgrade_url": "https://nexus.app/upgrade",
  "plan_comparison": {
    "pro": {
      "browser_tasks": 50,
      "price": "$15/mo"
    },
    "power": {
      "browser_tasks": 500,
      "price": "$39/mo"
    }
  }
}
```

### Frontend Handling

```typescript
// lib/api/tasks.ts

export async function createTask(payload: CreateTaskPayload) {
  const res = await fetch("/api/tasks/browser", {
    method: "POST",
    body: JSON.stringify(payload),
    headers: { "Content-Type": "application/json" },
  });

  // Handle soft quota warning
  const warning = res.headers.get("X-Quota-Warning");
  if (warning) {
    const [usage, limit] = parseQuotaWarning(warning);
    toast.warning(`${usage}/${limit} browser tasks used this month`, {
      action: { label: "Upgrade", onClick: () => router.push("/upgrade") },
    });
  }

  if (res.status === 402) {
    const error = await res.json();
    showUpgradeModal(error);  // Full-screen upgrade modal with plan comparison
    return null;
  }

  return res.json();
}
```

---

## 8. Priority Queue Logic

Pro and Power users get higher priority in the Inngest queue. This means their tasks are picked up sooner when the system is under load — critical for browser automation tasks that can take several minutes.

### Inngest Priority Assignment

```python
# app/services/task_dispatcher.py

import inngest

async def dispatch_task(
    task_type: str,
    task_id: str,
    user_id: str,
    user_plan: str,
    payload: dict,
) -> str:
    """Send task event to Inngest with plan-appropriate priority."""

    PRIORITY_MAP = {
        "free":  0,
        "pro":   5,
        "power": 10,
    }
    priority = PRIORITY_MAP.get(user_plan, 0)

    event_name_map = {
        "browser":  "nexus/task.browser.requested",
        "normal":   "nexus/task.windows.requested",
        "research": "nexus/task.research.requested",
    }

    await inngest_client.send(
        inngest.Event(
            name=event_name_map[task_type],
            data={
                "task_id":     task_id,
                "user_id":     user_id,
                "priority":    priority,
                **payload,
            },
        )
    )

    return task_id
```

### How Inngest Priority Works

Inngest uses an integer priority field (higher = picked up sooner). When multiple events are queued, the Inngest scheduler prioritizes higher-priority events. Configuration in the function definition:

```python
@inngest_client.create_function(
    fn_id="nexus/browser-task",
    trigger=inngest.TriggerEvent(event="nexus/task.browser.requested"),
    priority=inngest.Priority(
        run="event.data.priority",  # Read priority from event payload
    ),
    retries=2,
    timeout="10m",
)
async def handle_browser_task(ctx: inngest.Context, step: inngest.Step) -> dict:
    ...
```

**Effective result:** A Power user's browser task will jump the queue ahead of 10 pending Free tasks. This is the most tangible value prop for paying users during peak load.

---

## 9. Revenue Projections

### Cost Structure (Monthly, at Railway + Supabase free tiers)

| Item | Monthly Cost |
|---|---|
| Railway (backend) | $5 |
| Supabase (Postgres + Auth) | $0 (free tier) |
| Inngest (100k events/mo) | $0 (free tier) |
| Vercel (frontend) | $0 (hobby) |
| LemonSqueezy | 5% of revenue |
| Domain + misc | ~$2 |
| **Fixed infrastructure** | **~$7/mo** |

At $7/mo fixed costs, the break-even with LemonSqueezy's fee is:

- At $15/mo Pro: need **1 paying user** to cover infra (net $14.25 after fees)
- Ramen profitable (including personal time): ~**20 Pro users** ($285/mo net) or **8 Power users** ($296/mo net)

### Month 1–6 Targets

| Month | Free Users | Paying Users | Conversion | MRR |
|---|---|---|---|---|
| M1 | 50 | 2 | 4% | $30 |
| M2 | 150 | 8 | 5.3% | $120 |
| M3 | 400 | 25 | 6.25% | $375 |
| M4 | 800 | 60 | 7.5% | $900 |
| M5 | 1,500 | 120 | 8% | $1,800 |
| M6 | 2,500 | 225 | 9% | $3,375 |

*Assumes 50% Pro, 50% Power mix among paying users.*  
*Conversion rate 4–9% is realistic for a product with strong WOW moments and natural quota pressure.*

### Break-Even Analysis

```
Infrastructure cost: $7/mo
LemonSqueezy fee:    5% of MRR

At MRR = X:
Net revenue = X * 0.95 - 7

Break even: X * 0.95 = 7 → X = $7.37/mo → 1 Pro user covers it.

"Ramen profitable" target ($3,000/mo net take-home):
X * 0.95 - 7 = 3,000
X = $3,165/mo → ~211 Pro users OR ~82 Power users OR any blended mix.
```

The model scales well: infrastructure costs increase only when moving off free tiers (Supabase free tier handles up to 500MB DB and 50k MAU; Inngest free tier handles 100k events/month). Both are sufficient up to ~$5k MRR before needing to upgrade.

### Upgrade Tier Triggers (Infrastructure)

| MRR Milestone | Action Required | New Monthly Cost |
|---|---|---|
| ~$1k MRR | Supabase Pro ($25) for > 500MB storage | +$25 |
| ~$3k MRR | Inngest paid tier if > 100k events/mo | ~+$20 |
| ~$10k MRR | Railway autoscaling (2+ instances) | ~+$25–50 |
| ~$25k MRR | Dedicated Postgres (>25GB), CDN | +$100–200 |

---

*Document end. Last section: see `async_task_queue.md` for the Inngest queue implementation details.*
