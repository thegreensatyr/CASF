"""
Backend tests for email-verification gating (Casino Spotter, Jan 2026).

Covers:
  - Signup creates non-admin user with email_verified=false
  - Admin signup auto-verified
  - Legacy users (grandfathered) email_verified=true
  - LLM-gated endpoints return 403 for unverified users
  - /api/auth/verify-email: valid token, idempotency, invalid token
  - /api/auth/resend-verification: rate limited, already-verified shortcut
  - Backend log fallback writes [EMAIL-VERIFY] link
"""
import os
import re
import time
import uuid
import subprocess
import pytest
import requests

def _load_backend_url():
    url = os.environ.get("REACT_APP_BACKEND_URL", "").strip()
    if not url:
        try:
            with open("/app/frontend/.env", "r") as fh:
                for line in fh:
                    if line.startswith("REACT_APP_BACKEND_URL="):
                        url = line.split("=", 1)[1].strip().strip('"').strip("'")
                        break
        except Exception:
            pass
    return url.rstrip("/")


BASE_URL = _load_backend_url()
assert BASE_URL, "REACT_APP_BACKEND_URL must be set"
API = f"{BASE_URL}/api"

ADMIN_EMAIL = "casforensics@gmail.com"
ADMIN_PASS = "CasForensics2026!"
LEGACY_EMAIL = "test@cs.io"
LEGACY_PASS = "pass123"

LOG_FILES = [
    "/var/log/supervisor/backend.err.log",
    "/var/log/supervisor/backend.out.log",
]


# ---------------- helpers ----------------
def _post(path, json=None, headers=None):
    return requests.post(f"{API}{path}", json=json or {}, headers=headers or {}, timeout=30)


def _get(path, headers=None):
    return requests.get(f"{API}{path}", headers=headers or {}, timeout=30)


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


def _fresh_email():
    return f"TEST_verify_{uuid.uuid4().hex[:8]}@cs.io"


def _clear_signup_rate_limit():
    """Wipe signup_attempts in mongo so the IP-based 5/hour limit doesn't block tests."""
    try:
        from pymongo import MongoClient
        mongo_url = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
        db_name = os.environ.get("DB_NAME", "test_database")
        # Load from backend/.env if env not set in this process
        if "test_database" not in db_name and not os.environ.get("DB_NAME"):
            with open("/app/backend/.env") as fh:
                for line in fh:
                    if line.startswith("MONGO_URL="):
                        mongo_url = line.split("=", 1)[1].strip().strip('"')
                    if line.startswith("DB_NAME="):
                        db_name = line.split("=", 1)[1].strip().strip('"')
        client = MongoClient(mongo_url, serverSelectionTimeoutMS=2000)
        client[db_name].signup_attempts.delete_many({})
        client.close()
    except Exception as e:
        print(f"[warn] could not clear signup_attempts: {e}")


@pytest.fixture(scope="session", autouse=True)
def _reset_signup_rate_limit_session():
    _clear_signup_rate_limit()
    yield


@pytest.fixture(autouse=True)
def _reset_signup_rate_limit_per_test():
    # Clear before each test — 7+ signups happen across the suite, all from the same IP.
    _clear_signup_rate_limit()
    yield


def _read_verify_link(email):
    """Grep supervisor logs for the [EMAIL-VERIFY] line for this email."""
    # Wait a moment for the fire-and-forget task to write the log.
    pattern = re.compile(rf"\[EMAIL-VERIFY\] user={re.escape(email)} link=(\S+)")
    for _ in range(20):
        for path in LOG_FILES:
            try:
                # tail last ~500 lines to keep it fast
                out = subprocess.check_output(
                    ["tail", "-n", "1500", path], stderr=subprocess.DEVNULL
                ).decode("utf-8", errors="ignore")
            except Exception:
                continue
            matches = pattern.findall(out)
            if matches:
                return matches[-1]
        time.sleep(0.3)
    return None


def _signup(email=None, password="TestPass#1", name="Test User"):
    email = email or _fresh_email()
    r = _post("/auth/signup", {"email": email, "password": password, "name": name})
    return r, email, password


def _login(email, password):
    return _post("/auth/login", {"email": email, "password": password})


# ---------------- signup behaviour ----------------
class TestSignupEmailVerifiedFlag:
    def test_new_user_signup_unverified(self):
        r, email, _ = _signup()
        assert r.status_code == 200, r.text
        data = r.json()
        assert "token" in data and "user" in data
        assert data["user"]["email"] == email
        assert data["user"]["email_verified"] is False, "Fresh user must be unverified"
        assert data["user"]["is_admin"] is False

    def test_admin_signup_auto_verified(self):
        # Admin account already exists; just log in and confirm email_verified=True.
        r = _login(ADMIN_EMAIL, ADMIN_PASS)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["user"]["is_admin"] is True
        assert data["user"]["email_verified"] is True

    def test_legacy_user_grandfathered(self):
        r = _login(LEGACY_EMAIL, LEGACY_PASS)
        assert r.status_code == 200, r.text
        assert r.json()["user"]["email_verified"] is True, "Legacy users must be grandfathered"


