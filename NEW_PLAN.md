# Nadir — Supabase Setup & Architecture Guide

> Complete reference for setting up Supabase, the data schema, storage buckets, authentication, and monetization for the Nadir voice mood diary app.
> Intended for use with coding agents — each section is a discrete, executable step.

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Tech Stack](#2-tech-stack)
3. [Supabase Project Setup](#3-supabase-project-setup)
4. [Environment Variables](#4-environment-variables)
5. [Database Schema](#5-database-schema)
6. [Storage Buckets](#6-storage-buckets)
7. [Row Level Security](#7-row-level-security)
8. [Python Dependencies](#8-python-dependencies)
9. [Python db.py — Supabase Client](#9-python-dbpy--supabase-client)
10. [Authentication Flow](#10-authentication-flow)
11. [Subscription Tiers](#11-subscription-tiers)
12. [Monetization — Stripe + RevenueCat](#12-monetization--stripe--revenuecat)
13. [AI Call Enforcement Pattern](#13-ai-call-enforcement-pattern)
14. [FastAPI Endpoints Reference](#14-fastapi-endpoints-reference)
15. [Full System Architecture](#15-full-system-architecture)
16. [Build Order](#16-build-order)

---

## 1. Project Overview

Nadir is a voice-first personal mood diary app. Users speak freely, their voice is transcribed by Whisper, AI extracts emotional metadata, and entries are stored in a vector database for RAG-powered pattern queries.

**Core user flows:**

- Record a voice entry → transcribe → auto-tag mood/triggers → save
- Ask questions about emotional patterns → RAG retrieves relevant entries → AI answers
- Weekly reflection digest generated from last 7 entries

**Privacy:** All audio and diary data is private per-user. No entry is ever visible to other users.

---

## 2. Tech Stack

| Layer               | Tool                  | Notes                               |
| ------------------- | --------------------- | ----------------------------------- |
| Mobile frontend     | React Native + Expo   | iOS + Android from one codebase     |
| Backend API         | FastAPI (Python)      | Hosted on Railway or Render         |
| Database            | Supabase PostgreSQL   | + pgvector extension for embeddings |
| File storage        | Supabase Storage      | Private buckets, signed URLs        |
| Authentication      | Supabase Auth         | Email, Google, Apple sign-in        |
| Voice transcription | OpenAI Whisper        | Runs on server, not phone           |
| Embeddings          | sentence-transformers | `all-MiniLM-L6-v2`, runs locally    |
| LLM (local dev)     | Ollama `llama3.2:1b`  | Free, runs on your machine          |
| LLM (production)    | OpenAI `gpt-4o-mini`  | Swap when ready to deploy           |
| Billing             | Stripe + RevenueCat   | RevenueCat handles iOS/Android IAP  |

---

## 3. Supabase Project Setup

### Step 1 — Create project

1. Go to `supabase.com` and sign in
2. Click **New Project**
3. Choose a name (e.g. `nadir-prod`) and a strong database password
4. Select the region closest to your users
5. Wait ~2 minutes for provisioning

### Step 2 — Collect credentials

Go to **Settings → API** and copy:

```text
Project URL:   https://xxxxxxxxxxxx.supabase.co
Anon key:      eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
Service key:   eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...  ← keep secret, server only
```

Go to **Settings → Database** and copy:

```text
Connection string (URI):
postgresql://postgres:[PASSWORD]@db.xxxxxxxxxxxx.supabase.co:5432/postgres
```

---

## 4. Environment Variables

Add all of these to your `.env` file. Never commit this file to Git.

```env
# Supabase
SUPABASE_URL=https://xxxxxxxxxxxx.supabase.co
SUPABASE_ANON_KEY=eyJ...
SUPABASE_SERVICE_KEY=eyJ...        # server-side only, never expose to client
DATABASE_URL=postgresql://postgres:[PASSWORD]@db.xxxxxxxxxxxx.supabase.co:5432/postgres

# OpenAI (for production LLM calls)
OPENAI_API_KEY=sk-...

# Stripe
STRIPE_SECRET_KEY=sk_live_...
STRIPE_WEBHOOK_SECRET=whsec_...

# RevenueCat (optional, for mobile billing)
REVENUECAT_API_KEY=...
```

Your `.gitignore` should already contain `.env` — confirm before pushing to GitHub.

---

## 5. Database Schema

Run all of the following SQL in **Supabase → SQL Editor** in the order shown.

PR 1 includes the core schema only: Steps 1 and 3-7. Steps 2, 8-10 are planned for later PRs.

### Step 1 — Enable extensions

```sql
create schema if not exists extensions;

-- Vector similarity search
create extension if not exists vector with schema extensions;

-- UUID generation and crypto helpers
-- `gen_random_uuid()` is available on modern Postgres, but pgcrypto keeps the
-- setup compatible and provides other crypto helpers we may use later.
create extension if not exists pgcrypto with schema extensions;
```

### Step 2 — profiles table (planned trigger in a later PR)

`profiles` is the user identity table. In the current core schema PR, rows are not auto-created yet; the signup trigger will be added in a later PR.

```sql
create table public.profiles (
    id                  uuid primary key references auth.users(id) on delete cascade,
    created_at          timestamptz default now(),
    display_name        text,
    avatar_url          text
);
```

The auto-create trigger for new users will be added in a later PR.

### Step 3 — entries table

```sql
create table public.entries (
    id              uuid primary key default gen_random_uuid(),
    user_id         uuid not null references public.profiles(id) on delete cascade,
    created_at      timestamptz default now(),
    transcript      text not null,
    audio_path      text,                     -- pointer to Supabase Storage object path
    duration_secs   int,                      -- length of the voice recording
    processing_status text not null default 'recorded'
        check (processing_status in ('recorded', 'transcribing', 'transcribed', 'analyzing', 'pending_review', 'confirmed', 'error')),
    embedding       vector(384),              -- all-MiniLM-L6-v2 dimensions
    summary         text                      -- optional AI-generated summary
);

-- Index for fast vector similarity search
create index on public.entries
    using hnsw (embedding vector_cosine_ops);

-- Index for fast user entry lookups
create index on public.entries (user_id, created_at desc);

-- Index for queue-style lookups
create index on public.entries (user_id, processing_status, created_at desc);
```

### Step 4 — entry_analysis table

```sql
create table public.entry_analysis (
    entry_id         uuid primary key references public.entries(id) on delete cascade,
    created_at       timestamptz default now(),
    updated_at       timestamptz default now(),
    valence          double precision check (valence between -1.0 and 1.0),
    arousal          double precision check (arousal between 0.0 and 1.0),
    intensity        double precision check (intensity between 0.0 and 1.0),
    confidence       double precision check (confidence between 0.0 and 1.0),
    dominant_mood    text,
    analysis_status  text not null default 'proposed'
        check (analysis_status in ('proposed', 'pending_review', 'confirmed', 'corrected')),
    model_version    text
);

create index on public.entry_analysis (analysis_status);
create index on public.entry_analysis (created_at desc);
```

### Step 5 — entry_mood_signals table

```sql
create table public.entry_mood_signals (
    id            uuid primary key default gen_random_uuid(),
    entry_id      uuid not null references public.entries(id) on delete cascade,
    mood          text not null,
    intensity     double precision not null check (intensity between 0.0 and 1.0),
    confidence    double precision check (confidence between 0.0 and 1.0),
    valence_weight double precision,
    created_at    timestamptz default now(),
    unique (entry_id, mood)
);

create index on public.entry_mood_signals (entry_id);
create index on public.entry_mood_signals (mood, entry_id);
```

### Step 6 — entry_tags table

```sql
create table public.entry_tags (
    id            uuid primary key default gen_random_uuid(),
    entry_id      uuid not null references public.entries(id) on delete cascade,
    tag           text not null,
    confidence    double precision check (confidence between 0.0 and 1.0),
    created_at    timestamptz default now(),
    unique (entry_id, tag)
);

create index on public.entry_tags (entry_id);
create index on public.entry_tags (tag, entry_id);
```

### Step 7 — entry_feedback table

```sql
create table public.entry_feedback (
    id           uuid primary key default gen_random_uuid(),
    entry_id     uuid not null references public.entries(id) on delete cascade,
    user_id      uuid not null references public.profiles(id) on delete cascade,
    created_at   timestamptz default now(),
    field_name   text not null,
    old_value    jsonb,
    new_value    jsonb,
    reason       text,
    check (field_name in ('processing_status', 'analysis_status', 'valence', 'arousal', 'intensity', 'dominant_mood', 'mood_signals', 'tags', 'summary'))
);

create index on public.entry_feedback (user_id, created_at desc);
create index on public.entry_feedback (entry_id);
```

### Step 8 — ai_usage_log table (planned in a later PR)

```sql
create table public.ai_usage_log (
    id          uuid primary key default gen_random_uuid(),
    user_id     uuid not null references public.profiles(id) on delete cascade,
    created_at  timestamptz default now(),
    call_type   text not null
        check (call_type in ('ask', 'extract', 'summarise')),
    tokens_used int,
    model       text              -- 'llama3.2:1b' | 'gpt-4o-mini'
);

create index on public.ai_usage_log (user_id, created_at desc);
```

### Step 9 — subscriptions table (planned in a later PR)

```sql
create table public.subscriptions (
    user_id               uuid primary key references public.profiles(id) on delete cascade,
    created_at            timestamptz default now(),
    stripe_customer_id    text unique,
    stripe_sub_id         text unique,
    tier                  text not null default 'free',     -- 'free' | 'pro' | 'unlimited'
    status                text not null default 'active'
        check (status in ('active', 'cancelled', 'past_due')),
    current_period_end    date
);

create index on public.subscriptions (stripe_customer_id);
```

### Step 10 — match_entries function (planned in a later PR)

```sql
create or replace function match_entries (
    query_embedding  vector(384),
    match_user_id    uuid,
    match_count      int default 5
)
returns table (
    id           uuid,
    transcript   text,
    summary      text,
    created_at   timestamptz,
    valence      double precision,
    arousal      double precision,
    intensity    double precision,
    dominant_mood text,
    similarity   float
)
language sql stable
as $$
    select
        e.id,
        e.transcript,
        e.summary,
        e.created_at,
        a.valence,
        a.arousal,
        a.intensity,
        a.dominant_mood,
        1 - (e.embedding <=> query_embedding) as similarity
    from public.entries e
    left join public.entry_analysis a on a.entry_id = e.id
    where e.user_id = match_user_id
      and e.embedding is not null
    order by e.embedding <=> query_embedding
    limit match_count;
$$;
```

### Step 11 — usage accounting

```sql
-- Usage is tracked in ai_usage_log, so no profile counter reset is needed.
-- If limits are enforced in SQL later, add a dedicated usage summary table.
```

---

## 6. Storage Buckets

Run in **Supabase → SQL Editor** or create manually in **Storage** dashboard.

```sql
-- Recordings bucket (private)
insert into storage.buckets (id, name, public)
values ('recordings', 'recordings', false);

-- Avatars bucket (private)
insert into storage.buckets (id, name, public)
values ('avatars', 'avatars', false);
```

### File path conventions

```text
recordings/
└── {user_id}/
    └── {YYYYMMDD_HHMMSS}.m4a
    e.g. recordings/abc-123/20260316_143022.m4a

avatars/
└── {user_id}/
    └── avatar.jpg
    e.g. avatars/abc-123/avatar.jpg
```

### Accessing files from Python (signed URL — expires in 1 hour)

```python
response = supabase.storage.from_("recordings").create_signed_url(
    path=f"{user_id}/{filename}",
    expires_in=3600
)
url = response["signedURL"]
```

---

## 7. Row Level Security

RLS ensures every user can only see and modify their own data. Run in **SQL Editor**.

```sql
-- ── profiles ──
alter table public.profiles enable row level security;

create policy "Users can view own profile"
    on public.profiles for select
    using ((select auth.uid()) = id);

create policy "Users can update own profile"
    on public.profiles for update
    using ((select auth.uid()) = id);

-- ── entries ──
alter table public.entries enable row level security;

create policy "Users can view own entries"
    on public.entries for select
    using ((select auth.uid()) = user_id);

create policy "Users can insert own entries"
    on public.entries for insert
    with check ((select auth.uid()) = user_id);

create policy "Users can delete own entries"
    on public.entries for delete
    using ((select auth.uid()) = user_id);

-- ── entry_analysis ──
alter table public.entry_analysis enable row level security;

create policy "Users can view own analysis"
    on public.entry_analysis for select
    using (
        exists (
            select 1
            from public.entries e
            where e.id = entry_id
              and e.user_id = (select auth.uid())
        )
    );

-- ── entry_mood_signals ──
alter table public.entry_mood_signals enable row level security;

create policy "Users can view own mood signals"
    on public.entry_mood_signals for select
    using (
        exists (
            select 1
            from public.entries e
            where e.id = entry_id
              and e.user_id = (select auth.uid())
        )
    );

-- ── entry_tags ──
alter table public.entry_tags enable row level security;

create policy "Users can view own tags"
    on public.entry_tags for select
    using (
        exists (
            select 1
            from public.entries e
            where e.id = entry_id
              and e.user_id = (select auth.uid())
        )
    );

-- ── entry_feedback ──
alter table public.entry_feedback enable row level security;

create policy "Users can view own feedback"
    on public.entry_feedback for select
    using ((select auth.uid()) = user_id);

create policy "Users can insert own feedback"
    on public.entry_feedback for insert
    with check (
        (select auth.uid()) = user_id
        and exists (
            select 1
            from public.entries e
            where e.id = entry_id
              and e.user_id = (select auth.uid())
        )
    );

create policy "Users can update own feedback"
    on public.entry_feedback for update
    using (
        (select auth.uid()) = user_id
        and exists (
            select 1
            from public.entries e
            where e.id = entry_id
              and e.user_id = (select auth.uid())
        )
    );

create policy "Users can delete own feedback"
    on public.entry_feedback for delete
    using (
        (select auth.uid()) = user_id
        and exists (
            select 1
            from public.entries e
            where e.id = entry_id
              and e.user_id = (select auth.uid())
        )
    );

-- ── ai_usage_log ──
alter table public.ai_usage_log enable row level security;

create policy "Users can view own usage"
    on public.ai_usage_log for select
    using ((select auth.uid()) = user_id);

-- ── subscriptions ──
alter table public.subscriptions enable row level security;

create policy "Users can view own subscription"
    on public.subscriptions for select
    using ((select auth.uid()) = user_id);

-- ── Storage: recordings ──
create policy "Users can upload own recordings"
    on storage.objects for insert
    with check (
        bucket_id = 'recordings'
        and (select auth.uid())::text = (storage.foldername(name))[1]
    );

create policy "Users can view own recordings"
    on storage.objects for select
    using (
        bucket_id = 'recordings'
        and (select auth.uid())::text = (storage.foldername(name))[1]
    );

create policy "Users can delete own recordings"
    on storage.objects for delete
    using (
        bucket_id = 'recordings'
        and (select auth.uid())::text = (storage.foldername(name))[1]
    );

-- ── Storage: avatars ──
create policy "Users can manage own avatar"
    on storage.objects for all
    using (
        bucket_id = 'avatars'
        and (select auth.uid())::text = (storage.foldername(name))[1]
    );
```

---

## 8. Python Dependencies

```bash
# Remove ChromaDB, add Supabase stack
uv remove chromadb

uv add supabase
uv add sentence-transformers
uv add vecs
uv add stripe
uv add python-jose   # JWT token verification
uv add fastapi uvicorn
```

Full `pyproject.toml` dependencies section:

```toml
dependencies = [
    "fastapi>=0.115.0",
    "uvicorn>=0.30.0",
    "supabase>=2.0.0",
    "sentence-transformers>=3.0.0",
    "vecs>=0.4.0",
    "openai>=2.0.0",
    "openai-whisper>=20250625",
    "sounddevice>=0.5.0",
    "scipy>=1.17.0",
    "pydantic>=2.0.0",
    "python-dotenv>=1.0.0",
    "python-jose>=3.3.0",
    "stripe>=10.0.0",
    "python-multipart>=0.0.9",
]
```

---

## 9. Python db.py — Supabase Client

Replace your existing `db.py` entirely with this:

```python
"""
db.py — Supabase client and embedding model
Imported by store.py, query.py, and main.py
"""

import os
from dotenv import load_dotenv
from supabase import create_client, Client
from sentence_transformers import SentenceTransformer

load_dotenv()

# ── Supabase client ───────────────────────────────────────────────────────────

def get_supabase() -> Client:
    """Returns authenticated Supabase client using the service key."""
    url = os.environ["SUPABASE_URL"]
    key = os.environ["SUPABASE_SERVICE_KEY"]   # service key for server-side ops
    return create_client(url, key)

def get_storage():
    """Shortcut to the recordings storage bucket."""
    return get_supabase().storage.from_("recordings")

# ── Embedding model ───────────────────────────────────────────────────────────
# Downloads ~80MB on first run, cached locally after that

_model = None

def get_embedding_model() -> SentenceTransformer:
    global _model
    if _model is None:
        _model = SentenceTransformer("all-MiniLM-L6-v2")
    return _model

def embed(text: str) -> list[float]:
    """Convert a string to a 384-dimensional embedding vector."""
    model = get_embedding_model()
    return model.encode(text).tolist()
```

---

## 10. Authentication Flow

Supabase Auth handles everything. Your FastAPI server verifies the JWT token on every request.

### How it works

```text
1. User signs in on mobile app via Supabase Auth SDK
2. Supabase returns a JWT access token
3. Mobile app sends JWT in every API request header:
   Authorization: Bearer eyJ...
4. FastAPI verifies the JWT using Supabase's public key
5. FastAPI extracts user_id from the token
6. All database queries are scoped to that user_id
```

### FastAPI JWT verification

```python
from fastapi import Depends, HTTPException, Header
from jose import jwt, JWTError
import os

SUPABASE_JWT_SECRET = os.environ["SUPABASE_JWT_SECRET"]  # from Supabase dashboard

def get_current_user(authorization: str = Header(...)) -> str:
    """Extract and verify user_id from JWT. Use as a FastAPI dependency."""
    try:
        token = authorization.replace("Bearer ", "")
        payload = jwt.decode(token, SUPABASE_JWT_SECRET, algorithms=["HS256"])
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(401, "Invalid token")
        return user_id
    except JWTError:
        raise HTTPException(401, "Could not validate token")

# Usage in any endpoint:
@app.post("/entries/save")
def save_entry(data: EntryRequest, user_id: str = Depends(get_current_user)):
    # user_id is verified and safe to use
    ...
```

---

## 11. Subscription Tiers

| Tier      | Price    | AI asks/month | AI extractions | Weekly digest | Storage |
| --------- | -------- | ------------- | -------------- | ------------- | ------- |
| Free      | $0       | 30            | 30             | No            | 100 MB  |
| Pro       | $4.99/mo | 500           | Unlimited      | No            | 2 GB    |
| Unlimited | $9.99/mo | Unlimited     | Unlimited      | Yes           | 10 GB   |

### Tier limits by subscription tier

These limits live in application logic or a dedicated billing table, not `profiles`.

| Tier      | Monthly ask limit | Extraction limit | Weekly digest |
| --------- | ----------------- | ----------------- | ------------- |
| free      | 30                | 30                | No            |
| pro       | 500               | Unlimited         | No            |
| unlimited | Unlimited         | Unlimited         | Yes           |

### What counts as an AI call

| Action                        | Call type   | Counts against limit? |
| ----------------------------- | ----------- | --------------------- |
| User asks a question          | `ask`       | Yes                   |
| Auto-extract metadata on save | `extract`   | Yes (free), No (pro+) |
| Weekly reflection summary     | `summarise` | Unlimited only        |
| Transcription (Whisper)       | n/a         | No — flat server cost |

---

## 12. Monetization — Stripe + RevenueCat

### Why RevenueCat

Apple App Store and Google Play both require in-app purchases for subscriptions sold inside a mobile app. RevenueCat abstracts both platforms plus web (Stripe) into one API. Without it you'd manage three separate billing integrations.

### Setup steps

1. Create a RevenueCat account at `revenuecat.com`
2. Create products in App Store Connect and Google Play Console
3. Link those products to RevenueCat entitlements
4. RevenueCat sends webhooks to your FastAPI server on subscription events

### FastAPI webhook handler

```python
@app.post("/webhooks/revenuecat")
async def revenuecat_webhook(request: Request):
    payload = await request.json()
    event_type = payload["event"]["type"]
    user_id    = payload["event"]["app_user_id"]
    product_id = payload["event"].get("product_id", "")

    # Map product ID to tier
    tier_map = {
        "nadir_pro_monthly":       "pro",
        "nadir_unlimited_monthly": "unlimited",
    }
    tier = tier_map.get(product_id, "free")

    if event_type in ("INITIAL_PURCHASE", "RENEWAL"):
        supabase.table("subscriptions").upsert({
            "user_id": user_id,
            "tier": tier,
            "status": "active",
        }).execute()

    elif event_type in ("CANCELLATION", "EXPIRATION"):
        supabase.table("subscriptions").update({
            "status": "cancelled",
            "tier": "free",
        }).eq("user_id", user_id).execute()

    return {"status": "ok"}
```

---

## 13. AI Call Enforcement Pattern

Add this check to every FastAPI endpoint that calls an LLM.

```python
def check_ai_limit(user_id: str, call_type: str):
    """
    Raises HTTP 429 if user has exceeded their monthly AI limit for this call type.
    Logs the call if allowed.
    """
    supabase = get_supabase()

    # Fetch current subscription tier
    result = supabase.table("subscriptions")\
        .select("tier, status")\
        .eq("user_id", user_id)\
        .limit(1)\
        .execute()

    subscription = result.data[0] if result.data else None
    tier = subscription["tier"] if subscription and subscription["status"] == "active" else "free"

    # Call-type limits are enforced in application logic.
    # The database only stores the event log.
    limit_map = {
        "free": {"ask": 30, "extract": 30, "summarise": 0},
        "pro": {"ask": 500, "extract": 999999, "summarise": 0},
        "unlimited": {"ask": 999999, "extract": 999999, "summarise": 999999},
    }
    limit = limit_map.get(tier, limit_map["free"]).get(call_type, 0)

    if limit == 0:
        raise HTTPException(
            status_code=429,
            detail={
                "error": "This AI action is not available on your tier",
                "tier": tier,
                "call_type": call_type,
                "upgrade_url": "https://yourapp.com/upgrade"
            }
        )

    # Count usage for the current month and call type from the log table.
    # This keeps the profiles table identity-only.
    month_start = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    usage = supabase.table("ai_usage_log")\
        .select("id", count="exact")\
        .eq("user_id", user_id)\
        .eq("call_type", call_type)\
        .gte("created_at", month_start.isoformat())\
        .execute()

    used = usage.count or 0

    if used >= limit:
        raise HTTPException(
            status_code=429,
            detail={
                "error": f"Monthly AI limit reached for {call_type}",
                "used": used,
                "limit": limit,
                "tier": tier,
                "upgrade_url": "https://yourapp.com/upgrade"
            }
        )

    # Log the call
    supabase.table("ai_usage_log").insert({
        "user_id":  user_id,
        "call_type": call_type,
        "model":    "gpt-4o-mini",
    }).execute()
```

### Usage in endpoints

```python
@app.post("/ask")
def ask_question(data: AskRequest, user_id: str = Depends(get_current_user)):
    check_ai_limit(user_id, "ask")   # ← call this before any LLM call
    # ... rest of RAG logic
```

---

## 14. FastAPI Endpoints Reference

| Method   | Path                    | Auth     | Description                                  |
| -------- | ----------------------- | -------- | -------------------------------------------- |
| `POST`   | `/entries/upload-audio` | Required | Upload .m4a → transcribe → return transcript |
| `POST`   | `/entries/save`         | Required | Save transcript + analysis + signals + embedding |
| `GET`    | `/entries`              | Required | List user's recent entries                   |
| `GET`    | `/entries/{id}`         | Required | Get single entry                             |
| `DELETE` | `/entries/{id}`         | Required | Delete entry + audio file                    |
| `POST`   | `/ask`                  | Required | RAG question → AI answer                     |
| `GET`    | `/profile`              | Required | Get user profile + subscription info         |
| `POST`   | `/webhooks/revenuecat`  | None     | Handle billing events                        |
| `GET`    | `/health`               | None     | Server health check                          |

### POST /entries/upload-audio

```python
@app.post("/entries/upload-audio")
async def upload_audio(
    audio: UploadFile,
    user_id: str = Depends(get_current_user)
):
    audio_bytes = await audio.read()
    filename    = f"{user_id}/{datetime.now().strftime('%Y%m%d_%H%M%S')}.m4a"
    audio_path  = filename

    # Upload to Supabase Storage
    get_storage().upload(
        path=filename,
        file=audio_bytes,
        file_options={"content-type": "audio/m4a"}
    )

    # Transcribe with Whisper (temp file on disk)
    with tempfile.NamedTemporaryFile(suffix=".m4a", delete=False) as tmp:
        tmp.write(audio_bytes)
        tmp_path = tmp.name

    transcript = transcribe(tmp_path)   # your transcribe.py function
    os.unlink(tmp_path)

    return {"transcript": transcript, "audio_path": audio_path}
```

---

## 15. Full System Architecture

```text
┌─────────────────┐         ┌──────────────────────┐        ┌─────────────────────────┐
│   Phone app     │         │   FastAPI server      │        │   Supabase              │
│ React Native    │         │   main.py             │        │                         │
│                 │         │                       │        │  PostgreSQL             │
│  Microphone ────┼─────────┼→ POST /upload-audio   │        │  ┌──────────────────┐  │
│  Temp .m4a      │         │    transcribe.py      │        │  │ profiles         │  │
│  Chat UI   ←────┼─────────┼─  Whisper → text  ───┼────────┼→ │ entries          │  │
│                 │         │    store.py           │        │  │ entry_analysis   │  │
│                 │─────────┼→ POST /ask            │        │  │ entry_mood_signals│ │
│                 │         │    query.py           │        │  │ entry_tags       │  │
│                 │         │    embed → pgvector   │        │  │ entry_feedback   │  │
│                 │         │    Ollama / OpenAI    │        │  │ ai_usage_log     │  │
│                 │         │ POST /webhooks/       │        │  │ subscriptions    │  │
│  RevenueCat ────┼─────────┼→  revenuecat          │        │  └──────────────────┘  │
│                 │         │    update tier        │        │                         │
│                 │         │                       │        │  Storage                │
│                 │         │                       │        │  ┌──────────────────┐  │
│                 │         │                       │        │  │ recordings/      │  │
│                 │         │                       │        │  │ avatars/         │  │
│                 │         │                       │        │  └──────────────────┘  │
└─────────────────┘         └──────────────────────┘        └─────────────────────────┘
```

---

## 16. Build Order

Work through these phases in order. Each phase has a clear done-when checkpoint.

### Phase 1 — Supabase foundation

- [ ] Create Supabase project
- [ ] Run all SQL from Section 5 in SQL Editor
- [ ] Create storage buckets (Section 6)
- [ ] Apply RLS policies (Section 7)
- [ ] Add credentials to `.env`
- [ ] Install Python dependencies (Section 8)
- [ ] Write and test `db.py` (Section 9)

**Done when:** `python db.py` runs without errors and connects to Supabase

### Phase 2 — Rewrite store.py and query.py for Supabase

- [ ] Rewrite `store.py` to insert into `entries` table with embeddings
- [ ] Rewrite `query.py` to use `match_entries` RPC function
- [ ] Test: save an entry, run a vector search, get results back

**Done when:** You can save an entry and ask a question with results from Supabase

### Phase 3 — Voice recording

- [ ] Write `record.py` — mic capture → `.m4a` file
- [ ] Write `transcribe.py` — Whisper → text
- [ ] Test both independently from terminal

**Done when:** `python record.py` saves a file, `python transcribe.py recording.m4a` returns text

### Phase 4 — FastAPI server

- [ ] Write `main.py` with all endpoints from Section 14
- [ ] Add JWT auth middleware (Section 10)
- [ ] Add AI call enforcement (Section 13)
- [ ] Test all endpoints with Bruno or Postman

**Done when:** All endpoints return correct responses when called with a valid JWT

### Phase 5 — Mobile frontend

- [ ] Set up React Native + Expo project
- [ ] Integrate Supabase Auth SDK for sign-in
- [ ] Build record screen — calls `POST /entries/upload-audio`
- [ ] Build reflect screen — calls `POST /ask`
- [ ] Build entry list screen — calls `GET /entries`

**Done when:** Full flow works on a real device — record, save, ask, get answer

### Phase 6 — Billing

- [ ] Set up RevenueCat account and products
- [ ] Add webhook endpoint (Section 12)
- [ ] Test subscription flow end to end
- [ ] Verify tier enforcement works correctly

**Done when:** Subscribing to Pro updates the row in `subscriptions` and leaves `profiles` untouched

---

_Last updated: March 2026 — Nadir v0.1_
