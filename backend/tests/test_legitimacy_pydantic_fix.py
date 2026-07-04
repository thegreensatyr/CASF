"""Iteration 8 — dynamic backend tests for the POST /api/legitimacy/research pydantic fix.

Bug: LegitimacyOut required `user_id` but the endpoint stripped it before returning,
causing pydantic ValidationError -> HTTP 500 -> frontend toast "Lookup failed".

Fix: `user_id` removed from LegitimacyOut model (server.py line 267-277).

Covers:
- Admin trust-check returns 200 with valid schema + NO user_id in response
- Non-admin verified user trust-check returns 200 + quota increments
- Unverified user returns 403 (email verification gate)
- Cache hit path (repeat call within 24h serves fast + `served_from_cache`)
- GET /legitimacy/history returns list w/o pydantic validation error
- Privacy: user_id NOT leaked in response but IS stored in DB
"""
import os
import time
import uuid
import requests
import pytest
from pymongo import MongoClient

BASE_URL = os.environ.get(
    "REACT_APP_BACKEND_URL",
    open("/app/frontend/.env").read().split("REACT_APP_BACKEND_URL=")[1].split("\n")[0].strip(),
).rstrip("/")

ADMIN_EMAIL = "casforensics@gmail.com"
ADMIN_PASSWORD = "CasForensics2026!"
LEGACY_EMAIL = "test@cs.io"
LEGACY_PASSWORD = "pass123"

# Expected response schema keys after the fix (user_id MUST NOT appear)
EXPECTED_KEYS = {"id", "casino_name", "casino_url", "trust_score",
                 "verdict", "report", "red_flags", "green_flags", "slug", "created_at"}
FORBIDDEN_KEYS = {"user_id", "is_cache_seed", "casino_name_lower"}


def _mongo():
    client = MongoClient(os.environ.get("MONGO_URL", "mongodb://localhost:27017"))
    return client[os.environ.get("DB_NAME", "test_database")]


@pytest.fixture(scope="module")
def admin_token():
    r = requests.post(f"{BASE_URL}/api/auth/login",
                      json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}, timeout=30)
    assert r.status_code == 200, f"admin login failed: {r.status_code} {r.text}"
    return r.json()["token"]


@pytest.fixture(scope="module")
def legacy_token():
    r = requests.post(f"{BASE_URL}/api/auth/login",
                      json={"email": LEGACY_EMAIL, "password": LEGACY_PASSWORD}, timeout=30)
    assert r.status_code == 200, f"legacy login failed: {r.status_code} {r.text}"
    return r.json()["token"]


@pytest.fixture(scope="module")
def unverified_user():
    """Fresh signup — email_verified=false, not admin."""
    db = _mongo()
    db.signup_attempts.delete_many({})  # bypass 5/hour rate limit
    email = f"TEST_iter8_{uuid.uuid4().hex[:8]}@cs.io"
    r = requests.post(f"{BASE_URL}/api/auth/signup",
                      json={"email": email, "password": "Pass1234!", "name": "Iter8"},
                      timeout=30)
    assert r.status_code == 200, f"signup failed: {r.status_code} {r.text}"
    body = r.json()
    assert body["user"]["email_verified"] is False
    return {"email": email, "token": body["token"], "id": body["user"]["id"]}


def _validate_schema(body: dict, expect_casino_name: str, expect_url: str | None = None):
    """Assert response body matches LegitimacyOut schema post-fix."""
    # No forbidden keys
    for k in FORBIDDEN_KEYS:
        assert k not in body, f"forbidden key '{k}' leaked in response: {body}"
    # All expected keys present
    missing = EXPECTED_KEYS - set(body.keys())
    assert not missing, f"missing expected keys: {missing}, body keys: {list(body.keys())}"
    # Field types / values
    assert body["casino_name"] == expect_casino_name
    if expect_url is not None:
        assert body["casino_url"] == expect_url
    assert isinstance(body["trust_score"], int)
    assert 0 <= body["trust_score"] <= 100
    assert isinstance(body["verdict"], str) and body["verdict"]
    assert isinstance(body["report"], str) and len(body["report"]) > 20
    assert isinstance(body["red_flags"], list)
    assert isinstance(body["green_flags"], list)
    assert isinstance(body["slug"], str) and body["slug"]
    assert isinstance(body["id"], str) and len(body["id"]) > 0
    assert isinstance(body["created_at"], str) and len(body["created_at"]) > 0


# ---------- CORE FIX TESTS ----------

def test_admin_research_returns_200_and_valid_schema(admin_token):
    """Bug repro: prior to fix, this returned 500 due to pydantic ValidationError."""
    r = requests.post(
        f"{BASE_URL}/api/legitimacy/research",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"casino_name": "fortunewheelz", "casino_url": "https://www.fortunewheelz.com/"},
        timeout=90,  # Claude Sonnet 4.5 call may take a while on first uncached run
    )
    assert r.status_code == 200, f"expected 200 (post-fix), got {r.status_code}: {r.text[:400]}"
    body = r.json()
    _validate_schema(body, expect_casino_name="fortunewheelz",
                     expect_url="https://www.fortunewheelz.com/")


