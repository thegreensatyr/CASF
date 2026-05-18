"""Backend tests for Casino Spotter — Scam Wall feature (/api/scams)."""
import os
import uuid
import time
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
if not BASE_URL:
    try:
        with open("/app/frontend/.env") as f:
            for line in f:
                if line.startswith("REACT_APP_BACKEND_URL="):
                    BASE_URL = line.split("=", 1)[1].strip().strip('"').rstrip("/")
    except Exception:
        pass
API = f"{BASE_URL}/api"


def _signup():
    email = f"test_{uuid.uuid4().hex[:8]}@cs.io"
    pw = "pass123!"
    r = requests.post(f"{API}/auth/signup",
                      json={"email": email, "password": pw, "name": f"U_{email[:10]}"},
                      timeout=30)
    assert r.status_code == 200, r.text
    return {"email": email, "password": pw, "token": r.json()["token"], "user": r.json()["user"]}


@pytest.fixture(scope="session")
def user_a():
    return _signup()


@pytest.fixture(scope="session")
def user_b():
    return _signup()


@pytest.fixture(scope="session")
def headers_a(user_a):
    return {"Authorization": f"Bearer {user_a['token']}"}


@pytest.fixture(scope="session")
def headers_b(user_b):
    return {"Authorization": f"Bearer {user_b['token']}"}


def _valid_payload(suffix=""):
    return {
        "casino_name": f"BadCasino{suffix}",
        "title": f"TEST scam report {suffix} {uuid.uuid4().hex[:6]}",
        "story": "They refused to pay my withdrawal after I won and locked my account. " + suffix,
        "evidence_url": "https://example.com/proof",
    }


# ============== CREATE ==============
class TestCreateScam:
    def test_create_requires_auth(self):
        r = requests.post(f"{API}/scams", json=_valid_payload("noauth"), timeout=30)
        assert r.status_code in (401, 403), r.text

    def test_create_success(self, headers_a):
        payload = _valid_payload("ok")
        r = requests.post(f"{API}/scams", json=payload, headers=headers_a, timeout=30)
        assert r.status_code == 200, r.text
        d = r.json()
        for f in ("id", "user_id", "author_name", "casino_name", "title", "story",
                  "upvotes", "downvotes", "score", "my_vote", "created_at"):
            assert f in d, f"missing field {f}"
        assert d["upvotes"] == 0
        assert d["downvotes"] == 0
        assert d["score"] == 0
        assert d["my_vote"] is None
        assert d["title"] == payload["title"]
        assert d["casino_name"] == payload["casino_name"]
        assert isinstance(d["id"], str) and len(d["id"]) > 10

    def test_create_short_title(self, headers_a):
        p = _valid_payload("st")
        p["title"] = "abc"  # < 4
        r = requests.post(f"{API}/scams", json=p, headers=headers_a, timeout=30)
        assert r.status_code == 422, r.text

    def test_create_short_story(self, headers_a):
        p = _valid_payload("ss")
        p["story"] = "too short"  # < 20
        r = requests.post(f"{API}/scams", json=p, headers=headers_a, timeout=30)
        assert r.status_code == 422, r.text


# ============== LIST / GET ==============
class TestListAndGet:
    @pytest.fixture(scope="class")
    def seeded_posts(self, headers_a):
        ids = []
        for i in range(2):
            r = requests.post(f"{API}/scams", json=_valid_payload(f"seed{i}"),
                              headers=headers_a, timeout=30)
            assert r.status_code == 200
            ids.append(r.json()["id"])
            time.sleep(1.1)  # ensure distinct created_at for sort=new
        return ids

    def test_list_default_top(self, seeded_posts):
        r = requests.get(f"{API}/scams", timeout=30)
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, list)
        assert len(data) >= 2
        # sort by score desc, then created_at desc (tie breaker)
        scores = [p["score"] for p in data]
        assert scores == sorted(scores, reverse=True), f"not sorted by score desc: {scores}"

    def test_list_sort_top_explicit(self, seeded_posts):
        r = requests.get(f"{API}/scams", params={"sort": "top"}, timeout=30)
        assert r.status_code == 200
        scores = [p["score"] for p in r.json()]
        assert scores == sorted(scores, reverse=True)

    def test_list_sort_new(self, seeded_posts):
        r = requests.get(f"{API}/scams", params={"sort": "new"}, timeout=30)
        assert r.status_code == 200
        data = r.json()
        created = [p["created_at"] for p in data]
        assert created == sorted(created, reverse=True), f"not sorted by created_at desc: {created}"

    def test_list_unauth_my_vote_null(self, seeded_posts):
        r = requests.get(f"{API}/scams", timeout=30)
        assert r.status_code == 200
        for p in r.json():
            assert p["my_vote"] is None

    def test_get_valid(self, seeded_posts):
        pid = seeded_posts[0]
        r = requests.get(f"{API}/scams/{pid}", timeout=30)
        assert r.status_code == 200
        d = r.json()
        assert d["id"] == pid
        for f in ("upvotes", "downvotes", "score"):
            assert f in d and isinstance(d[f], int)

    def test_get_invalid_id(self):
        r = requests.get(f"{API}/scams/{uuid.uuid4().hex}", timeout=30)
        assert r.status_code == 404


