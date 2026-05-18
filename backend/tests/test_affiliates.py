"""Backend tests for Affiliate Casinos (Monetization) endpoints."""
import os
import uuid
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

ADMIN_EMAIL = "admin@cs.io"
ADMIN_PASS = "admin1234"
USER_EMAIL = "test@cs.io"
USER_PASS = "pass123"


# ---------- Auth helpers ----------
def _login_or_signup(email: str, password: str, name: str) -> str:
    r = requests.post(f"{API}/auth/login", json={"email": email, "password": password}, timeout=30)
    if r.status_code == 200:
        return r.json()["token"]
    r = requests.post(f"{API}/auth/signup", json={"email": email, "password": password, "name": name}, timeout=30)
    assert r.status_code == 200, f"signup failed: {r.status_code} {r.text}"
    return r.json()["token"]


@pytest.fixture(scope="session")
def admin_token():
    return _login_or_signup(ADMIN_EMAIL, ADMIN_PASS, "Admin")


@pytest.fixture(scope="session")
def user_token():
    return _login_or_signup(USER_EMAIL, USER_PASS, "Tester")


@pytest.fixture(scope="session")
def admin_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}"}


@pytest.fixture(scope="session")
def user_headers(user_token):
    return {"Authorization": f"Bearer {user_token}"}


@pytest.fixture(scope="session")
def created_ids():
    return []


@pytest.fixture(scope="session", autouse=True)
def cleanup_created(admin_headers, created_ids):
    yield
    # teardown - delete any leftover test casinos
    for cid in list(created_ids):
        try:
            requests.delete(f"{API}/affiliates/casinos/{cid}", headers=admin_headers, timeout=15)
        except Exception:
            pass


# ---------- auth/me admin flag ----------
class TestAuthMe:
    def test_admin_me_is_admin_true(self, admin_headers):
        r = requests.get(f"{API}/auth/me", headers=admin_headers, timeout=15)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["email"].lower() == ADMIN_EMAIL
        assert data["is_admin"] is True

    def test_user_me_is_admin_false(self, user_headers):
        r = requests.get(f"{API}/auth/me", headers=user_headers, timeout=15)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["email"].lower() == USER_EMAIL
        assert data["is_admin"] is False


# ---------- Public list ----------
class TestPublicList:
    def test_list_no_auth_returns_active_only_sorted(self):
        r = requests.get(f"{API}/affiliates/casinos", timeout=15)
        assert r.status_code == 200, r.text
        data = r.json()
        assert isinstance(data, list)
        # All should be active
        for c in data:
            assert c["active"] is True
            assert "id" in c and "name" in c and "url" in c
            assert "sort_order" in c
            assert "created_at" in c
        # sorted by sort_order asc then created_at asc
        keys = [(c["sort_order"], c["created_at"]) for c in data]
        assert keys == sorted(keys), f"Public list not sorted: {keys}"


