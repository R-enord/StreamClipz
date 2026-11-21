# StreamClipz

A small, login-protected web app for running StreamClipz / SnipRiot on your own
machine and opening it from your phone. Local use first; structured so it can
grow into a hosted product later.

## What's here

| Path | Purpose |
| --- | --- |
| `app/main.py` | App factory (`create_app`), wiring of routers and static files |
| `app/config.py` | Settings from environment variables (see `.env.example`) |
| `app/db.py` | SQLite schema and connection handling (`data/streamclipz.db`) |
| `app/security.py` | scrypt password hashing, hashed session tokens |
| `app/auth.py` | Login, sessions, lockout after repeated failures |
| `app/routes/` | `auth_routes` (login/logout), `pages` (dashboard), `api` (JSON) |
| `app/templates/`, `app/static/` | Phone-friendly pages and styles |
| `app/cli.py` | Create accounts on the server: `python -m app.cli create-user` |
| `tests/` | Pytest suite for login, lockout, sessions and API access |

## Setup (once)

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
cp .env.example .env            # optional: change the data folder
.venv/bin/python -m app.cli create-user yourname --admin
```

You type the password yourself at the hidden prompt. It is stored only as a scrypt hash.
Passwords must be at least 10 characters.

## Run

```bash
.venv/bin/uvicorn app.main:create_app --factory --host 0.0.0.0 --port 8000
```

Open `http://<this-computer's-LAN-IP>:8000` on a phone on the same Wi-Fi and sign in.
The health check is at `/api/health`. Run the tests with `.venv/bin/python -m pytest`.

### Reaching it from your phone away from home

Use a private tunnel rather than opening your router's ports. Tailscale has a free
personal plan and is the simplest choice. Install it on the computer and the phone,
then use the Tailscale address on port 8000. Once you're on HTTPS, set
`STREAMCLIPZ_COOKIE_SECURE=1`. Firewall and sign-in changes are yours to make.

## SnipRiot integration (pending)

The SnipRiot worker writes its state to `data/snipriot/status.json`. The
`/api/status` endpoint reads that file read-only. The worker code itself is not in
this repository yet, so the SnipRiot pieces (clip pipeline, job inbox, dashboard
tabs) still need to be brought in. See the handover notes in the project chat.

## Security notes

- Passwords: scrypt. Sessions: random 256-bit tokens; only their SHA-256 is stored.
- Cookies are `HttpOnly` and `SameSite=Lax`. Logout deletes the server-side session.
- Failed logins are counted per username; 5 failures lock that name for 15 minutes.
- Nothing here is meant for the public internet without HTTPS and a review.
