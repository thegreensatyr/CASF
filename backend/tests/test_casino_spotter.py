"""Backend tests for Casino Spotter API."""
import io
import os
import uuid
import struct
import zlib
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://scam-spotter-casino.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"

# load frontend env to get the public URL if not set
if not os.environ.get("REACT_APP_BACKEND_URL"):
    try:
        with open("/app/frontend/.env") as f:
            for line in f:
                if line.startswith("REACT_APP_BACKEND_URL="):
                    BASE_URL = line.split("=", 1)[1].strip().strip('"').rstrip("/")
                    API = f"{BASE_URL}/api"
    except Exception:
        pass


def _png_bytes():
    """Minimal 1x1 PNG."""
    sig = b"\x89PNG\r\n\x1a\n"
    ihdr_data = struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0)
    ihdr = b"IHDR" + ihdr_data
    ihdr_chunk = struct.pack(">I", len(ihdr_data)) + ihdr + struct.pack(">I", zlib.crc32(ihdr))
    raw = b"\x00\xff\x00\x00"
    comp = zlib.compress(raw)
    idat = b"IDAT" + comp
    idat_chunk = struct.pack(">I", len(comp)) + idat + struct.pack(">I", zlib.crc32(idat))
    iend = b"IEND"
    iend_chunk = struct.pack(">I", 0) + iend + struct.pack(">I", zlib.crc32(iend))
    return sig + ihdr_chunk + idat_chunk + iend_chunk


@pytest.fixture(scope="session")
def fresh_user():
    email = f"test_{uuid.uuid4().hex[:8]}@cs.io"
    password = "pass123!"
    r = requests.post(f"{API}/auth/signup", json={"email": email, "password": password, "name": "Tester"}, timeout=30)
    assert r.status_code == 200, r.text
    data = r.json()
    return {"email": email, "password": password, "token": data["token"], "user": data["user"]}


@pytest.fixture(scope="session")
def auth_headers(fresh_user):
    return {"Authorization": f"Bearer {fresh_user['token']}"}


# ============== AUTH ==============
class TestAuth:
    def test_signup_new(self):
        email = f"test_{uuid.uuid4().hex[:8]}@cs.io"
        r = requests.post(f"{API}/auth/signup", json={"email": email, "password": "pw12345", "name": "X"}, timeout=30)
        assert r.status_code == 200
        d = r.json()
        assert "token" in d and isinstance(d["token"], str) and len(d["token"]) > 10
        assert d["user"]["email"] == email
        assert "id" in d["user"]

    def test_signup_duplicate(self, fresh_user):
        r = requests.post(f"{API}/auth/signup", json={
            "email": fresh_user["email"], "password": "pass123!", "name": "Tester"
        }, timeout=30)
        assert r.status_code == 400

    def test_login_correct(self, fresh_user):
        r = requests.post(f"{API}/auth/login", json={
            "email": fresh_user["email"], "password": fresh_user["password"]
        }, timeout=30)
        assert r.status_code == 200
        assert "token" in r.json()

    def test_login_wrong(self, fresh_user):
        r = requests.post(f"{API}/auth/login", json={
            "email": fresh_user["email"], "password": "wrong-pw"
        }, timeout=30)
        assert r.status_code == 401

    def test_me_valid(self, fresh_user, auth_headers):
        r = requests.get(f"{API}/auth/me", headers=auth_headers, timeout=30)
        assert r.status_code == 200
        assert r.json()["email"] == fresh_user["email"]

    def test_me_invalid(self):
        r = requests.get(f"{API}/auth/me", headers={"Authorization": "Bearer bogus.token.value"}, timeout=30)
        assert r.status_code == 401


# ============== TECHNIQUES ==============
class TestTechniques:
    def test_list(self):
        r = requests.get(f"{API}/techniques", timeout=30)
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, list)
        assert len(data) == 8
        required = {"slug", "name", "category", "short", "description", "how_it_works", "how_to_spot", "severity"}
        for t in data:
            assert required.issubset(t.keys())

    def test_get_near_miss(self):
        r = requests.get(f"{API}/techniques/near-miss", timeout=30)
        assert r.status_code == 200
        assert r.json()["slug"] == "near-miss"

    def test_get_nonexistent(self):
        r = requests.get(f"{API}/techniques/does-not-exist", timeout=30)
        assert r.status_code == 404


# ============== LEGITIMACY ==============
class TestLegitimacy:
    def test_research_reputable(self, auth_headers):
        r = requests.post(f"{API}/legitimacy/research",
                          json={"casino_name": "Bet365"},
                          headers=auth_headers, timeout=120)
        assert r.status_code == 200, r.text
        d = r.json()
        for f in ["trust_score", "verdict", "report", "red_flags", "green_flags"]:
            assert f in d
        assert isinstance(d["trust_score"], int)
        assert 0 <= d["trust_score"] <= 100
        assert isinstance(d["red_flags"], list)
        assert isinstance(d["green_flags"], list)
        assert len(d["report"]) > 50

    def test_research_scam(self, auth_headers):
        r = requests.post(f"{API}/legitimacy/research",
                          json={"casino_name": "Lucky31"},
                          headers=auth_headers, timeout=120)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["trust_score"] < 60, f"expected low trust, got {d['trust_score']}"
        # red flags expected for blacklisted
        assert len(d["red_flags"]) > 0 or d["trust_score"] < 40

    def test_history(self, auth_headers):
        r = requests.get(f"{API}/legitimacy/history", headers=auth_headers, timeout=30)
        assert r.status_code == 200
        assert isinstance(r.json(), list)
        assert len(r.json()) >= 1


# ============== ANALYSIS ==============
class TestAnalysis:
    def test_upload_no_auth(self):
        files = {"file": ("test.png", io.BytesIO(_png_bytes()), "image/png")}
        data = {"game_type": "Slots", "casino_name": "Test"}
        r = requests.post(f"{API}/analysis/upload", files=files, data=data, timeout=30)
        assert r.status_code in (401, 403)

    def test_upload_image(self, auth_headers):
        files = {"file": ("test.png", io.BytesIO(_png_bytes()), "image/png")}
        data = {"game_type": "Slots", "casino_name": "Test"}
        r = requests.post(f"{API}/analysis/upload", files=files, data=data, headers=auth_headers, timeout=120)
        assert r.status_code == 200, r.text
        d = r.json()
        for f in ["id", "user_id", "media_type", "game_type", "casino_name", "file_name", "analysis", "techniques_detected", "created_at"]:
            assert f in d
        assert d["media_type"] == "image"
        assert d["game_type"] == "Slots"
        assert len(d["analysis"]) > 20
        assert isinstance(d["techniques_detected"], list)

    def test_history(self, auth_headers):
        r = requests.get(f"{API}/analysis/history", headers=auth_headers, timeout=30)
        assert r.status_code == 200
        assert isinstance(r.json(), list)
        assert len(r.json()) >= 1
