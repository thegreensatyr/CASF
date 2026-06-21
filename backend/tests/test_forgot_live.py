"""Forgot-password regression + Live screen-capture API tests."""
import os
import time
import base64
import io
import uuid
import requests
import pytest
from PIL import Image

BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/") if os.environ.get("REACT_APP_BACKEND_URL") else "https://scam-spotter-casino.preview.emergentagent.com"
API = f"{BASE_URL}/api"

ADMIN_EMAIL = "casforensics@gmail.com"
ADMIN_PASSWORD = "CasForensics2026!"
LEGACY_EMAIL = "test@cs.io"
LEGACY_PASSWORD = "pass123"


def _make_jpeg_data_url(color=(255, 0, 0)):
    img = Image.new("RGB", (32, 32), color)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=60)
    b64 = base64.b64encode(buf.getvalue()).decode()
    return f"data:image/jpeg;base64,{b64}"


@pytest.fixture(scope="module")
def admin_token():
    r = requests.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
    assert r.status_code == 200, f"Admin login failed: {r.status_code} {r.text}"
    return r.json()["token"]


@pytest.fixture(scope="module")
def admin_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}"}


@pytest.fixture(scope="module")
def legacy_token():
    r = requests.post(f"{API}/auth/login", json={"email": LEGACY_EMAIL, "password": LEGACY_PASSWORD})
    if r.status_code != 200:
        pytest.skip("legacy user unavailable")
    return r.json()["token"]


def signup_user(suffix=None):
    suffix = suffix or uuid.uuid4().hex[:8]
    email = f"TEST_live_{suffix}@cs.io"
    pwd = "TestPass#1"
    r = requests.post(f"{API}/auth/signup", json={"email": email, "password": pwd, "name": f"Test {suffix}"})
    assert r.status_code in (200, 201), r.text
    data = r.json()
    return {"email": email, "password": pwd, "token": data["token"], "user": data["user"]}


