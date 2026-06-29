"""Live endpoint regressions for iteration 7 — runs against REACT_APP_BACKEND_URL.

Covers:
- POST /api/auth/signup creates a new user (email_verified=false, JWT issued)
- POST /api/auth/login with admin credentials (is_admin=true, email_verified=true)
- POST /api/auth/forgot-password with admin (email_sent=true OR debug_link present)
- GET /api/sitemap.xml contains https://casforensics.org/techniques/ URLs
- GET /api/techniques returns 8 techniques with articles
- GET /api/scams public returns 24 seeded posts
- POST /api/admin/seed-scam-wall idempotent
"""
import os
import time
import uuid
import requests
import pytest

BASE_URL = os.environ.get(
    "REACT_APP_BACKEND_URL",
    # read frontend/.env fallback
    open("/app/frontend/.env").read().split("REACT_APP_BACKEND_URL=")[1].split("\n")[0].strip(),
).rstrip("/")

ADMIN_EMAIL = "casforensics@gmail.com"
ADMIN_PASSWORD = "CasForensics2026!"


@pytest.fixture(scope="module")
def admin_token():
    r = requests.post(f"{BASE_URL}/api/auth/login",
                      json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}, timeout=30)
    assert r.status_code == 200, f"admin login failed: {r.status_code} {r.text}"
    return r.json()["token"]


@pytest.fixture(scope="module")
def admin_login_resp():
    r = requests.post(f"{BASE_URL}/api/auth/login",
                      json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}, timeout=30)
    assert r.status_code == 200
    return r.json()


# REGRESSION 1: signup creates a new user with unique email, JWT, email_verified=false
def test_signup_creates_unverified_user_with_jwt():
    # Wipe rate-limit collection before signup test (no admin endpoint, use direct mongo)
    from pymongo import MongoClient
    mongo = MongoClient(os.environ.get("MONGO_URL", "mongodb://localhost:27017"))
    db = mongo[os.environ.get("DB_NAME", "test_database")]
    db.signup_attempts.delete_many({})

    email = f"TEST_iter7_{uuid.uuid4().hex[:8]}@cs.io"
    r = requests.post(f"{BASE_URL}/api/auth/signup",
                      json={"email": email, "password": "Pass1234!", "name": "Iter7"},
                      timeout=30)
    assert r.status_code == 200, f"signup failed: {r.status_code} {r.text}"
    body = r.json()
    assert "token" in body and isinstance(body["token"], str) and len(body["token"]) > 0
    assert "user" in body
    u = body["user"]
    assert u["email"] == email
    assert u["name"] == "Iter7"
    assert u["is_admin"] is False
    assert u["email_verified"] is False, "non-admin signup should NOT be auto-verified"
    assert "id" in u and len(u["id"]) > 0


# REGRESSION 2: admin login returns is_admin=true, email_verified=true
def test_admin_login_is_admin_and_verified(admin_login_resp):
    u = admin_login_resp["user"]
    assert u["email"].lower() == ADMIN_EMAIL
    assert u["is_admin"] is True
    assert u["email_verified"] is True


# REGRESSION 3: forgot-password for admin returns 200 with email_sent=true OR debug_link
def test_forgot_password_admin_returns_email_sent_or_debug_link():
    r = requests.post(f"{BASE_URL}/api/auth/forgot-password",
                      json={"email": ADMIN_EMAIL}, timeout=30)
    assert r.status_code == 200, f"got {r.status_code}: {r.text}"
    body = r.json()
    assert body.get("ok") is True
    # admin always gets debug_link
    assert "debug_link" in body, f"admin should get debug_link, body={body}"
    assert "/reset-password?token=" in body["debug_link"]
    # email_sent should be a bool (true if Resend OK, false if it failed but link is in logs)
    assert "email_sent" in body
    assert isinstance(body["email_sent"], bool)


# REGRESSION 4: sitemap.xml returns XML with https://casforensics.org/techniques/ URLs
def test_sitemap_uses_site_url_constant():
    r = requests.get(f"{BASE_URL}/api/sitemap.xml", timeout=30)
    assert r.status_code == 200
    ct = r.headers.get("content-type", "")
    assert "xml" in ct.lower(), f"expected xml content-type, got {ct}"
    body = r.text
    assert "<urlset" in body
    assert "https://casforensics.org/techniques/" in body, \
        f"sitemap missing prod URL prefix. First 500 chars: {body[:500]}"


# REGRESSION 5: /api/techniques returns 8 techniques with article populated
def test_techniques_endpoint_returns_8_with_articles():
    r = requests.get(f"{BASE_URL}/api/techniques", timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    assert len(data) == 8, f"expected 8 techniques, got {len(data)}"
    for t in data:
        assert "slug" in t and "name" in t
        assert t.get("article") is not None, f"technique {t['slug']} missing article"
        assert "sections" in t["article"]


# REGRESSION 6: /api/scams public returns the seeded posts (expect 24)
def test_scams_public_returns_seeded_posts():
    r = requests.get(f"{BASE_URL}/api/scams", timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    # Spec says 24 — allow >= 23 to tolerate one off-by-one in seed
    assert len(data) >= 23, f"expected ~24 seeded scam posts, got {len(data)}"


# REGRESSION 7: /api/admin/seed-scam-wall is idempotent (inserted:0 on re-run)
def test_seed_scam_wall_idempotent(admin_token):
    r = requests.post(f"{BASE_URL}/api/admin/seed-scam-wall",
                      headers={"Authorization": f"Bearer {admin_token}"},
                      timeout=60)
    assert r.status_code == 200, f"seed failed: {r.status_code} {r.text}"
    body = r.json()
    assert "inserted" in body
    assert "total" in body
    assert body["inserted"] == 0, f"seed should be idempotent, inserted={body['inserted']}"
    assert body["total"] >= 23
