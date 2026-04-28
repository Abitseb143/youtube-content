# Faceless YouTube Automation SaaS — Design Spec

**Date:** 2026-04-28
**Status:** Draft (awaiting user review)
**Author:** Brainstorming session output

---

## 1. Overview & Boundaries

### Product

A multi-tenant SaaS platform where users connect a YouTube channel, configure a recurring content cadence (e.g., 3 videos/week on a niche), and receive AI-generated faceless videos in an approval queue. Approved videos publish to YouTube. The system pulls post-publish analytics and uses them to bias future script generation per channel.

Long-form videos are the primary output; shorts are a secondary supported format.

### Locked decisions

| # | Topic | Choice |
|---|---|---|
| 1 | Product | Faceless YouTube channel automation (long-form primary, shorts secondary) |
| 2 | Audience | Public multi-tenant SaaS — users connect their own YouTube channels |
| 3 | Monetization | Pay-as-you-go credits (no subscription) |
| 4 | Credit granularity | Flat per-video pricing |
| 5 | Visuals | OpenAI `gpt-image-1` per scene → Kling 3.0 image-to-video → FFmpeg stitch |
| 6 | Voice | ElevenLabs |
| 7 | Publishing | Scheduled auto-generation → approval queue → YouTube upload |
| 8 | Intelligence | Engagement-driven optimization in MVP (per-channel few-shot conditioning from YouTube Analytics) |
| 9 | Deployment | Single-cloud monolith-ish on Railway; Postgres + Redis + Cloudflare R2 |
| 10 | Backend | Python (FastAPI + arq for job queue) |
| 11 | Frontend | Next.js (App Router) |
| 12 | Music | Royalty-free library only |
| 13 | Captions | Burned-in for MVP |
| 14 | Thumbnails | Auto-generate via `gpt-image-1` and allow user override |
| 15 | Repo | Monorepo (pnpm workspaces) |
| 16 | Storage | Cloudflare R2 (zero-egress, S3-compatible) |
| 17 | Maturity threshold for top performers | 7 days |

### External boundaries

| Boundary | Provider | Purpose | Failure mode |
|---|---|---|---|
| Auth | Clerk | User signup, sessions | Down → users can't log in |
| Payments | Stripe (one-time payments) | Buy credits, webhook fulfillment | Webhook delays → eventual consistency |
| Script LLM | OpenAI GPT-4-class | Script + scene plan + metadata + thumbnail prompt | Rate limit/outage → retry + backoff |
| Images | OpenAI `gpt-image-1` | One still per scene + thumbnail | Content-policy refusal → reprompt → fail scene |
| Video clips | Kling 3.0 (image-to-video, async) | Animate stills | Long queues; per-account concurrency limits |
| TTS | ElevenLabs | Voiceover with word-level alignment | Rate limit → backoff; alignment failure → Whisper fallback |
| Forced alignment | OpenAI Whisper | Caption timing fallback | Both down → ship without burned captions |
| Music | R2 royalty-free library indexed in Postgres | Background bed | Always available |
| Storage | Cloudflare R2 | All assets | Standard durability assumptions |
| Publishing | YouTube Data API v3 (OAuth per channel) | Upload + metadata + privacy | Quota limits — batch & respect daily cap |
| Analytics | YouTube Analytics API v2 | Views, retention, CTR, likes per video | Quota limits — back-off polling cadence |
| Composition | FFmpeg (in worker process) | Stitch clips + audio + captions + music | CPU-bound; sized worker pool |

### Out of scope for MVP

- Voice cloning (custom user voices) — preset ElevenLabs voices only
- Multi-language output — English only
- Avatar / talking-head modes
- Live editing UI (timeline editor) — users regenerate or reject, not edit clip-by-clip
- Cross-posting to TikTok/Instagram — YouTube only
- Mobile app — web only
- Collaboration / multi-user-per-account

### Hard non-functional requirements

- A user is never charged credits for a job that didn't produce a finished video. Credits debit atomically and refund automatically on terminal failure.
- A worker crash mid-pipeline must not lose progress beyond the in-flight stage. Resumable from last persisted state.
- The system enforces per-tenant credit balance with pre-flight checks before each expensive stage.

---

## 2. Data Model & Lineage

The data model is the spine of the system. Every other section reads from or writes to these tables. The lineage chain `prompt → script → scene plan → assets → published video → analytics` must be intact end-to-end so the optimizer (Section 8) has training signal.

### Entity relationships

```
User ──< Channel ──< ContentSeries ──< Job ──< Scene ──< Asset
                                       │
                                       ├──< CreditTransaction
                                       ├──< PublishedVideo ──< AnalyticsSnapshot
                                       └──< ApprovalEvent
```

### Tables

**`users`**
- `id` (uuid, pk), `email` (unique), `clerk_user_id` (unique)
- `credit_balance` (int) — denormalized cache of ledger sum, reconciled nightly
- `created_at`, `updated_at`

