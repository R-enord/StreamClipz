# StreamClipz

A login-protected web app that runs on your own computer and opens on your phone.
Local use first, structured so it can grow into a hosted product later.

## Start it (Windows laptop)

1. Double-click **`start.bat`**. The first run sets everything up. It takes about a minute.
2. If it says there is no login account yet, open a terminal in this folder and run
   `.venv\Scripts\python.exe -m app.cli create-user yourname --admin`
   You type your password at the hidden prompt yourself. It is stored only as a scrypt hash.
3. Run `start.bat` again. It prints the link to open on your phone, for example
   `http://192.168.1.23:8000`. Your phone must be on the same Wi-Fi.
4. If Windows asks about the firewall, allow access on **Private networks**.
   Keep the window open while you use the app.

**Away from home:** install the free Tailscale app on the laptop and the phone and sign in
to both yourself. Then `start.bat` also prints a Tailscale link that works anywhere.

The laptop must be on and the window must stay open. If it sleeps, shuts down or loses power,
the link stops working until you start it again.

## Start it (other systems)

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/python -m app.cli create-user yourname --admin
.venv/bin/python scripts/start.py
```

## What's here

| Path | Purpose |
| --- | --- |
| `start.bat` | Windows double-click launcher (first-run setup, then starts the app) |
| `scripts/start.py` | Starts the server and prints the phone link |
| `app/main.py` | App factory (`create_app`), wiring of routers and static files |
| `app/config.py` | Settings from environment variables (see `.env.example`) |
| `app/db.py` | SQLite schema and connection handling (`data/streamclipz.db`) |
| `app/security.py` | scrypt password hashing, hashed session tokens |
| `app/auth.py` | Login, sessions, lockout after repeated failures |
| `app/routes/` | `auth_routes` (login/logout), `pages` (dashboard), `api` (JSON) |
| `app/templates/`, `app/static/` | Phone-friendly pages and styles |
| `app/cli.py` | Create accounts on the server: `python -m app.cli create-user` |
| `tests/` | Pytest suite for login, lockout, sessions and API access |

Run the tests with `.venv/bin/python -m pytest` (or `.venv\Scripts\python.exe -m pytest`).

## SnipRiot integration (pending)

The SnipRiot worker writes its state to `data/snipriot/status.json`. The
`/api/status` endpoint reads that file read-only, and the dashboard shows it. The
SnipRiot worker code itself is not in this repository yet, so the clip pipeline, job inbox and
dashboard tabs still need to be brought in.

## Security notes

- Passwords: scrypt. Sessions: random 256-bit tokens; only their SHA-256 is stored.
- Cookies are `HttpOnly` and `SameSite=Lax`. Logout deletes the server-side session.
- Failed logins are counted per username; 5 failures lock that name for 15 minutes.
- The app is for your own devices on a private network. It is not ready for the public
  internet without HTTPS and a review. Set `STREAMCLIPZ_COOKIE_SECURE=1` only behind HTTPS.