# ============== VOTING ==============
class TestVoting:
    @pytest.fixture(scope="class")
    def post_id(self, headers_a):
        r = requests.post(f"{API}/scams", json=_valid_payload("vote"),
                          headers=headers_a, timeout=30)
        assert r.status_code == 200, r.text
        return r.json()["id"]

    def test_vote_requires_auth(self, post_id):
        r = requests.post(f"{API}/scams/{post_id}/vote", json={"vote": "up"}, timeout=30)
        assert r.status_code in (401, 403)

    def test_vote_invalid_string(self, post_id, headers_a):
        r = requests.post(f"{API}/scams/{post_id}/vote",
                          json={"vote": "sideways"}, headers=headers_a, timeout=30)
        # Pydantic doesn't restrict the literal at model level; server raises 400 manually
        assert r.status_code in (400, 422), r.text

    def test_upvote(self, post_id, headers_b):
        r = requests.post(f"{API}/scams/{post_id}/vote",
                          json={"vote": "up"}, headers=headers_b, timeout=30)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["upvotes"] == 1
        assert d["downvotes"] == 0
        assert d["score"] == 1
        assert d["my_vote"] == "up"

    def test_upvote_idempotent(self, post_id, headers_b):
        # Same user upvoting again should not duplicate
        r = requests.post(f"{API}/scams/{post_id}/vote",
                          json={"vote": "up"}, headers=headers_b, timeout=30)
        assert r.status_code == 200
        d = r.json()
        assert d["upvotes"] == 1
        assert d["downvotes"] == 0
        assert d["my_vote"] == "up"

    def test_switch_to_down(self, post_id, headers_b):
        r = requests.post(f"{API}/scams/{post_id}/vote",
                          json={"vote": "down"}, headers=headers_b, timeout=30)
        assert r.status_code == 200
        d = r.json()
        assert d["upvotes"] == 0
        assert d["downvotes"] == 1
        assert d["score"] == -1
        assert d["my_vote"] == "down"

    def test_two_users_independent(self, post_id, headers_a, headers_b):
        # user A upvotes (user B already has down from previous test)
        r_a = requests.post(f"{API}/scams/{post_id}/vote",
                            json={"vote": "up"}, headers=headers_a, timeout=30)
        assert r_a.status_code == 200
        d = r_a.json()
        assert d["upvotes"] == 1
        assert d["downvotes"] == 1
        assert d["score"] == 0
        assert d["my_vote"] == "up"

        # confirm from B's perspective
        r_b = requests.get(f"{API}/scams/{post_id}",
                           headers=headers_b, timeout=30)
        assert r_b.status_code == 200
        db = r_b.json()
        assert db["upvotes"] == 1 and db["downvotes"] == 1
        assert db["my_vote"] == "down"

    def test_remove_vote_none(self, post_id, headers_b):
        r = requests.post(f"{API}/scams/{post_id}/vote",
                          json={"vote": "none"}, headers=headers_b, timeout=30)
        assert r.status_code == 200
        d = r.json()
        # B's down removed; A's up remains
        assert d["upvotes"] == 1
        assert d["downvotes"] == 0
        assert d["score"] == 1
        assert d["my_vote"] is None  # from B's view

    def test_list_my_vote_when_auth(self, post_id, headers_a):
        r = requests.get(f"{API}/scams", headers=headers_a, timeout=30)
        assert r.status_code == 200
        found = next((p for p in r.json() if p["id"] == post_id), None)
        assert found is not None
        assert found["my_vote"] == "up"