**`channels`** — connected YouTube channel
- `id`, `user_id` (fk), `youtube_channel_id`, `name`, `handle`
- `oauth_refresh_token` (encrypted at rest, AES-GCM), `oauth_access_token`, `oauth_expires_at`
- `connected_at`, `disconnected_at` (nullable, soft-delete)

**`content_series`** — recurring content stream
- `id`, `channel_id` (fk)
- `name`, `niche`, `target_format` (`short` | `long`)
- `prompt_template` — user-editable prompt seed
- `cadence_cron` — when to enqueue next job
- `auto_approve_after_hours` (nullable; null = manual only)
- `voice_id`, `music_mood`, `style_preset`
- `paused_at` (nullable), `learning_profile_id` (fk, nullable)
- `next_run_at` — computed from cadence_cron, drives scheduler

**`jobs`** — one job = one video generation attempt
- `id`, `series_id` (fk, nullable for one-offs), `channel_id` (fk), `user_id` (fk, denormalized)
- `state` (enum, see Section 3), `format` (`short` | `long`)
- `credit_cost` (computed at creation, debited atomically)
- `prompt_resolved` (actual prompt after merging template + learning hints)
- `script_text`, `script_metadata_json` (title, description, tags, hook, CTA, thumbnail_prompt)
- `scene_plan_json`
- `final_video_asset_id` (fk assets, nullable until composed)
- `final_thumbnail_asset_id` (fk assets, nullable)
- `error_code`, `error_detail` (nullable)
- `current_stage_attempt`
- `created_at`, `updated_at`, `state_changed_at`

**`scenes`** — one row per scene in a job
- `id`, `job_id` (fk), `idx`
- `image_prompt`, `narration_text`
- `image_asset_id`, `clip_asset_id`, `audio_asset_id` (fk assets, nullable until generated)
- `kling_external_job_id`
- `state` (enum: `pending`, `image_done`, `clip_done`, `audio_done`, `done`, `failed`)
- `attempt`, `last_error`

**`assets`** — opaque file references in R2
- `id`, `job_id` (fk)
- `kind` (enum: `scene_image`, `scene_clip`, `scene_audio`, `final_video`, `thumbnail`, `voiceover_full`, `caption_track`)
- `s3_key`, `mime`, `bytes`, `duration_s` (nullable)
- `created_at`

**`credit_transactions`** — append-only ledger
- `id`, `user_id` (fk)
- `delta` (signed int)
- `reason` (enum: `purchase`, `job_debit`, `job_refund`, `manual_adjustment`, `promo`)
- `job_id` (fk, nullable)
- `stripe_payment_intent_id` (nullable, unique where non-null — webhook idempotency)
- `created_at`
- Constraint: `SUM(delta) WHERE user_id = X` must equal `users.credit_balance`. Reconciled nightly.
- Partial unique index `(job_id) WHERE reason = 'job_refund'` prevents double-refund.

**`approval_events`** — every approve/reject/edit
- `id`, `job_id` (fk), `user_id` (fk)
- `action` (enum: `approved`, `rejected`, `regenerated`, `auto_approved`, `edited_metadata`)
- `reason_text` (nullable), `created_at`

**`published_videos`** — one row per successful YouTube upload
- `id`, `job_id` (fk, unique), `channel_id` (fk)
- `youtube_video_id` (unique), `published_at`
- `last_analytics_pull_at`, `next_analytics_pull_at` (drives polling scheduler with back-off cadence)

**`analytics_snapshots`** — time series of YouTube metrics
- `id`, `published_video_id` (fk), `pulled_at`
- `views`, `watch_time_minutes`, `avg_view_duration_s`, `ctr_pct`, `likes`, `comments`, `subs_gained`

**`learning_profiles`** — per-channel "what works here"
- `id`, `channel_id` (fk, unique)
- `top_performers_job_ids` (jsonb)
- `negative_signal_job_ids` (jsonb — captured but not used in MVP prompt)
- `aggregate_features_json` (hooks, optimal duration, title patterns, niche keywords)
- `last_recomputed_at`

**`unit_costs`** — internal cost accounting (not user-facing)
- `id`, `job_id` (fk)
- `provider` (enum), `units` (tokens/images/seconds/chars), `usd_cost`
- Drives margin dashboards and pricing-table tuning.

**`job_events`** — audit trail of state transitions
- `id`, `job_id` (fk)
- `from_state`, `to_state`, `at`, `worker_id`, `attempt`, `error_detail` (nullable)

**`credit_packs`** — config-table SKUs (editable without redeploy)
- `id`, `name`, `credits`, `price_usd`, `stripe_price_id`, `active`

**`video_pricing`** — per-format credit costs (config-table)
- `format`, `credits`

**`promo_codes`** — promo grants
- `code`, `credits`, `single_use`, `expires_at`
- Join table `promo_redemptions(user_id, code)` to prevent reuse.

### Indices

