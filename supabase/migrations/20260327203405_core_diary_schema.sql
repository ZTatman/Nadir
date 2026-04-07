create schema if not exists extensions;

create extension if not exists vector with schema extensions;
create extension if not exists pgcrypto with schema extensions;

-- ------------------------------------------------------------
-- profiles
-- ------------------------------------------------------------
create table public.profiles (
    id uuid primary key references auth.users(id) on delete cascade,
    created_at timestamptz not null default now(),
    display_name text,
    avatar_url text
);

-- ------------------------------------------------------------
-- entries
-- ------------------------------------------------------------
create table public.entries (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references public.profiles(id) on delete cascade,
    created_at timestamptz not null default now(),
    transcript text not null,
    audio_path text,
    duration_secs int,
    processing_status text not null default 'recorded'
        check (
            processing_status in (
                'recorded',
                'transcribing',
                'transcribed',
                'analyzing',
                'pending_review',
                'confirmed',
                'error'
            )
        ),
    embedding vector(384),
    summary text
);

create index entries_user_created_at_idx
    on public.entries (user_id, created_at desc);

create index entries_user_status_created_at_idx
    on public.entries (user_id, processing_status, created_at desc);

create index entries_embedding_idx
    on public.entries
    using hnsw (embedding vector_cosine_ops);

-- ------------------------------------------------------------
-- entry_analysis
-- ------------------------------------------------------------
create table public.entry_analysis (
    entry_id uuid primary key references public.entries(id) on delete cascade,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    valence double precision check (valence between -1.0 and 1.0),
    arousal double precision check (arousal between 0.0 and 1.0),
    intensity double precision check (intensity between 0.0 and 1.0),
    confidence double precision check (confidence between 0.0 and 1.0),
    dominant_mood text,
    analysis_status text not null default 'proposed'
        check (analysis_status in ('proposed', 'pending_review', 'confirmed', 'corrected')),
    model_version text
);

create index entry_analysis_status_idx
    on public.entry_analysis (analysis_status);

create index entry_analysis_created_at_idx
    on public.entry_analysis (created_at desc);

-- ------------------------------------------------------------
-- entry_mood_signals
-- ------------------------------------------------------------
create table public.entry_mood_signals (
    id uuid primary key default gen_random_uuid(),
    entry_id uuid not null references public.entries(id) on delete cascade,
    mood text not null,
    intensity double precision not null check (intensity between 0.0 and 1.0),
    confidence double precision check (confidence between 0.0 and 1.0),
    valence_weight double precision,
    created_at timestamptz not null default now(),
    unique (entry_id, mood)
);

create index entry_mood_signals_entry_id_idx
    on public.entry_mood_signals (entry_id);

create index entry_mood_signals_mood_entry_id_idx
    on public.entry_mood_signals (mood, entry_id);

-- ------------------------------------------------------------
-- entry_tags
-- ------------------------------------------------------------
create table public.entry_tags (
    id uuid primary key default gen_random_uuid(),
    entry_id uuid not null references public.entries(id) on delete cascade,
    tag text not null,
    confidence double precision check (confidence between 0.0 and 1.0),
    created_at timestamptz not null default now(),
    unique (entry_id, tag)
);

create index entry_tags_entry_id_idx
    on public.entry_tags (entry_id);

create index entry_tags_tag_entry_id_idx
    on public.entry_tags (tag, entry_id);

-- ------------------------------------------------------------
-- entry_feedback
-- ------------------------------------------------------------
create table public.entry_feedback (
    id uuid primary key default gen_random_uuid(),
    entry_id uuid not null references public.entries(id) on delete cascade,
    user_id uuid not null references public.profiles(id) on delete cascade,
    created_at timestamptz not null default now(),
    field_name text not null,
    old_value jsonb,
    new_value jsonb,
    reason text,
    check (
        field_name in (
            'processing_status',
            'analysis_status',
            'valence',
            'arousal',
            'intensity',
            'dominant_mood',
            'mood_signals',
            'tags',
            'summary'
        )
    )
);

create index entry_feedback_user_created_at_idx
    on public.entry_feedback (user_id, created_at desc);

create index entry_feedback_entry_id_idx
    on public.entry_feedback (entry_id);