# ----------------- FORGOT PASSWORD REGRESSION -----------------
class TestForgotPassword:
    debug_token_holder = {}

    def test_forgot_admin_returns_debug_link(self):
        r = requests.post(f"{API}/auth/forgot-password",
                          json={"email": ADMIN_EMAIL, "origin_url": BASE_URL})
        assert r.status_code == 200, r.text
        data = r.json()
        assert data.get("ok") is True
        assert "debug_link" in data, f"admin response missing debug_link: {data}"
        link = data["debug_link"]
        assert "token=" in link
        token = link.split("token=")[-1]
        TestForgotPassword.debug_token_holder["token"] = token

    def test_forgot_non_admin_no_debug_link(self):
        r = requests.post(f"{API}/auth/forgot-password",
                          json={"email": LEGACY_EMAIL, "origin_url": BASE_URL})
        assert r.status_code == 200
        data = r.json()
        assert data.get("ok") is True
        assert "debug_link" not in data, f"non-admin should not get debug_link: {data}"

    def test_forgot_unknown_email_generic_no_enum(self):
        r = requests.post(f"{API}/auth/forgot-password",
                          json={"email": f"nobody_{uuid.uuid4().hex[:6]}@nowhere.io",
                                "origin_url": BASE_URL})
        assert r.status_code == 200
        data = r.json()
        assert data.get("ok") is True
        assert "debug_link" not in data

    def test_reset_invalid_token_rejected(self):
        r = requests.post(f"{API}/auth/reset-password",
                          json={"token": "not-a-real-token", "password": "NewPass#1"})
        assert r.status_code == 400

    def test_reset_short_password_rejected(self):
        token = self.debug_token_holder.get("token")
        if not token:
            pytest.skip("no admin token captured")
        r = requests.post(f"{API}/auth/reset-password",
                          json={"token": token, "password": "abc"})
        assert r.status_code in (400, 422), r.text

    def test_reset_success_then_reuse_rejected_and_restore(self):
        token = self.debug_token_holder.get("token")
        assert token, "missing token from previous test"
        new_pw = "TempReset#9"
        # 1st use OK
        r = requests.post(f"{API}/auth/reset-password",
                          json={"token": token, "password": new_pw})
        assert r.status_code == 200, r.text
        body = r.json()
        assert "token" in body and "user" in body
        assert body["user"]["email"].lower() == ADMIN_EMAIL.lower()

        # verify can login with new password
        l = requests.post(f"{API}/auth/login",
                         json={"email": ADMIN_EMAIL, "password": new_pw})
        assert l.status_code == 200

        # reuse rejected
        reuse = requests.post(f"{API}/auth/reset-password",
                              json={"token": token, "password": "Another#1"})
        assert reuse.status_code == 400

        # restore admin password to canonical
        r2 = requests.post(f"{API}/auth/forgot-password",
                           json={"email": ADMIN_EMAIL, "origin_url": BASE_URL})
        tok2 = r2.json()["debug_link"].split("token=")[-1]
        restore = requests.post(f"{API}/auth/reset-password",
                                json={"token": tok2, "password": ADMIN_PASSWORD})
        assert restore.status_code == 200, f"restore failed: {restore.text}"
        # verify
        verify = requests.post(f"{API}/auth/login",
                              json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
        assert verify.status_code == 200


# ----------------- LIVE SESSION START -----------------
class TestLiveStart:
    def test_start_requires_auth(self):
        r = requests.post(f"{API}/live/session/start", json={"game_type": "slot"})
        assert r.status_code in (401, 403)

    def test_start_premium_admin_180s(self, admin_headers):
        r = requests.post(f"{API}/live/session/start",
                          json={"game_type": "slot", "casino_name": "TEST_casino"},
                          headers=admin_headers)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["cadence_seconds"] == 15
        assert data["max_seconds"] == 180
        assert data["is_trial"] is False
        assert "session_id" in data
        # store for later
        TestLiveStart.admin_session_id = data["session_id"]

    def test_start_free_user_trial_then_402(self):
        u = signup_user()
        h = {"Authorization": f"Bearer {u['token']}"}
        r = requests.post(f"{API}/live/session/start",
                          json={"game_type": "slot", "casino_name": "TEST_freecasino"},
                          headers=h)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["max_seconds"] == 60
        assert data["is_trial"] is True
        sid = data["session_id"]

        # End the first one so user state moves on
        e = requests.post(f"{API}/live/session/end",
                         json={"session_id": sid}, headers=h)
        assert e.status_code == 200

        # verify live_trial_used flag
        me = requests.get(f"{API}/auth/me", headers=h)
        assert me.status_code == 200
        assert me.json().get("live_trial_used") is True

        # second start attempt should 402
        r2 = requests.post(f"{API}/live/session/start",
                           json={"game_type": "slot"}, headers=h)
        assert r2.status_code == 402, r2.text


# ----------------- LIVE FRAME -----------------
class TestLiveFrame:
    @pytest.fixture(scope="class")
    def admin_session(self, admin_headers):
        r = requests.post(f"{API}/live/session/start",
                          json={"game_type": "slot", "casino_name": "TEST_frame"},
                          headers=admin_headers)
        assert r.status_code == 200
        return r.json()["session_id"]

    def test_frame_basic(self, admin_headers, admin_session):
        body = {
            "session_id": admin_session,
            "frame_data_url": _make_jpeg_data_url(),
            "elapsed_seconds": 0,
        }
        r = requests.post(f"{API}/live/frame", json=body, headers=admin_headers, timeout=60)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["frame_idx"] == 0
        assert isinstance(data["note"], str)
        assert isinstance(data["should_continue"], bool)
        # remaining = 180 - 0 - 15 = 165
        assert data["remaining_seconds"] == 165

    def test_frame_unknown_session_404(self, admin_headers):
        body = {
            "session_id": "does-not-exist-" + uuid.uuid4().hex[:8],
            "frame_data_url": _make_jpeg_data_url(),
            "elapsed_seconds": 5,
        }
        r = requests.post(f"{API}/live/frame", json=body, headers=admin_headers)
        assert r.status_code == 404

    def test_frame_elapsed_exceeds_max_400(self, admin_headers, admin_session):
        body = {
            "session_id": admin_session,
            "frame_data_url": _make_jpeg_data_url(),
            "elapsed_seconds": 999,
        }
        r = requests.post(f"{API}/live/frame", json=body, headers=admin_headers)
        assert r.status_code == 400, r.text

    def test_frame_invalid_data_url_400(self, admin_headers, admin_session):
        body = {
            "session_id": admin_session,
            "frame_data_url": "notadataurl",
            "elapsed_seconds": 15,
        }
        r = requests.post(f"{API}/live/frame", json=body, headers=admin_headers)
        assert r.status_code == 400


# ----------------- LIVE SESSION END -----------------
class TestLiveEnd:
    def test_end_with_frames_generates_summary_idempotent(self, admin_headers):
        # start fresh
        s = requests.post(f"{API}/live/session/start",
                          json={"game_type": "slot", "casino_name": "TEST_end"},
                          headers=admin_headers).json()
        sid = s["session_id"]
        # post one frame
        fb = {"session_id": sid, "frame_data_url": _make_jpeg_data_url((0, 200, 0)),
              "elapsed_seconds": 0}
        requests.post(f"{API}/live/frame", json=fb, headers=admin_headers, timeout=60)
        # end
        r = requests.post(f"{API}/live/session/end",
                         json={"session_id": sid}, headers=admin_headers, timeout=60)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["frame_count"] >= 1
        assert isinstance(data["summary"], str) and data["summary"]
        first_summary = data["summary"]
        # idempotent
        r2 = requests.post(f"{API}/live/session/end",
                          json={"session_id": sid}, headers=admin_headers)
        assert r2.status_code == 200
        assert r2.json()["summary"] == first_summary

    def test_end_no_frames_fallback_summary(self, admin_headers):
        s = requests.post(f"{API}/live/session/start",
                         json={"game_type": "slot", "casino_name": "TEST_empty"},
                         headers=admin_headers).json()
        sid = s["session_id"]
        r = requests.post(f"{API}/live/session/end",
                         json={"session_id": sid}, headers=admin_headers)
        assert r.status_code == 200
        data = r.json()
        assert data["frame_count"] == 0
        assert isinstance(data["summary"], str)


# ----------------- LIVE LIST / DETAIL -----------------
class TestLiveListDetail:
    def test_list_returns_user_sessions_no_frames(self, admin_headers):
        r = requests.get(f"{API}/live/sessions", headers=admin_headers)
        assert r.status_code == 200, r.text
        items = r.json()
        assert isinstance(items, list)
        if items:
            assert items[0].get("frames", []) == []  # list omits frames

    def test_detail_returns_frames(self, admin_headers):
        # create session w/ a frame
        s = requests.post(f"{API}/live/session/start",
                         json={"game_type": "slot", "casino_name": "TEST_detail"},
                         headers=admin_headers).json()
        sid = s["session_id"]
        fb = {"session_id": sid, "frame_data_url": _make_jpeg_data_url((0, 0, 200)),
              "elapsed_seconds": 0}
        requests.post(f"{API}/live/frame", json=fb, headers=admin_headers, timeout=60)
        requests.post(f"{API}/live/session/end", json={"session_id": sid}, headers=admin_headers, timeout=60)
        r = requests.get(f"{API}/live/session/{sid}", headers=admin_headers)
        assert r.status_code == 200
        d = r.json()
        assert d["id"] == sid
        assert isinstance(d.get("frames"), list) and len(d["frames"]) >= 1

    def test_cannot_fetch_other_users_session(self, admin_headers):
        # fresh user creates a session
        u = signup_user()
        h = {"Authorization": f"Bearer {u['token']}"}
        s = requests.post(f"{API}/live/session/start",
                         json={"game_type": "slot"}, headers=h).json()
        sid = s["session_id"]
        # admin tries to fetch
        r = requests.get(f"{API}/live/session/{sid}", headers=admin_headers)
        assert r.status_code == 404