- `jobs(state, state_changed_at)` — workers query "pending jobs in stage X"
- `jobs(user_id, created_at desc)` — user dashboard
- `credit_transactions(user_id, created_at desc)` — billing history + reconciliation
- `published_videos(next_analytics_pull_at) WHERE next_analytics_pull_at IS NOT NULL` — analytics scheduler
- `scenes(job_id, idx)` — composition reads scenes in order
- `content_series(next_run_at) WHERE paused_at IS NULL` — cadence scheduler

### Storage & encryption

- All R2 assets: server-side encryption.
- `oauth_refresh_token`: app-level AES-GCM with key from `ENCRYPTION_KEY` env var. Never log decrypted.
- Stripe customer ids on `users`; PCI scope stays at Stripe.

---

## 3. Pipeline State Machine & Orchestration

### Job-level states

```
created
  → scripting
    → scene_plan
      → scene_fanout (per-scene sub-state machine)
        → composing
          → ready_for_review
            → uploading (after approval — manual or auto-timeout)
              → published
[any stage] → failed (terminal; credits refunded)
```

A user-rejected `ready_for_review` can spawn a new Job (regenerate) at fresh credit cost.

### Per-scene sub-state machine

Scenes fan out in parallel within Kling per-account concurrency limits.

```
pending → image_done → clip_pending → clip_done → audio_done → done
                          │
                          └─ kling_polling (loop with back-off)
```

Job advances to `composing` only when all scenes are `done` or any is terminally `failed`.

### Workers and queues (arq, Redis-backed)

| Queue | Concurrency | Stage handlers |
|---|---|---|
| `q.script` | high | `generate_script`, `generate_scene_plan` |
| `q.image` | medium | `generate_scene_image` |
| `q.clip_submit` | low (rate-limited) | `submit_kling_job` |
| `q.clip_poll` | recurring (every 30s) | `poll_kling_jobs` (batched) |
| `q.audio` | medium | `generate_scene_audio` |
| `q.compose` | low (CPU/disk-bound) | `compose_final_video` |
| `q.upload` | low | `upload_to_youtube` |
| `q.analytics` | recurring | `pull_analytics` (batched by next_pull time) |
| `q.scheduler` | recurring (cron-like) | `enqueue_due_series_jobs`, `auto_approve_expired`, `recompute_learning_profiles`, `reconcile_credits` |

### Critical orchestration rules

1. **State transitions are atomic Postgres updates** with `WHERE state = $expected` guard. If 0 rows affected, another worker won — exit silently.
2. **Idempotency:** every stage handler checks "already done" before doing work. Crash recovery is automatic.
3. **Credit debits are atomic and pre-flight.** Serializable transaction that checks balance and debits before submitting to expensive providers (Kling).
4. **No cross-stage state in worker memory.** Read from Postgres at start, persist before exit.
5. **Retries with exponential back-off**, capped per stage. Retry counts on `scenes.attempt` / `jobs.current_stage_attempt`.
6. **Kling polling is decoupled from submission.** A separate batched poller queries many in-flight jobs per call. Reduces API pressure dramatically.

### Failure handling & refund policy

| Stage | If exhausted retries terminally fail | Credit policy |
|---|---|---|
| `scripting` / `scene_plan` | Job fails | Full refund |
| `scene_fanout` (any scene) | Job fails | Full refund (all-or-nothing) |
| `composing` | Job fails | Full refund |
| `uploading` | Job stays `ready_for_review` (user can retry) | No debit (upload free) |

Principle: **the user is only charged when a finished, approvable video exists.**

### Scheduling

`q.scheduler` runs every minute. For each due series:
1. Check user credit balance.
2. Create `Job` row in `created` state.
3. Enqueue `q.script.generate_script`.
4. Update `content_series.next_run_at` based on `cadence_cron`.

Insufficient balance → soft warning on series, retry next tick.

A second recurring task auto-approves jobs whose `auto_approve_after_hours` window has elapsed.

### Observability hooks

- Every state transition writes a `job_events` row.
- Per-stage timing histograms (Prometheus).
- Per-tenant cost meter (writes to `unit_costs`) for margin tracking.

### Per-stage retry budgets

| Stage | Max attempts | Back-off |
|---|---|---|
| Script | 3 | 5s, 30s, 2min |
| Scene plan | 2 | 10s, 1min |
| Image (per scene) | 3 (incl. 1 reprompt) | 5s, 30s |
| Kling submit | 3 | 30s, 2min, 5min |
| Kling poll-completion timeout | 30 min × 2 attempts | n/a |
| TTS | 3 | 5s, 30s, 2min |
| Compose | 2 | 60s |
| Upload | 5 | 30s, 2min, 10min, 1h, 6h |

---

## 4. Credit System & Billing

### Principles

1. **The ledger is the source of truth.** `users.credit_balance` is a denormalized cache of `SUM(credit_transactions.delta)`, reconciled nightly. If they ever disagree, the ledger wins.
2. **Credits move only in atomic Postgres transactions** wrapping the operation that triggers them.

### Credit packs (initial SKUs, table-driven)

| Pack | Credits | Price (USD) | Per-credit |
|---|---|---|---|
| Starter | 50 | $9 | $0.18 |
| Creator | 250 | $39 | $0.156 |
| Pro | 1000 | $129 | $0.129 |

