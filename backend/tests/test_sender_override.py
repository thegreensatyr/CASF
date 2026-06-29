"""Verify SENDER_EMAIL sandbox override + defaults across 3 env scenarios."""
import os
import sys
import importlib
import subprocess
import json


def _run_in_env(env_overrides: dict):
    """Spawn a child python that imports server with custom env and prints config as JSON."""
    code = (
        "import importlib, sys, json\n"
        "sys.path.insert(0, '/app/backend')\n"
        "if 'server' in sys.modules: del sys.modules['server']\n"
        "import server\n"
        "print('___JSON___' + json.dumps({\n"
        "    'SENDER_EMAIL': server.SENDER_EMAIL,\n"
        "    'SENDER_NAME': server.SENDER_NAME,\n"
        "    'REPLY_TO': server.REPLY_TO,\n"
        "    'SITE_URL': server.SITE_URL,\n"
        "    'SENDER_FROM': server.SENDER_FROM,\n"
        "}))\n"
    )
    # Base env: keep MONGO_URL/DB_NAME/EMERGENT_LLM_KEY/JWT_SECRET (required), strip sender vars
    env = {k: v for k, v in os.environ.items()
           if k not in {"SENDER_EMAIL", "SENDER_NAME", "REPLY_TO", "SITE_URL"}}
    env.update(env_overrides)
    # Disable load_dotenv() by pointing it at a non-existent dir? load_dotenv won't overwrite
    # existing env vars (default override=False), so as long as we SET the overrides explicitly,
    # they win. For the "empty env" case, we have to pre-empt the .env file values; do this by
    # passing override values as the test condition (we test what happens when env is empty
    # AND .env has no values — but .env DOES have values in this repo). Workaround: run with
    # cwd in a temp dir so the relative .env path isn't found... but server uses
    # ROOT_DIR/.env. Instead, we explicitly set the values we WANT and trust load_dotenv's
    # no-overwrite semantics.
    result = subprocess.run(
        [sys.executable, "-c", code],
        env=env, capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 0, f"child crashed: {result.stderr}"
    line = [ln for ln in result.stdout.splitlines() if ln.startswith("___JSON___")]
    assert line, f"no json marker in: {result.stdout}\n{result.stderr}"
    return json.loads(line[0][len("___JSON___"):])


def test_boot1_preview_env_explicit_verified_sender():
    """BOOT TEST 1: preview .env has SENDER_EMAIL=noreply@casforensics.org explicitly."""
    cfg = _run_in_env({
        "SENDER_EMAIL": "noreply@casforensics.org",
        "SITE_URL": "https://casforensics.org",
    })
    assert cfg["SENDER_EMAIL"] == "noreply@casforensics.org"
    assert cfg["SITE_URL"] == "https://casforensics.org"


def test_boot2_production_stale_sandbox_overrides_to_verified():
    """BOOT TEST 2: simulate production with stale SENDER_EMAIL=onboarding@resend.dev."""
    cfg = _run_in_env({
        "SENDER_EMAIL": "onboarding@resend.dev",
        "SITE_URL": "https://casforensics.org",
    })
    assert cfg["SENDER_EMAIL"] == "noreply@casforensics.org", \
        f"sandbox override did not fire, got {cfg['SENDER_EMAIL']}"
    assert cfg["SENDER_FROM"] == "Casino Spotter <noreply@casforensics.org>"


def test_boot3_empty_env_defaults():
    """BOOT TEST 3: no sender vars set anywhere — but .env file is still loaded by server.
    To truly test the defaults, we use override values that force the fallback path."""
    # We can't easily prevent .env from loading without filesystem changes.
    # Instead, prove the defaults by setting EMPTY strings — the code uses
    # `(os.environ.get(...) or "").strip()` and falls back to defaults when empty.
    cfg = _run_in_env({
        "SENDER_EMAIL": "",
        "SENDER_NAME": "",
        "REPLY_TO": "",
        "SITE_URL": "",
    })
    # NOTE: load_dotenv(override=False) won't replace already-set (even empty) env vars
    # on most python-dotenv versions; verify the defaults all fire.
    assert cfg["SENDER_EMAIL"] == "noreply@casforensics.org"
    assert cfg["SENDER_NAME"] == "Casino Spotter"
    assert cfg["REPLY_TO"] == "casforensics@gmail.com"
    assert cfg["SITE_URL"] == "https://casforensics.org"
