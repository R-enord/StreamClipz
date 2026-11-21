# StreamClipz architecture

Status: planning and Phase 0 (foundation). This document is kept generic on purpose,
because the repository is public. Account names, campaign details and personal data
do not belong here.

## Purpose

Turn long live streams into short clips, with a person approving every clip before it is
published, and an audit trail for every decision.

## Principles

1. **A person approves before anything is published.** The system never posts on its own.
2. **Every clip traces to its source:** the stream, the permission or campaign that allows
   its use, who approved it, and when.
3. **Allowed capture only.** Use official APIs or the methods a source's terms allow. Never
   bypass access controls, bot checks or platform restrictions. If a check appears, report it.
4. **Local first, hosted later.** It runs on one computer now. The same code should run on a
   server later without a rewrite.
5. **Small, tested, reversible changes.** Back up before any change that deletes or overwrites data.
6. **No secrets or personal data in git.** Settings with keys, databases, media and logs stay out.

## Components

| Component | Purpose | Status |
| --- | --- | --- |
| Web app (phone-friendly) | Sign-in, dashboard, review queue, status | Login and dashboard exist |
| Core | Data models, settings, job queue | Planned (Phase 1) |
| Ingest | Source registry, import and recording, one adapter per platform | Planned (Phase 2) |
| Analysis | Finds candidate moments (audio level first, transcripts later) | Planned (Phase 3) |
| Render | Cuts and captions clips; originals pipeline with voice and graphics | Planned (Phase 3, 6) |
| Review | Approval queue and audit log | Planned (Phase 4) |
| Scheduler | Posting plan. Publishing stays manual until a platform API is approved | Planned (Phase 5) |
| Operations | Health checks, backups, logs, status file | Partly exists (status endpoint) |

## Data model (first version)

- **Source:** where a stream comes from: platform, channel, and the rule that allows its use.
- **Stream:** one broadcast or file: source, title, start time, length, file location, checksum, whether it has audio.
- **Moment:** a candidate window inside a stream, with a score and the reason it was chosen.
- **Clip:** a rendered output: moment, file location, checksum, rights note, status.
- **Review:** an approve or reject decision with a reason, the reviewer and the time.
- **Post:** a planned publish: clip, account, planned time, status, published link.
- **Job:** background work: kind, parameters, status, attempts, lease expiry, last error.
- **AuditEvent:** append-only log of who did what to which record, and when.

Clip states: `draft` → `needs_review` → `approved` or `rejected`; `approved` → `scheduled`
→ `published` → `archived`. Only a person can move a clip to `approved`.

## Product flow

The stages, specs and acceptance test come from an example video. See [PRODUCT.md](PRODUCT.md).

## Stack

Decided in [ADR 0001](decisions/0001-stack.md): Python 3.12, FastAPI, SQLAlchemy with Alembic,
SQLite now and PostgreSQL later, pydantic-settings, pytest, ruff, GitHub Actions, Dependabot,
ffmpeg for media.

## Phases and done-criteria

**Phase 0: Foundation** (done)
- Repository, lint, tests and CI run on every push.
- Architecture, decisions and runbook written.
- Login and dashboard tested.
- Done when: CI is green and the runbook works on the laptop.

**Phase 1: Core and job queue** (done)
- Database migrations with Alembic. Job table with leases, retries and timeouts.
- Done when: a job survives a restart and is retried once after a simulated failure.
- Result: `core/` holds the models, migrations, queue and worker. `tests/test_worker.py`
  covers the restart and retry cases, and `tests/test_migrations.py` covers the upgrade of the
  first version's database.

**Phase 2: Sources and import**
- Source registry. Import a stream file the owner downloads, with checksum and metadata.
- One platform adapter, only after its terms are checked.
- Done when: an imported file appears as a Stream with the right length and an audio check.

**Phase 3: Moments and clips**
- Find candidate moments and render clips from a sample file.
- Done when: golden tests pass on a short sample and a 1-hour sample produces reviewed clips.

**Phase 4: Review on the phone**
- Approve and reject with reasons, full audit trail, sign-in per person.
- Done when: every approval in the database has a reviewer, a time and an audit event.

**Phase 5: Posting plan and analytics**
- Posting plan with checklists. Manual posting first. Analytics import where the platform allows it.
- Done when: the plan shows what was posted, when, and the link.

**Phase 6: Originals pipeline**
- Voice and motion graphics as a separate render step. Compare with the current originals before switching.
- Done when: the new output matches the approved reference style on a review sheet.

**Phase 7: Company readiness**
- Roles for several people, hosting (after the owner approves any cost), backups, monitoring,
  privacy policy, terms, and a legal review.

## Compliance and risk (not legal advice)

- Platform terms and campaign rules decide what can be downloaded, clipped and reposted.
  Check each source before it is added to the registry.
- Music and game assets may carry rights. Keep a rights note on every clip.
- If the system stores personal data about people, plan for Nigeria's Data Protection Act 2023
  and any other law that applies. Get legal advice before selling or hosting it for others.
- Running several accounts on one platform can break that platform's rules. Check them.
- Paid services only with the owner's approval.

## Operating rules

- Each change has tests, and docs are updated in the same change.
- Before deleting or overwriting user data: a backup, and the owner's approval.
- The running system stays up until its replacement has passed the parity checklist.

## Repository layout

```
app/            web app and API (depends on core/)
core/           database, models, migrations, job queue and worker (no imports from app/)
scripts/        start script and maintenance scripts (scripts/start.py is used by start.bat)
tests/          automated tests
docs/           architecture, decisions (ADRs), runbook
.github/        CI and dependency updates
```

Planned additions: `ingest/`, `render/`, `ops/` (Phases 2 to 6).