### Per-video pricing (initial, table-driven)

| Format | Credits |
|---|---|
| Short (≤60s vertical) | 5 |
| Long (3–10 min horizontal) | 25 |

Real numbers tuned post-MVP based on observed unit cost.

### Purchase flow

User → Stripe Checkout (hosted) → Stripe webhook `payment_intent.succeeded` → handler validates signature, looks up pack from metadata, inserts `credit_transaction(delta=+N, reason=purchase, stripe_payment_intent_id=X)` and updates `users.credit_balance` in one Postgres transaction. Idempotent via unique constraint on `stripe_payment_intent_id`.

### Debit flow (job creation)

```sql
BEGIN;
  SELECT credit_balance FROM users WHERE id = $user_id FOR UPDATE;
  -- Pre-flight check
  IF credit_balance < job.credit_cost THEN ROLLBACK; ...
  -- Create job + debit
  INSERT INTO jobs (..., credit_cost = $cost, state = 'created');
  INSERT INTO credit_transactions (..., delta = -$cost, reason = 'job_debit', job_id = $job_id);
  UPDATE users SET credit_balance = credit_balance - $cost WHERE id = $user_id;
COMMIT;
```

`FOR UPDATE` lock prevents concurrent over-spending when balance is exactly enough for one job.

### Refund flow (job terminal failure)

Append `credit_transaction(delta=+$cost, reason='job_refund', job_id=...)` and update balance, in one transaction. Idempotency from partial unique index on `(job_id) WHERE reason='job_refund'`.

### Reconciliation

Nightly query compares `users.credit_balance` to ledger sum. Mismatches alert ops and self-heal by overwriting cache with ledger sum.

### Cost accounting (internal)

Workers write to `unit_costs` at each external API call. Feeds margin dashboards; alerts when 7-day rolling unit cost approaches credit price.

### Stripe-side refunds & chargebacks

Webhook on `charge.refunded` appends negative `manual_adjustment` for the credits granted, regardless of how many were already spent (balance can go negative — prevents fraud loophole).

### Free credits / promo

`promo_codes` table grants `+N` credits with `reason='promo'`. Single-use per user via redemption join table.

---

## 5. Generation Pipeline Detail

### 5.1 Script generation

**Input:** `series.prompt_template` + format + learning hints (top-3 high-performers as few-shot).
**Provider:** OpenAI GPT-4-class (config-driven model id; default `gpt-4o`).
**Output:** structured JSON via response_format — `title`, `description`, `tags`, `thumbnail_prompt`, `hook_text`, `script`, `estimated_duration_s`.
**Validation:** estimated_duration within ±20% of format window; otherwise reroll once with explicit length constraint.

### 5.2 Scene plan generation

**Input:** `script_text`, `target_format`, `style_preset`.
**Output:** array of `{idx, narration_text, image_prompt, duration_target_s, motion_hint}`.
**Constraints:**
- Sum of `duration_target_s` matches `estimated_duration_s` ±10%.
- Number of scenes within format-specific bounds (shorts: 4–10; long-form: 15–40).
- Joined `narration_text` equals `script_text` exactly (stable lineage).
- `image_prompt` rewritten to inject style consistency tokens.

Retry up to 2 times with diff-based feedback.

### 5.3 Scene image generation (parallel)

**Provider:** OpenAI `gpt-image-1`.
**Sizes:** `1024x1792` (vertical for shorts) or `1792x1024` (horizontal for long-form). Quality: `high`.
**Failure handling:**
- Content-policy refusal → single tone-down reprompt → second refusal marks scene `failed` → job-level failure → full refund.
- Rate-limit → exponential back-off within attempt budget.

### 5.4 Kling clip submission + polling

**Submit (`q.clip_submit`):**
- Input: scene image URL, motion hint, duration (rounded to Kling-supported 5s or 10s).
- Concurrency-bounded by `KLING_MAX_INFLIGHT` (default 4).
- Persists `kling_external_job_id` on scene.

**Poll (`q.clip_poll`, batched every 30s):**
- Query all in-flight scenes; status-check in batches.
- Completed → download MP4 → R2 → set `clip_asset_id` → state `clip_done`.
- Failed → increment attempt; retry submit if under budget; else mark `failed`.
- Timed-out (>30 min wall clock) → treat as failed.

### 5.5 TTS / voiceover (parallel; can run alongside 5.3/5.4)

**Provider:** ElevenLabs.
**Model:** `eleven_multilingual_v2` (or v3 when stable) — config-driven.
**Settings:** voice id from series; stability/similarity from `voices` lookup.
**Outputs:**
- Audio (MP3/WAV) → R2 → `audio_asset_id`.
- Word-level alignment JSON → R2 → kind `caption_track`.

**Fallback:** if alignment fails but TTS succeeded, run Whisper forced-alignment. If both fail, ship without burned captions and log warning.

### 5.6 Composition (CPU-bound, FFmpeg)