def test_admin_response_does_not_leak_user_id_but_db_stores_it(admin_token):
    """Privacy: response has no user_id even though DB record still has one."""
    unique_name = f"TESTCASINO_privacy_{uuid.uuid4().hex[:6]}"
    r = requests.post(
        f"{BASE_URL}/api/legitimacy/research",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"casino_name": unique_name},
        timeout=90,
    )
    assert r.status_code == 200, f"got {r.status_code}: {r.text[:400]}"
    body = r.json()
    assert "user_id" not in body
    # Verify DB record still stores user_id (needed for /history)
    db = _mongo()
    doc = db.legitimacy_reports.find_one({"id": body["id"]})
    assert doc is not None, "record not persisted"
    assert "user_id" in doc, "DB doc must retain user_id for /history"
    assert doc["user_id"]  # non-empty


def test_cache_hit_returns_fast_and_marks_served_from_cache(admin_token):
    """Repeat call within 24h on the same casino_name_lower should hit cache."""
    unique_name = f"TESTCASINO_cache_{uuid.uuid4().hex[:6]}"
    # First call — populates cache (is_cache_seed=True)
    r1 = requests.post(
        f"{BASE_URL}/api/legitimacy/research",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"casino_name": unique_name},
        timeout=90,
    )
    assert r1.status_code == 200, f"first call failed: {r1.status_code} {r1.text[:300]}"
    body1 = r1.json()

    # Second call — must hit cache (should be fast, <5s realistically)
    start = time.time()
    r2 = requests.post(
        f"{BASE_URL}/api/legitimacy/research",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"casino_name": unique_name},
        timeout=30,
    )
    elapsed = time.time() - start
    assert r2.status_code == 200, f"second call failed: {r2.status_code} {r2.text[:300]}"
    body2 = r2.json()
    # Different id (cloned) but same underlying content
    assert body2["id"] != body1["id"], "cache clone should have a new id"
    # Same trust_score + verdict + report indicates a cache hit
    assert body2["trust_score"] == body1["trust_score"]
    assert body2["verdict"] == body1["verdict"]
    assert body2["report"] == body1["report"]
    # Cache hit should be very fast (LLM calls typically 5-30s)
    assert elapsed < 10.0, f"cache hit too slow: {elapsed:.2f}s (suggests LLM was called again)"

    # Confirm the cloned DB row has served_from_cache=True
    db = _mongo()
    clone_doc = db.legitimacy_reports.find_one({"id": body2["id"]})
    assert clone_doc is not None
    assert clone_doc.get("served_from_cache") is True


def test_unverified_user_gets_403_email_verification_gate(unverified_user):
    """Email-verification gate: unverified user should get 403 BEFORE LLM call."""
    r = requests.post(
        f"{BASE_URL}/api/legitimacy/research",
        headers={"Authorization": f"Bearer {unverified_user['token']}"},
        json={"casino_name": "Bovada"},
        timeout=30,
    )
    assert r.status_code == 403, f"expected 403 (unverified), got {r.status_code}: {r.text[:300]}"
    detail = r.json().get("detail", "")
    assert "verify your email" in detail.lower(), f"unexpected detail: {detail}"


def test_verified_nonadmin_research_and_quota_increments(legacy_token):
    """Fresh verified non-admin should get 200 + quota counter increments.

    Note: legacy test@cs.io may already have exhausted free quota from prior runs
    (FREE_TRUST_CHECKS_LIMIT=1). We reset the counter in DB first to isolate this test.
    """
    db = _mongo()
    # Reset the counter so we can observe an increment cleanly
    db.users.update_one({"email": LEGACY_EMAIL}, {"$set": {"free_trust_checks_used": 0}})
    before = db.users.find_one({"email": LEGACY_EMAIL}).get("free_trust_checks_used", 0)
    assert before == 0

    r = requests.post(
        f"{BASE_URL}/api/legitimacy/research",
        headers={"Authorization": f"Bearer {legacy_token}"},
        json={"casino_name": "Bovada"},
        timeout=90,
    )
    assert r.status_code == 200, f"legacy user research failed: {r.status_code} {r.text[:400]}"
    body = r.json()
    _validate_schema(body, expect_casino_name="Bovada")

    after = db.users.find_one({"email": LEGACY_EMAIL}).get("free_trust_checks_used", 0)
    assert after == before + 1, f"quota should increment from {before} to {before+1}, got {after}"


def test_legitimacy_history_returns_list_without_validation_error(admin_token):
    """GET /legitimacy/history must not raise pydantic validation error even though
    DB docs still contain user_id (pydantic v2 ignores extras by default)."""
    r = requests.get(
        f"{BASE_URL}/api/legitimacy/history",
        headers={"Authorization": f"Bearer {admin_token}"},
        timeout=30,
    )
    assert r.status_code == 200, f"history failed: {r.status_code} {r.text[:400]}"
    data = r.json()
    assert isinstance(data, list)
    # After admin ran multiple checks above, we should have at least 1 record
    assert len(data) >= 1, "expected admin to have >=1 history record from earlier tests"
    for item in data:
        # Same schema guarantee as POST response
        for k in FORBIDDEN_KEYS:
            assert k not in item, f"forbidden key '{k}' in /history item: {item}"
        missing = EXPECTED_KEYS - set(item.keys())
        assert not missing, f"/history item missing keys: {missing}"
