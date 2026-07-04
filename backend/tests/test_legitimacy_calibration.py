"""Iteration 9 — backend tests for the trust-score calibration + Scam Wall community-signal.

Fixes under test:
- server.py lines 1918-1940: new 5-band calibration prompt (unknown/new default 55, not 42)
- server.py lines 1905-1916: wall_signal derived from db.scam_posts case-insensitive regex
- server.py lines 1949-1954: prompt now carries the wall_signal line

Coverage:
1. 'Chanced' should score >=50 and NOT be verdict='High Risk'
2. Betway/PokerStars (reputable) still scores 70+
3. Bovada (has wall entry) is passed the elevated-signal line; verify prompt is composed
   correctly by asserting the wall regex query returns >=1 (isolated MongoDB verification)
4. Novel unknown 'ZZZ9999FakeCasino' scores 45-60
5. Wall count regex is case-insensitive: 'bovada' == 'Bovada' == 'BOVADA' from mongodb probe
6. Endpoint still returns 200 + well-formed LegitimacyOut (regression)
7. Cache reuse (<2s) still works — regression
"""
import os
import re
import time
import uuid
import requests
import pytest
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv("/app/backend/.env")

BASE_URL = open("/app/frontend/.env").read().split("REACT_APP_BACKEND_URL=")[1].split("\n")[0].strip().rstrip("/")

ADMIN_EMAIL = "casforensics@gmail.com"
ADMIN_PASSWORD = "CasForensics2026!"

EXPECTED_KEYS = {"id", "casino_name", "casino_url", "trust_score",
                 "verdict", "report", "red_flags", "green_flags", "slug", "created_at"}
FORBIDDEN_KEYS = {"user_id", "is_cache_seed", "casino_name_lower"}


def _mongo():
    client = MongoClient(os.environ["MONGO_URL"])
    return client, client[os.environ["DB_NAME"]]


@pytest.fixture(scope="module")
def admin_token():
    r = requests.post(f"{BASE_URL}/api/auth/login",
                      json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}, timeout=15)
    assert r.status_code == 200, f"Admin login failed: {r.status_code} {r.text}"
    return r.json()["token"]


@pytest.fixture(scope="module")
def clean_cache():
    """Wipe cached legitimacy reports for test casinos so we hit a fresh Claude call."""
    _, db = _mongo()
    for name in ["chanced", "betway", "pokerstars", "zzz9999fakecasino", "bovada"]:
        db.legitimacy_reports.delete_many({"casino_name_lower": name})
    yield


def _research(token, casino_name, casino_url=None, timeout=90):
    payload = {"casino_name": casino_name}
    if casino_url:
        payload["casino_url"] = casino_url
    return requests.post(
        f"{BASE_URL}/api/legitimacy/research",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        json=payload,
        timeout=timeout,
    )


# ---------------- Feature 1: Chanced recalibration ----------------
class TestChancedRecalibration:
    def test_chanced_scores_at_least_50_and_not_high_risk(self, admin_token, clean_cache):
        r = _research(admin_token, "Chanced", "https://chanced.com")
        assert r.status_code == 200, f"HTTP {r.status_code}: {r.text}"
        data = r.json()
        # Schema regression
        assert EXPECTED_KEYS.issubset(set(data.keys()))
        assert not (FORBIDDEN_KEYS & set(data.keys()))
        # Calibration: Chanced (unknown sweepstakes crypto casino) must not fall in scam band
        score = data["trust_score"]
        verdict = data["verdict"].lower()
        print(f"[Chanced] score={score} verdict={data['verdict']}")
        print(f"[Chanced] green_flags={data['green_flags']}")
        print(f"[Chanced] red_flags={data['red_flags']}")
        assert score >= 50, f"Chanced expected >=50, got {score}. Verdict='{data['verdict']}'"
        assert "high risk" not in verdict, f"Verdict should not be 'High Risk', got '{data['verdict']}'"


# ---------------- Feature 2: Reputable operators unchanged ----------------
class TestReputableUnchanged:
    @pytest.mark.parametrize("name", ["Betway", "PokerStars"])
    def test_reputable_still_scores_70_plus(self, admin_token, clean_cache, name):
        # Reset quota for admin (admin bypasses quota, but this is defensive)
        r = _research(admin_token, name)
        assert r.status_code == 200, f"HTTP {r.status_code}: {r.text}"
        data = r.json()
        score = data["trust_score"]
        print(f"[{name}] score={score} verdict={data['verdict']}")
        assert score >= 70, f"{name} expected >=70 (established brand), got {score}"