# ---------- Admin Create / Update / Delete ----------
class TestAdminCRUD:
    def test_create_as_admin(self, admin_headers, created_ids):
        unique = f"TEST_AFF_{uuid.uuid4().hex[:8]}"
        payload = {
            "name": unique,
            "url": "https://example.com/aff",
            "license": "MGA",
            "badge": "Top Pick",
            "description": "Test affiliate casino",
            "logo_url": "https://example.com/logo.png",
            "payout_note": "24h payouts",
            "sort_order": 5,
            "active": True,
        }
        r = requests.post(f"{API}/affiliates/casinos", json=payload, headers=admin_headers, timeout=20)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["name"] == unique
        assert data["url"] == payload["url"]
        assert data["license"] == "MGA"
        assert data["sort_order"] == 5
        assert data["active"] is True
        assert "id" in data and isinstance(data["id"], str)
        assert "created_at" in data
        created_ids.append(data["id"])

        # Verify it appears in public list
        r2 = requests.get(f"{API}/affiliates/casinos", timeout=15)
        assert r2.status_code == 200
        names = [c["name"] for c in r2.json()]
        assert unique in names

    def test_create_no_auth_unauthorized(self):
        payload = {"name": f"TEST_NOAUTH_{uuid.uuid4().hex[:6]}", "url": "https://x.com"}
        r = requests.post(f"{API}/affiliates/casinos", json=payload, timeout=15)
        assert r.status_code in (401, 403), f"expected 401/403 got {r.status_code}: {r.text}"

    def test_create_as_non_admin_forbidden(self, user_headers):
        payload = {"name": f"TEST_NONADMIN_{uuid.uuid4().hex[:6]}", "url": "https://x.com"}
        r = requests.post(f"{API}/affiliates/casinos", json=payload, headers=user_headers, timeout=15)
        assert r.status_code == 403, f"expected 403 got {r.status_code}: {r.text}"

    def test_update_as_admin(self, admin_headers, created_ids):
        unique = f"TEST_UPD_{uuid.uuid4().hex[:8]}"
        create = requests.post(
            f"{API}/affiliates/casinos",
            json={"name": unique, "url": "https://x.com", "sort_order": 1, "active": True},
            headers=admin_headers, timeout=20,
        )
        assert create.status_code == 200
        cid = create.json()["id"]
        created_ids.append(cid)

        new_name = unique + "_UPD"
        upd = requests.put(
            f"{API}/affiliates/casinos/{cid}",
            json={
                "name": new_name, "url": "https://y.com", "license": "UKGC", "badge": "Updated",
                "description": "upd", "logo_url": None, "payout_note": "fast", "sort_order": 9, "active": False,
            },
            headers=admin_headers, timeout=20,
        )
        assert upd.status_code == 200, upd.text
        d = upd.json()
        assert d["name"] == new_name
        assert d["url"] == "https://y.com"
        assert d["license"] == "UKGC"
        assert d["sort_order"] == 9
        assert d["active"] is False

        # Verify via /all (admin)
        all_r = requests.get(f"{API}/affiliates/casinos/all", headers=admin_headers, timeout=15)
        assert all_r.status_code == 200
        found = [c for c in all_r.json() if c["id"] == cid]
        assert found and found[0]["name"] == new_name and found[0]["active"] is False

    def test_update_as_non_admin_forbidden(self, admin_headers, user_headers, created_ids):
        # create as admin first
        unique = f"TEST_UPDFB_{uuid.uuid4().hex[:8]}"
        create = requests.post(
            f"{API}/affiliates/casinos",
            json={"name": unique, "url": "https://x.com"},
            headers=admin_headers, timeout=20,
        )
        assert create.status_code == 200
        cid = create.json()["id"]
        created_ids.append(cid)

        r = requests.put(
            f"{API}/affiliates/casinos/{cid}",
            json={"name": unique + "_X", "url": "https://x.com"},
            headers=user_headers, timeout=15,
        )
        assert r.status_code == 403

    def test_delete_as_admin(self, admin_headers, created_ids):
        unique = f"TEST_DEL_{uuid.uuid4().hex[:8]}"
        create = requests.post(
            f"{API}/affiliates/casinos",
            json={"name": unique, "url": "https://x.com"},
            headers=admin_headers, timeout=20,
        )
        assert create.status_code == 200
        cid = create.json()["id"]

        d = requests.delete(f"{API}/affiliates/casinos/{cid}", headers=admin_headers, timeout=15)
        assert d.status_code == 200, d.text
        body = d.json()
        assert body.get("deleted") == cid

        # Verify gone from /all
        all_r = requests.get(f"{API}/affiliates/casinos/all", headers=admin_headers, timeout=15)
        assert all_r.status_code == 200
        ids = [c["id"] for c in all_r.json()]
        assert cid not in ids

    def test_delete_nonexistent_returns_404(self, admin_headers):
        fake_id = f"nonexistent-{uuid.uuid4().hex}"
        r = requests.delete(f"{API}/affiliates/casinos/{fake_id}", headers=admin_headers, timeout=15)
        assert r.status_code == 404