Worker downloads all scene clips, scene audio, caption tracks, and selected music bed.

FFmpeg pipeline:
1. Concat scene clips → primary video track.
2. Concat scene audio → primary voiceover track.
3. Music bed: loop to match duration, sidechain compress (-18dB ducking under voice).
4. Mix voiceover + ducked music.
5. Captions: ASS subtitle file from word-level alignment, styled per `style_preset`, burned in via `subtitles=` filter.
6. Optional intro/outro from series config.
7. Output: H.264 / yuv420p / AAC, 1080p (long) or 1080×1920 (short), CRF 20, faststart.

Thumbnail generated in parallel via `gpt-image-1` from `script_metadata_json.thumbnail_prompt`, sized 1280×720.

Final video → R2 → `final_video_asset_id` → state `ready_for_review`.

### 5.7 User-supplied thumbnail (optional)

Approval UI accepts custom thumbnail upload. Stored as new `Asset(kind=thumbnail)`; `final_thumbnail_asset_id` swapped. Auto-generated thumbnail retained for fallback / future A/B.

### 5.8 YouTube upload

Triggered on approval (manual or auto-timeout):
1. Refresh OAuth token if expiring within 5 min.
2. `videos.insert` resumable upload.
3. `thumbnails.set`.
4. Set privacy from series config (`public` / `unlisted` / `private`).
5. **First 5 uploads per new YouTube connection default to `unlisted`** as account-suspension protection.
6. Persist `youtube_video_id` → create `published_videos` row.
7. Schedule first analytics pull at `published_at + 24h`.

**Quota awareness:** 10,000-unit daily quota per project; `videos.insert` costs 1600 units. Tracker pauses uploads that would exceed quota; uploads resume next day.

### Style consistency note (known MVP limitation)

Style consistency across scenes is via prompt-injection only (no IP-Adapter / LoRA / reference-image conditioning). Future work: feed a generated character/style reference image into subsequent prompts via `gpt-image-1` edit mode.

### Parallelism note

TTS runs in parallel with image+clip generation (depends only on scene narration text, not visuals). Cuts wall-clock generation time substantially.

---

## 6. Frontend & API Surface

### Frontend pages (Next.js App Router)

| Route | Purpose | Auth |
|---|---|---|
| `/` | Marketing / landing | public |
| `/pricing` | Credit packs | public |
| `/sign-in`, `/sign-up` | Auth (Clerk-hosted) | public |
| `/dashboard` | Per-channel summary | required |
| `/channels` | Connect / disconnect YouTube | required |
| `/channels/[id]/series` | List & create series | required |
| `/series/[id]` | Edit series | required |
| `/series/[id]/run-now` | Trigger one-off | required |
| `/queue` | Approval queue | required |
| `/jobs/[id]` | Job detail with live progress | required |
| `/published` | Published videos with analytics | required |
| `/billing` | Buy credits, transaction history | required |
| `/settings` | Profile, defaults | required |

### Shared components

- `<JobProgressBar>` (WebSocket-driven)
- `<ScenePreviewGrid>`
- `<VideoPreviewPlayer>`
- `<CreditBadge>` (sticky in nav)
- `<StripeCheckoutButton>`

### API surface (FastAPI, prefix `/api/v1`)

#### Auth & user

| Method | Path |
|---|---|
| GET | `/me` |

#### Channels

| Method | Path |
|---|---|
| GET | `/channels` |
| POST | `/channels/connect/start` |
| GET | `/channels/connect/callback` |
| DELETE | `/channels/{id}` |

#### Series

| Method | Path |
|---|---|
| GET | `/channels/{id}/series` |
| POST | `/channels/{id}/series` |
| GET | `/series/{id}` |
| PATCH | `/series/{id}` |
| POST | `/series/{id}/pause` |
| POST | `/series/{id}/resume` |
| POST | `/series/{id}/run-now` |

#### Jobs

| Method | Path |
|---|---|
| GET | `/jobs?state=...&channel_id=...&cursor=...` |
| GET | `/jobs/{id}` |
| POST | `/jobs/{id}/approve` |
| POST | `/jobs/{id}/reject` (optional `regenerate=true`) |
| PATCH | `/jobs/{id}/metadata` |
| POST | `/jobs/{id}/thumbnail` (multipart) |

Regeneration debits fresh credits (no free regenerations in MVP).

#### Billing

| Method | Path |
|---|---|
| GET | `/billing/packs` |
| POST | `/billing/checkout` |
| POST | `/billing/webhook` (signature-validated, idempotent) |
| GET | `/billing/transactions?cursor=...` |

#### Analytics (read-only)

| Method | Path |
|---|---|
| GET | `/published?channel_id=...&cursor=...` |
| GET | `/published/{id}/timeseries` |

#### WebSocket

| Path |
|---|
| `WS /api/v1/ws/jobs/{id}` (auth via short-lived signed token from job GET) |

#### Internal (IP-allowlisted or service-token-auth)

| Method | Path |
|---|---|
| POST | `/internal/scheduler/tick` |
| POST | `/internal/analytics/poll` |
| POST | `/internal/reconciliation/credits` |

