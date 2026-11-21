from app.config import Settings
from tests.conftest import PASSWORD


def login(client, username="owner", password=PASSWORD):
    return client.post("/login", data={"username": username, "password": password}, follow_redirects=False)


def test_dashboard_redirects_to_login_when_signed_out(client):
    r = client.get("/", follow_redirects=False)
    assert r.status_code == 303 and r.headers["location"] == "/login"


def test_api_requires_sign_in(client):
    assert client.get("/api/me").status_code == 401
    assert client.get("/api/status").status_code == 401


def test_health_is_public(client):
    assert client.get("/api/health").json() == {"status": "ok"}


def test_good_login_sets_cookie_and_opens_dashboard(client):
    r = login(client)
    assert r.status_code == 303 and r.headers["location"] == "/"
    assert "sc_session" in r.cookies
    me = client.get("/api/me").json()
    assert me == {"username": "owner", "is_admin": True}


def test_wrong_password_is_rejected(client):
    r = login(client, password="wrong-password-here")
    assert r.status_code == 401
    assert "Wrong username or password" in r.text
    assert client.get("/api/me").status_code == 401


def test_unknown_user_gets_same_message(client):
    r = login(client, username="nobody", password="whatever-password")
    assert r.status_code == 401 and "Wrong username or password" in r.text


def test_lockout_after_repeated_failures(client, settings):
    for _ in range(settings.max_login_failures):
        login(client, password="wrong-password-here")
    r = login(client)  # correct password, but locked
    assert r.status_code == 401
    assert "Too many failed attempts" in r.text


def test_logout_invalidates_session(client):
    login(client)
    assert client.get("/api/me").status_code == 200
    client.post("/logout", follow_redirects=False)
    client.cookies.clear()
    assert client.get("/api/me").status_code == 401


def test_status_reports_missing_snipriot_data_gracefully(client):
    login(client)
    body = client.get("/api/status").json()
    assert body["available"] is False


def test_status_reads_snipriot_file_when_present(client, settings):
    login(client)
    path = settings.status_file
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text('{"recording": true}', encoding="utf-8")
    body = client.get("/api/status").json()
    assert body == {"available": True, "status": {"recording": True}}