# ---------- /all endpoint ----------
class TestAllEndpoint:
    def test_all_as_admin(self, admin_headers, user_headers, created_ids):
        # Create an inactive casino
        unique = f"TEST_INACT_{uuid.uuid4().hex[:8]}"
        r = requests.post(
            f"{API}/affiliates/casinos",
            json={"name": unique, "url": "https://inactive.com", "active": False, "sort_order": 100},
            headers=admin_headers, timeout=20,
        )
        assert r.status_code == 200
        cid = r.json()["id"]
        created_ids.append(cid)

        # /all should include inactive
        all_r = requests.get(f"{API}/affiliates/casinos/all", headers=admin_headers, timeout=15)
        assert all_r.status_code == 200
        all_names = [c["name"] for c in all_r.json()]
        assert unique in all_names

        # public list should NOT include inactive
        pub = requests.get(f"{API}/affiliates/casinos", timeout=15)
        assert pub.status_code == 200
        pub_names = [c["name"] for c in pub.json()]
        assert unique not in pub_names

    def test_all_as_non_admin_forbidden(self, user_headers):
        r = requests.get(f"{API}/affiliates/casinos/all", headers=user_headers, timeout=15)
        assert r.status_code == 403

    def test_all_no_auth_forbidden(self):
        r = requests.get(f"{API}/affiliates/casinos/all", timeout=15)
        assert r.status_code in (401, 403)


# ---------- Click tracking ----------
class TestClick:
    def test_click_no_auth(self, admin_headers, created_ids):
        # create a target casino
        unique = f"TEST_CLK_{uuid.uuid4().hex[:8]}"
        cr = requests.post(
            f"{API}/affiliates/casinos",
            json={"name": unique, "url": "https://clk.com"},
            headers=admin_headers, timeout=20,
        )
        assert cr.status_code == 200
        cid = cr.json()["id"]
        created_ids.append(cid)

        r = requests.post(f"{API}/affiliates/click", json={"affiliate_id": cid, "source": "test"}, timeout=15)
        assert r.status_code == 200, r.text
        assert r.json() == {"ok": True}

        # verify click counted in stats
        stats = requests.get(f"{API}/affiliates/stats", headers=admin_headers, timeout=15)
        assert stats.status_code == 200
        match = [s for s in stats.json() if s["id"] == cid]
        assert match and match[0]["clicks"] >= 1

    def test_click_with_auth(self, admin_headers, user_headers, created_ids):
        unique = f"TEST_CLKAUTH_{uuid.uuid4().hex[:8]}"
        cr = requests.post(
            f"{API}/affiliates/casinos",
            json={"name": unique, "url": "https://clkauth.com"},
            headers=admin_headers, timeout=20,
        )
        assert cr.status_code == 200
        cid = cr.json()["id"]
        created_ids.append(cid)

        r = requests.post(
            f"{API}/affiliates/click",
            json={"affiliate_id": cid, "source": "test_auth"},
            headers=user_headers, timeout=15,
        )
        assert r.status_code == 200
        assert r.json() == {"ok": True}

        stats = requests.get(f"{API}/affiliates/stats", headers=admin_headers, timeout=15)
        assert stats.status_code == 200
        match = [s for s in stats.json() if s["id"] == cid]
        assert match and match[0]["clicks"] >= 1


# ---------- Stats endpoint ----------
class TestStats:
    def test_stats_as_admin(self, admin_headers):
        r = requests.get(f"{API}/affiliates/stats", headers=admin_headers, timeout=15)
        assert r.status_code == 200, r.text
        data = r.json()
        assert isinstance(data, list)
        for row in data:
            assert "id" in row
            assert "name" in row
            assert "clicks" in row
            assert isinstance(row["clicks"], int)
            assert "active" in row

    def test_stats_as_non_admin_forbidden(self, user_headers):
        r = requests.get(f"{API}/affiliates/stats", headers=user_headers, timeout=15)
        assert r.status_code == 403

    def test_stats_no_auth_forbidden(self):
        r = requests.get(f"{API}/affiliates/stats", timeout=15)
        assert r.status_code in (401, 403)