### Asset access

R2 buckets are private. Backend issues short-lived (15 min) signed URLs after server-side ownership check. Final published videos served by YouTube.

### Conventions

- Cursor-paginated list endpoints with `Link` header.
- Standardized error envelope: `{ "error": { "code", "message", "detail" } }`.
- `Idempotency-Key` header on mutating endpoints (24h replay window).
- Per-user 60 req/min rate limit; webhook unlimited.

### WebSocket event shapes

```json
{ "type": "job.state_changed", "job_id": "...", "from": "scripting", "to": "scene_plan", "at": "..." }
{ "type": "scene.state_changed", "job_id": "...", "scene_idx": 3, "to": "clip_done" }
{ "type": "job.failed", "job_id": "...", "error_code": "kling_timeout", "error_detail": {} }
{ "type": "job.ready_for_review", "job_id": "...", "preview_url": "<signed>" }
```

Frontend falls back to 5s polling if WS disconnects.

---

## 7. Repository Layout & Code Organization

Monorepo with pnpm workspaces; two apps + shared types.

### Top level

```
faceless-yt/
├── apps/
│   ├── web/                    # Next.js (App Router) frontend
│   └── api/                    # FastAPI backend + workers
├── packages/
│   ├── shared-types/           # OpenAPI-generated TS types
│   └── eslint-config/
├── infra/
│   ├── docker/
│   ├── compose/                # local dev docker-compose
│   └── deploy/                 # railway.json / Procfiles
├── docs/
│   └── superpowers/specs/
├── .github/workflows/
├── pnpm-workspace.yaml
├── package.json
└── README.md
```

### Backend (apps/api) — one Python package, multiple entrypoints

```
apps/api/src/faceless/
├── main.py            # FastAPI app entry
├── worker.py          # arq worker entry
├── scheduler.py       # cron-tick entry
├── api/               # HTTP layer (thin)
│   ├── deps.py        # auth, db session, settings, ownership
│   ├── errors.py
│   ├── ws.py
│   └── routes/        # one file per resource
├── domain/            # pure types — no I/O
│   ├── models.py      # Pydantic value objects
│   ├── states.py      # state-machine enums + transitions
│   └── pricing.py
├── db/
│   ├── base.py
│   ├── models/        # one file per table
│   └── repos/         # query helpers
├── services/          # business logic / orchestration glue
│   ├── credits.py
│   ├── scheduling.py
│   ├── approval.py
│   ├── transitions.py
│   └── lineage.py
├── pipeline/          # state machine handlers
│   ├── stages/        # 1:1 with state transitions
│   │   ├── script.py
│   │   ├── scene_plan.py
│   │   ├── scene_image.py
│   │   ├── kling_submit.py
│   │   ├── kling_poll.py
│   │   ├── tts.py
│   │   ├── compose.py
│   │   └── upload.py
│   ├── retry.py
│   └── idempotency.py
├── providers/         # REPLACEABLE adapters behind protocols
│   ├── llm/           {base.py, openai_llm.py}
│   ├── image/         {base.py, openai_image.py}
│   ├── video/         {base.py, kling.py}
│   ├── tts/           {base.py, elevenlabs.py}
│   ├── alignment/     {base.py, whisper.py}
│   ├── youtube/       {data_api.py, analytics_api.py}
│   └── stripe_client.py
├── compose/           # FFmpeg layer (pure functions)
│   ├── filters.py
│   ├── captions.py
│   ├── ducking.py
│   └── runner.py
├── storage/           {s3.py, tmp.py}    # s3.py adapts to R2 via endpoint config
├── auth/              {clerk.py, oauth_youtube.py}
├── observability/     {logging.py, metrics.py, tracing.py}
├── config.py          # pydantic-settings
└── crypto.py          # AES-GCM
```

### Frontend (apps/web)

```
apps/web/src/
├── app/                      # App Router routes (matches Section 6)
│   ├── (marketing)/
│   ├── (app)/                # auth-required group
│   └── api/                  # client-only proxies if needed
├── components/
│   ├── job/                  # JobProgressBar, ScenePreviewGrid, ApprovalCard
│   ├── billing/
│   ├── channels/
│   └── ui/                   # primitives
├── lib/                      # api-client, ws, auth, stripe
├── hooks/                    # useJob, useCredits, ...
└── styles/
```

### Key boundary

`pipeline/stages/*` import only `providers/*/base.py` protocols. Concrete provider classes wired at startup. Swapping Kling for Runway = new `providers/video/runway.py` + config flag. No pipeline code changes.

### Configuration

All config via env vars typed by `pydantic-settings`. Loaded from Railway secrets per environment. Never committed.