# ---------------- LLM gating ----------------
class TestLLMGatesUnverified:
    @pytest.fixture(scope="class")
    def unverified_token(self):
        r, email, _ = _signup()
        assert r.status_code == 200, r.text
        return r.json()["token"], email

    def test_legitimacy_research_blocked(self, unverified_token):
        token, _ = unverified_token
        r = _post("/legitimacy/research", {"casino_name": "TestCasino", "casino_url": "https://example.com"}, _auth(token))
        assert r.status_code == 403, f"Expected 403 got {r.status_code}: {r.text}"
        assert "verify" in r.json().get("detail", "").lower()

    def test_live_session_start_blocked(self, unverified_token):
        token, _ = unverified_token
        r = _post("/live/session/start", {}, _auth(token))
        assert r.status_code == 403, f"Expected 403 got {r.status_code}: {r.text}"
        assert "verify" in r.json().get("detail", "").lower()

    def test_admin_bypasses_gate(self):
        # Admin can hit /legitimacy/research without verification gate (will return 200 or some non-403)
        login = _login(ADMIN_EMAIL, ADMIN_PASS)
        assert login.status_code == 200
        token = login.json()["token"]
        r = _post(
            "/legitimacy/research",
            {"casino_name": "AdminGateProbe", "casino_url": "https://stake.com"},
            _auth(token),
        )
        # We don't actually want to wait for LLM; just confirm we don't get the 403 verification error.
        assert r.status_code != 403, f"Admin must not be gated. Got {r.status_code}: {r.text[:200]}"


# ---------------- verify-email endpoint ----------------
class TestVerifyEmailEndpoint:
    def test_invalid_token_400(self):
        r = _post("/auth/verify-email", {"token": "definitely-not-a-real-token-xxx"})
        assert r.status_code == 400, r.text

    def test_valid_token_marks_verified(self):
        r, email, _ = _signup()
        assert r.status_code == 200
        token_jwt = r.json()["token"]
        link = _read_verify_link(email)
        assert link, f"No [EMAIL-VERIFY] log line found for {email}"
        m = re.search(r"token=([A-Za-z0-9_\-]+)", link)
        assert m, f"Cannot parse token from link: {link}"
        verify_tok = m.group(1)

        # First call: marks user as verified
        r1 = _post("/auth/verify-email", {"token": verify_tok})
        assert r1.status_code == 200, r1.text
        body = r1.json()
        assert body["user"]["email"].lower() == email.lower()
        assert body["user"]["email_verified"] is True
        assert isinstance(body.get("token"), str) and len(body["token"]) > 10, "Fresh JWT must be returned"

        # Idempotent: same token twice → 200 (handles React StrictMode + email prefetchers)
        r2 = _post("/auth/verify-email", {"token": verify_tok})
        assert r2.status_code == 200, f"Idempotent re-verify must return 200, got {r2.status_code}: {r2.text}"
        assert r2.json()["user"]["email_verified"] is True

        # And the gate should now be lifted: /legitimacy/research no longer returns 403
        gated = _post(
            "/legitimacy/research",
            {"casino_name": "PostVerifyProbe", "casino_url": "https://stake.com"},
            _auth(token_jwt),
        )
        assert gated.status_code != 403, f"After verification, user must not be gated. Got {gated.status_code}: {gated.text[:200]}"


# ---------------- resend-verification ----------------
class TestResendVerification:
    def test_resend_rate_limited_immediately_after_signup(self):
        # Signup auto-issues one token; immediate resend should 429.
        r, email, _ = _signup()
        jwt = r.json()["token"]
        rr = _post("/auth/resend-verification", {"origin_url": BASE_URL}, _auth(jwt))
        assert rr.status_code == 429, f"Expected 429 immediately post-signup, got {rr.status_code}: {rr.text}"

    def test_resend_already_verified_shortcut(self):
        # Admin (verified) hitting resend returns {already_verified: true}
        login = _login(ADMIN_EMAIL, ADMIN_PASS)
        jwt = login.json()["token"]
        rr = _post("/auth/resend-verification", {"origin_url": BASE_URL}, _auth(jwt))
        assert rr.status_code == 200, rr.text
        body = rr.json()
        assert body.get("already_verified") is True

    def test_resend_requires_auth(self):
        rr = _post("/auth/resend-verification", {"origin_url": BASE_URL})
        assert rr.status_code in (401, 403), f"Expected 401/403 unauthenticated, got {rr.status_code}"


# ---------------- log fallback ----------------
class TestEmailVerifyLogFallback:
    def test_log_contains_verify_link_for_new_signup(self):
        r, email, _ = _signup()
        assert r.status_code == 200
        link = _read_verify_link(email)
        assert link is not None, "Backend log must contain [EMAIL-VERIFY] line"
        assert "/verify-email?token=" in link
        # Token is 32-char url-safe (secrets.token_urlsafe(32) → ~43 chars)
        m = re.search(r"token=([A-Za-z0-9_\-]+)", link)
        assert m and len(m.group(1)) >= 32


# ---------------- existing flows continue to work ----------------
class TestRegressionAuth:
    def test_admin_login_still_works(self):
        r = _login(ADMIN_EMAIL, ADMIN_PASS)
        assert r.status_code == 200, r.text
        assert r.json()["user"]["is_admin"] is True

    def test_legacy_user_login_still_works(self):
        r = _login(LEGACY_EMAIL, LEGACY_PASS)
        assert r.status_code == 200, r.text

    def test_legacy_user_can_use_llm_endpoints(self):
        login = _login(LEGACY_EMAIL, LEGACY_PASS)
        token = login.json()["token"]
        r = _post(
            "/legitimacy/research",
            {"casino_name": "LegacyProbe", "casino_url": "https://stake.com"},
            _auth(token),
        )
        # Must not be email-verification gated (403). Could be 402 (free quota) or 200.
        assert r.status_code != 403, f"Legacy user must not be email-gated. Got {r.status_code}: {r.text[:200]}"