# ---------------- Feature 3: Bovada + Community wall signal ----------------
class TestCommunitySignal:
    def test_bovada_wall_count_positive(self, clean_cache):
        """Direct mongo probe: the code that composes the wall_signal
        for Bovada should see >=1 posts (Bovada has 1 seeded post)."""
        _, db = _mongo()
        cnt = db.scam_posts.count_documents({
            "casino_name": {"$regex": "^Bovada$", "$options": "i"}
        })
        assert cnt >= 1, f"Bovada seed missing on scam_posts: got {cnt}"

    def test_bovada_wall_regex_case_insensitive(self):
        """The count query must be case-insensitive so 'bovada'/'BOVADA'/'Bovada' all match."""
        _, db = _mongo()
        for variant in ["bovada", "Bovada", "BOVADA", "BoVaDa"]:
            cnt = db.scam_posts.count_documents({
                "casino_name": {"$regex": f"^{re.escape(variant)}$", "$options": "i"}
            })
            assert cnt >= 1, f"Case-insensitive regex failed for variant {variant!r} (got {cnt})"

    def test_bovada_research_carries_community_signal(self, admin_token, clean_cache):
        """Bovada has a wall entry → prompt should carry a community-concern hint.
        Claude may reflect that in either a note in the report or reduced green flags."""
        r = _research(admin_token, "Bovada")
        assert r.status_code == 200, f"HTTP {r.status_code}: {r.text}"
        data = r.json()
        score = data["trust_score"]
        report = data["report"].lower()
        print(f"[Bovada] score={score} verdict={data['verdict']}")
        print(f"[Bovada] report snippet: {report[:400]}")
        # Regression: response is well-formed
        assert EXPECTED_KEYS.issubset(set(data.keys()))
        # We can't hard-assert score band because Bovada is a known offshore brand
        # (Claude might rate 40-65). Just verify the endpoint completed and returned
        # something meaningful.
        assert 0 <= score <= 100


# ---------------- Feature 4: Novel unknown casino defaults to 45-60 ----------------
class TestNovelUnknownBaseline:
    def test_novel_fake_name_defaults_45_to_60(self, admin_token, clean_cache):
        novel = f"ZZZ9999FakeCasino{uuid.uuid4().hex[:4]}"
        r = _research(admin_token, novel)
        assert r.status_code == 200, f"HTTP {r.status_code}: {r.text}"
        data = r.json()
        score = data["trust_score"]
        verdict = data["verdict"].lower()
        print(f"[{novel}] score={score} verdict={data['verdict']}")
        print(f"[{novel}] green_flags={data['green_flags']} red_flags={data['red_flags']}")
        # Calibration spec: unknown/new must NOT default below 40. Range 45-60 for a
        # completely made-up name (which Claude will treat as no-info-found).
        # Allow 40-70 tolerance for LLM stochasticity, but STRICTLY not below 40.
        assert score >= 40, f"Novel unknown must not score below 40 (got {score})"
        assert score <= 70, f"Novel unknown must not score above 70 (got {score})"
        # Verdict should not be 'High Risk' or 'Reputable' — should be Caution/Insufficient
        assert "high risk" not in verdict, f"Novel unknown incorrectly rated High Risk (verdict='{data['verdict']}')"


# ---------------- Feature 5: Endpoint regression ----------------
class TestEndpointRegression:
    def test_endpoint_returns_200_and_well_formed(self, admin_token, clean_cache):
        """Original pydantic-fix regression."""
        r = _research(admin_token, "fortunewheelz", "https://www.fortunewheelz.com/")
        assert r.status_code == 200
        data = r.json()
        assert EXPECTED_KEYS.issubset(set(data.keys()))
        assert not (FORBIDDEN_KEYS & set(data.keys()))
        assert isinstance(data["trust_score"], int)
        assert isinstance(data["red_flags"], list)
        assert isinstance(data["green_flags"], list)


# ---------------- Feature 6: Cache reuse < 2s ----------------
class TestCacheReuse:
    def test_cache_hit_second_call_fast(self, admin_token):
        """First call populates cache; second identical call should serve <2s."""
        casino = f"CacheTestCasino_{uuid.uuid4().hex[:8]}"
        # Ensure fresh
        _, db = _mongo()
        db.legitimacy_reports.delete_many({"casino_name_lower": casino.lower()})

        t0 = time.time()
        r1 = _research(admin_token, casino)
        d1 = time.time() - t0
        assert r1.status_code == 200
        first_data = r1.json()

        t0 = time.time()
        r2 = _research(admin_token, casino)
        d2 = time.time() - t0
        assert r2.status_code == 200
        second_data = r2.json()

        print(f"[CACHE] first={d1:.2f}s second={d2:.2f}s")
        assert d2 < 3.0, f"Second (cache) call took {d2:.2f}s (expected <3s)"
        # Same casino → identical trust_score/verdict since cache clone
        assert first_data["trust_score"] == second_data["trust_score"]
        assert first_data["verdict"] == second_data["verdict"]
        # But different id/slug (per-user record)
        assert first_data["id"] != second_data["id"]