```
DATABASE_URL=postgres://...
REDIS_URL=redis://...
S3_BUCKET=...                 # R2 bucket
S3_ENDPOINT=https://<account>.r2.cloudflarestorage.com
S3_ACCESS_KEY=...
S3_SECRET_KEY=...
OPENAI_API_KEY=...
KLING_API_KEY=...
KLING_MAX_INFLIGHT=4
ELEVENLABS_API_KEY=...
YOUTUBE_OAUTH_CLIENT_ID=...
YOUTUBE_OAUTH_CLIENT_SECRET=...
STRIPE_SECRET_KEY=...
STRIPE_WEBHOOK_SECRET=...
CLERK_SECRET_KEY=...
ENCRYPTION_KEY=...            # base64-encoded 32 bytes for AES-GCM
SENTRY_DSN=...
LOG_LEVEL=info
```

### Local dev

`docker-compose.yml` brings up Postgres + Redis + MinIO (S3-compatible local stand-in for R2) + api + worker + scheduler + web. `make dev` to start; migrations run on startup.

### Deployment (Railway)

Four Railway services from one repo, each with its own start command:
- `api` — `uvicorn faceless.main:app --host 0.0.0.0 --port $PORT`
- `worker` — `arq faceless.worker.WorkerSettings`
- `scheduler` — Railway native cron, runs internal scheduler/analytics endpoints on schedule
- `web` — `next start -p $PORT`

Postgres and Redis as Railway managed addons; private networking between services.

---

## 8. Learning Loop & Engagement Optimization

Goal: each channel gets *better at its niche* over time without training a model. Mechanism: **per-channel few-shot conditioning** of the script-generation prompt, refreshed as analytics arrive.

### Data inputs

Lineage from Section 2 captures everything: `jobs.script_text` + `script_metadata_json` + `scene_plan_json` → `published_videos.youtube_video_id` → `analytics_snapshots` time series.

### Analytics polling cadence

| Age of video | Pull cadence |
|---|---|
| 0–24h | every 1h |
| 1–7d | every 6h |
| 7–30d | daily |
| 30d+ | weekly |

Driven by `published_videos.next_analytics_pull_at`. Batched cron every 15 min queries due videos in batches of 50 via YouTube Analytics multi-id queries. Daily quota tracked.

### Performance score

Computed when a video reaches "mature" age (7 days post-publish):

```
score = w1 * (avg_view_duration / video_duration)        # retention rate
      + w2 * normalize(ctr_pct, channel_baseline)         # CTR vs. channel mean
      + w3 * normalize(views, channel_baseline)           # views vs. channel mean
      + w4 * (likes / views)                              # engagement
```

Initial weights: `w1=0.5, w2=0.25, w3=0.15, w4=0.10`. Per-channel z-score normalization makes small/large channels comparable to themselves.

### Daily learning-profile recompute

`q.scheduler.recompute_learning_profiles` runs nightly. Per channel:
1. Score every mature video (≥7 days old).
2. Pick top 3 → `top_performers_job_ids`.
3. Pick bottom 3 → `negative_signal_job_ids` (captured, not used in MVP prompt).
4. Distill `aggregate_features_json`:
   - Hook patterns (first ~10 words of each top performer's script, verbatim).
   - Optimal duration (median `avg_view_duration` of top performers).
   - Title patterns (top 3 verbatim).
   - Niche keywords (TF-IDF top terms — captured, not used in MVP prompt).
5. Update `last_recomputed_at`.

Channels with <3 mature videos: empty profile → script generation runs unconditioned.

### Script generation with learning hints

System prompt for `pipeline.stages.script.generate_script` includes:
- The user's prompt template / niche.
- 3 verbatim top-performer examples with their retention/CTR.
- Target duration matching the top-performer median.

The LLM does the rest via in-context pattern matching.

### Out of scope for MVP

- A/B testing of script variants.
- Regression model on (features → engagement).
- Meta-prompt tuning (the meta-prompt is human-edited, version-controlled).
- Cross-channel learning.
- Thumbnail-style learning.

### `approval_events` and the loop

User approve/reject/regenerate is **persisted but not fed back** into the optimizer in MVP. Lineage stays intact for future use.

### Failure modes

- **No published videos** → empty profile → unconditioned generation. Acceptable.
- **Fluke top performer** → daily recompute washes it out as more data arrives.
- **YouTube Analytics API down** → polling retries; profile uses stale data. Acceptable.

---

## 9. Testing, Observability, Security & Risks

### 9.1 Testing strategy

**Unit tests (fast, no I/O):**
- `domain/` (pricing math, state-transition validity, score computation)
- `compose/` (filter graph string builders, ASS subtitle generation)
- `services/credits.py` (debit/refund logic, mocked DB)
- Provider adapter request shaping / response parsing (network mocked)

**Integration tests (Postgres + Redis + MinIO via docker-compose, providers mocked at HTTP layer):**
- Each pipeline stage: feed a job in state X, run handler, assert state Y + side effects.
- Full happy path: job from `created` → `published` with all providers stubbed.
- Failure paths: each terminal-failure case asserts refund and balance restoration.
- Concurrency: two workers race on the same job → exactly one wins.

**End-to-end smoke (manual / staging, not in CI):**
- One scripted "real video" run against staging with cheapest models, upload to private test YouTube channel.
- Run weekly via Railway cron in staging; alert on failure.

**Cost discipline:** No real provider calls in CI. Provider-protocol boundary makes mocking trivial.

**Coverage targets (advisory):** 80% on `domain/`, `services/`, `pipeline/stages/`. Lower on `providers/`. FFmpeg covered by integration tests with tiny test clips.

### 9.2 Observability

**Logs:** `structlog` JSON to stdout (Railway captures and indexes). Every line has `request_id`, `job_id`, `user_id`, `stage`, `attempt`. Provider responses logged at `debug` only; tokens/keys never logged.

**Metrics:** Prometheus exporter on each service `:9090/metrics`. Grafana (self-hosted on Railway or Grafana Cloud free tier).

Key metrics:
- `job_state_transitions_total{from, to}`
- `job_stage_duration_seconds{stage}` (histogram)
- `provider_call_total{provider, status}`
- `provider_call_duration_seconds{provider}` (histogram)
- `credit_balance_total` (gauge)
- `kling_inflight` (gauge)
- `youtube_quota_units_used` (gauge per project per day)

**Errors & alerts:** Sentry across api/worker/scheduler. Alerts on:
- Credit reconciliation mismatch (any non-zero diff)
- YouTube quota >90% of daily limit
- Worker exception rate >1/min for 5 min
- Job pipeline P95 wall-time >2× rolling baseline
- Stripe webhook delivery failure

**Per-job audit trail:** `job_events` table; `/jobs/{id}/events` admin endpoint. 90-day hot retention; older archived to R2 as JSONL.

### 9.3 Security

**Secrets:** All in Railway env vars (encrypted at rest by Railway). `oauth_refresh_token` AES-GCM encrypted with `ENCRYPTION_KEY`; rotation procedure documented.

**Auth & ownership:** Clerk JWT verified server-side on every authenticated route. Centralized `current_user_owns(resource)` FastAPI dependency enforces tenant isolation on every endpoint. Soft-deletes still enforce ownership. Integration tests assert cross-user 403.

**OAuth scope minimization (YouTube):** `youtube.upload`, `youtube.readonly`, `yt-analytics.readonly`. Nothing else.

**Asset isolation:** Private R2 buckets; signed URLs only (15-min TTL); ownership checked before signing. Naming: `{user_id}/{job_id}/{kind}/{uuid}`.

**Rate limiting:** Per-user 60 req/min on auth-required (Redis token bucket). Webhook excluded. Public marketing 600 req/min by IP.

**Content safety:** OpenAI moderation implicit on `gpt-image-1`. Optional pre-flight script through `omni-moderation-latest` before Kling stage; reject hard categories.

**PII / data handling:** Email + Stripe-managed billing only. User-deletion endpoint cascades to R2. 30-day tombstone on email re-use.

### 9.4 Top risks and mitigations

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Kling outage / price change | Medium | Critical | Provider-protocol swap to Runway/Luma; daily smoke test; status page |
| OpenAI content-policy refusals on niche content | High | High | Reprompt fallback; "safe-niche" guidance; future fallback to Flux/SDXL |
| YouTube account suspension from auto-uploads | Medium | Critical (per user) | First 5 uploads per channel default `unlisted`; ToS warning during connect; never publish under our account |
| Cost-per-video exceeds credit price | Medium | Margin collapse | `unit_costs` monitored; alerts; pricing tables editable |
| Credit-refund failure leaves user uncompensated | Low | Trust-killer | Mandatory refund step in `failed` transition; reconciliation catches drift; manual support workflow |
| Worker crash mid-FFmpeg compose | Medium | Wasted minutes | Idempotent stage; tmp reset; retry once; refund on second failure |
| Inconsistent style across scenes | High | Quality (not crash) | Style-injection in scene plan; documented MVP limitation |
| YouTube quota exhausted | Medium | Upload delay | Quota tracker; queue-and-resume next day; future: multi-project |
| Stripe disputes / chargebacks | Low–Medium | Direct loss | Webhook honors refunds; balance can go negative |
| Multi-tenant data leak | Low | Catastrophic | Centralized ownership dependency; cross-user 403 integration test; signed-URL audit |

### 9.5 Definition of "MVP done"

System is MVP-complete when ALL of these are true:

1. New user: sign up → buy credits (Stripe) → connect YouTube → create series → see video in approval queue → approve → published on YouTube.
2. Scheduled series produces videos on cadence without manual intervention.
3. Credit ledger reconciles with zero drift over a 7-day staging soak.
4. Auto-approval timeout works end-to-end.
5. Engagement-driven optimization is wired (analytics polled, learning profile recomputed nightly, hints injected into script gen) — even if measurable lift takes longer than MVP to demonstrate.
6. Smoke test on staging runs nightly and passes.
7. All sections of this spec have corresponding code paths. No half-built features.

Explicitly NOT required for MVP:
- High render volume (single Railway worker pool is fine)
- Pretty marketing site (functional landing OK)
- Multi-language support
- Cross-platform publishing
- Advanced editing UI
