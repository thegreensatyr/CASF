import os
import re
import uuid
import base64
import secrets
import logging
import shutil
import asyncio
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import List, Optional

import bcrypt
import jwt
import resend
from dotenv import load_dotenv
from fastapi import FastAPI, APIRouter, HTTPException, Depends, UploadFile, File, Form, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.staticfiles import StaticFiles
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, EmailStr, Field

from emergentintegrations.llm.chat import LlmChat, UserMessage, FileContentWithMimeType
from emergentintegrations.payments.stripe.checkout import (
    StripeCheckout, CheckoutSessionRequest, CheckoutSessionResponse,
    CheckoutStatusResponse,
)
from fastapi import Request as FastAPIRequest
from fastapi.responses import Response

from technique_articles import TECHNIQUE_ARTICLES

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

UPLOAD_DIR = ROOT_DIR / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

MONGO_URL = os.environ["MONGO_URL"]
DB_NAME = os.environ["DB_NAME"]
EMERGENT_LLM_KEY = os.environ["EMERGENT_LLM_KEY"]
JWT_SECRET = os.environ["JWT_SECRET"]
STRIPE_API_KEY = os.environ.get("STRIPE_API_KEY", "sk_test_emergent")
RESEND_API_KEY = os.environ.get("RESEND_API_KEY", "")
SENDER_EMAIL = os.environ.get("SENDER_EMAIL", "onboarding@resend.dev")
if RESEND_API_KEY:
    resend.api_key = RESEND_API_KEY
JWT_ALGO = "HS256"
JWT_EXP_DAYS = 7

# Freemium quota
FREE_TRUST_CHECKS_LIMIT = 1
FREE_VIDEO_SCANS_LIMIT = 1

# Subscription package (server-side fixed)
PREMIUM_MONTHLY_USD = 9.99
DEEP_AUDIT_USD = 24.99

client = AsyncIOMotorClient(MONGO_URL)
db = client[DB_NAME]

app = FastAPI(title="Casino Spotter API")
api_router = APIRouter(prefix="/api")
security = HTTPBearer()

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


# ============= Models =============
class SignupReq(BaseModel):
    email: EmailStr
    password: str
    name: str
    signup_source: Optional[str] = None  # e.g. "reddit:near-miss", "google", "direct"


class LoginReq(BaseModel):
    email: EmailStr
    password: str


class ForgotPasswordReq(BaseModel):
    email: EmailStr
    origin_url: Optional[str] = None


class ResetPasswordReq(BaseModel):
    token: str
    password: str


class UserOut(BaseModel):
    id: str
    email: str
    name: str
    is_admin: bool = False
    is_premium: bool = False
    free_trust_checks_used: int = 0
    free_video_scans_used: int = 0
    free_trust_checks_limit: int = FREE_TRUST_CHECKS_LIMIT
    free_video_scans_limit: int = FREE_VIDEO_SCANS_LIMIT
    email_digest_subscribed: bool = True
    live_trial_used: bool = False


class LiveSessionStartReq(BaseModel):
    game_type: str = Field(default="slot")
    casino_name: Optional[str] = ""


class LiveSessionStartResp(BaseModel):
    session_id: str
    cadence_seconds: int
    max_seconds: int
    is_trial: bool


class LiveFrameReq(BaseModel):
    session_id: str
    frame_data_url: str          # data:image/jpeg;base64,...
    elapsed_seconds: int


class LiveFrameResp(BaseModel):
    frame_idx: int
    techniques_detected: List[str]
    note: str
    should_continue: bool
    remaining_seconds: int


class LiveSessionEndReq(BaseModel):
    session_id: str


class LiveFrameOut(BaseModel):
    idx: int
    elapsed_seconds: int
    techniques_detected: List[str]
    note: str
    created_at: str


class LiveSessionOut(BaseModel):
    id: str
    game_type: str
    casino_name: Optional[str]
    started_at: str
    ended_at: Optional[str]
    is_trial: bool
    max_seconds: int
    cadence_seconds: int
    frame_count: int
    techniques_aggregated: List[str]
    summary: Optional[str]
    frames: List[LiveFrameOut] = []
    public_slug: Optional[str] = None


class PublicLiveSessionOut(BaseModel):
    public_slug: str
    game_type: str
    casino_name: Optional[str]
    started_at: str
    ended_at: Optional[str]
    frame_count: int
    techniques_aggregated: List[str]
    summary: Optional[str]
    frames: List[LiveFrameOut] = []
    headline: str
    published_at: str


class DigestPrefReq(BaseModel):
    subscribed: bool


class DisputeReq(BaseModel):
    target_type: str = Field(..., pattern="^(trust|live|scam_post)$")
    target_slug: Optional[str] = None
    target_id: Optional[str] = None
    casino_name: str
    contact_email: EmailStr
    contact_name: Optional[str] = ""
    role: Optional[str] = ""  # e.g. "Compliance Officer", "Legal counsel"
    response_text: str = Field(..., min_length=20, max_length=4000)


class DisputeOut(BaseModel):
    id: str
    target_type: str
    target_slug: Optional[str]
    target_id: Optional[str]
    casino_name: str
    contact_email: str
    contact_name: Optional[str]
    role: Optional[str]
    response_text: str
    status: str  # pending | approved | rejected
    submitted_at: str
    reviewed_at: Optional[str] = None
    review_notes: Optional[str] = None


class PublicDisputeOut(BaseModel):
    """Sanitized public-facing dispute (no contact email exposed)."""
    casino_name: str
    contact_name: Optional[str]
    role: Optional[str]
    response_text: str
    approved_at: str


class DisputeModerateReq(BaseModel):
    status: str = Field(..., pattern="^(approved|rejected)$")
    review_notes: Optional[str] = ""


class AuthResp(BaseModel):
    token: str
    user: UserOut


class LegitimacyReq(BaseModel):
    casino_name: str
    casino_url: Optional[str] = None


class AnalysisOut(BaseModel):
    id: str
    user_id: str
    media_type: str
    game_type: str
    casino_name: Optional[str]
    file_name: str
    analysis: str
    techniques_detected: List[str]
    created_at: str


class LegitimacyOut(BaseModel):
    id: str
    user_id: str
    casino_name: str
    casino_url: Optional[str]
    trust_score: int
    verdict: str
    report: str
    red_flags: List[str]
    green_flags: List[str]
    slug: str
    created_at: str


class PublicLegitimacyOut(BaseModel):
    slug: str
    casino_name: str
    casino_url: Optional[str]
    trust_score: int
    verdict: str
    report: str
    red_flags: List[str]
    green_flags: List[str]
    created_at: str


def make_slug(casino_name: str) -> str:
    base = re.sub(r"[^a-z0-9]+", "-", casino_name.lower()).strip("-")[:40] or "casino"
    return f"{base}-{uuid.uuid4().hex[:6]}"


class TechniqueFAQ(BaseModel):
    q: str
    a: str


class TechniqueArticleSection(BaseModel):
    heading: str
    body: str


class TechniqueArticle(BaseModel):
    seo_title: str
    meta_description: str
    published_date: str
    updated_date: Optional[str] = None
    reading_time_min: int
    hero_subhead: str
    sections: List[TechniqueArticleSection]
    faqs: List[TechniqueFAQ]
    related_slugs: List[str] = []


class TechniqueOut(BaseModel):
    slug: str
    name: str
    category: str
    short: str
    description: str
    how_it_works: str
    how_to_spot: str
    severity: str
    article: Optional[TechniqueArticle] = None


# ============= Auth helpers =============
def hash_password(pw: str) -> str:
    return bcrypt.hashpw(pw.encode(), bcrypt.gensalt()).decode()


def verify_password(pw: str, hashed: str) -> bool:
    return bcrypt.checkpw(pw.encode(), hashed.encode())


def create_token(user_id: str) -> str:
    payload = {
        "sub": user_id,
        "exp": datetime.now(timezone.utc) + timedelta(days=JWT_EXP_DAYS),
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGO)


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        payload = jwt.decode(credentials.credentials, JWT_SECRET, algorithms=[JWT_ALGO])
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token")
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

    user = await db.users.find_one({"id": user_id}, {"_id": 0, "password": 0})
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user


ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "").lower()


def is_admin_user(user: dict) -> bool:
    return bool(user.get("is_admin")) or (ADMIN_EMAIL and user.get("email", "").lower() == ADMIN_EMAIL)


async def require_admin(user=Depends(get_current_user)):
    if not is_admin_user(user):
        raise HTTPException(status_code=403, detail="Admin only")
    return user


def build_user_out(user: dict) -> UserOut:
    return UserOut(
        id=user["id"],
        email=user["email"],
        name=user["name"],
        is_admin=is_admin_user(user),
        is_premium=bool(user.get("is_premium")),
        free_trust_checks_used=int(user.get("free_trust_checks_used", 0)),
        free_video_scans_used=int(user.get("free_video_scans_used", 0)),
        email_digest_subscribed=bool(user.get("email_digest_subscribed", True)),
        live_trial_used=bool(user.get("live_trial_used", False)),
    )


# ============= Techniques seed =============
TECHNIQUES_SEED = [
    {
        "slug": "near-miss",
        "name": "Near-Miss Manipulation",
        "category": "Slot Machines",
        "short": "Engineered close-but-no-win results to trick your brain into 'almost won' euphoria.",
        "description": "Slots are programmed to display reels that stop just one symbol short of a jackpot far more often than chance would allow. Your brain releases dopamine almost as if you won — keeping you playing.",
        "how_it_works": "Virtual reels weight specific 'blank' or 'just-off' symbols heavier on stop positions adjacent to the jackpot. The display is decoupled from true odds.",
        "how_to_spot": "Look for repeated 'one-symbol-off' jackpots, especially after a big spend. Independent jurisdictions ban this; many offshore casinos do not.",
        "severity": "high",
    },
    {
        "slug": "false-rtp",
        "name": "False / Hidden RTP",
        "category": "Slots & Table Games",
        "short": "Advertised Return-to-Player percentages that don't match the math actually running.",
        "description": "Casinos advertise RTPs (e.g. 96%) but run lower-RTP variants of the same-looking game. Some platforms even dynamically tune RTP based on player behavior.",
        "how_it_works": "Most modern slots ship with multiple RTP configurations (e.g. 88/92/96%). Operators choose the variant. Without a license requiring disclosure, you'll never know.",
        "how_to_spot": "Check the game's info screen. Compare advertised RTP vs the actual deployed version. Reputable jurisdictions (MGA, UKGC) require disclosure; offshore licenses don't.",
        "severity": "high",
    },
    {
        "slug": "slow-reveal",
        "name": "Slow Reveal & Loss Disguise",
        "category": "UX Manipulation",
        "short": "Drawn-out win animations and 'losses disguised as wins' (LDW) where you actually lost money.",
        "description": "When you bet $1 and 'win' $0.30, the game still plays a celebratory animation. The slow reveal is designed to override your loss-perception.",
        "how_it_works": "Audio cues, coin showers, and screen flashes fire on any non-zero return, even if it's a net loss for the spin.",
        "how_to_spot": "Track wagered vs returned per spin. If celebratory effects play on returns smaller than your bet, that's a deliberate LDW pattern.",
        "severity": "medium",
    },
    {
        "slug": "bonus-traps",
        "name": "Bonus Wagering Traps",
        "category": "Promotions",
        "short": "Generous deposit bonuses with hidden 30x–80x wagering requirements designed to be impossible.",
        "description": "A '$500 free!' bonus often requires you to wager that bonus 40+ times before any withdrawal. Math says the house keeps it.",
        "how_it_works": "Wagering requirements (WR) multiply bonus amount. With house edges of 2-10%, the expected loss often exceeds the bonus itself before WR is met.",
        "how_to_spot": "Always read the terms. WR above 35x is predatory. Game weighting clauses (e.g. blackjack counts only 10%) make it worse.",
        "severity": "high",
    },
    {
        "slug": "delayed-withdrawal",
        "name": "Delayed / Cancelled Withdrawals",
        "category": "Banking Practices",
        "short": "Operators stall payouts hoping you'll re-deposit and lose your winnings back.",
        "description": "Common scam pattern: KYC requests are weaponized after a big win. Verification 'reviews' take weeks. Many players give up and re-gamble.",
        "how_it_works": "Pending periods of 24-72 hours can be extended indefinitely citing 'security review'. The longer your money sits, the more likely you'll reverse and replay.",
        "how_to_spot": "Read withdrawal terms before depositing. Check independent reviewer sites for payout speed reports. Reputable casinos pay within 24h.",
        "severity": "critical",
    },
    {
        "slug": "rigged-rng",
        "name": "Unaudited or Rigged RNG",
        "category": "Game Integrity",
        "short": "Random number generators that aren't independently certified — and can be tuned against you.",
        "description": "A legitimate RNG is independently audited (eCOGRA, iTech Labs, GLI). Operators flagged by player communities often either display fake certifications or run uncertified games.",
        "how_it_works": "Server-side RNG can be biased. Without third-party audit, outcomes can favor the house arbitrarily.",
        "how_to_spot": "Look for genuine eCOGRA/iTech Labs/GLI seals — and verify on the auditor's website. Fake seals are common.",
        "severity": "critical",
    },
    {
        "slug": "live-dealer-shills",
        "name": "Live Dealer Shills & Camera Tricks",
        "category": "Live Games",
        "short": "Fake 'big winners' in chat and camera angles that conceal dealer manipulation.",
        "description": "Shill accounts post fake wins in live chat to create FOMO. Some rogue operators use sleight-of-hand dealers or pre-determined outcomes.",
        "how_it_works": "Operators control chat moderation. Camera positioning and dealer training can mask card peeks or biased shuffles.",
        "how_to_spot": "Reputable live dealer studios (Evolution, Pragmatic Live) stream from regulated facilities. Verify the studio source.",
        "severity": "medium",
    },
    {
        "slug": "vip-manipulation",
        "name": "VIP Host Manipulation",
        "category": "Behavioral Targeting",
        "short": "Personal 'hosts' who exploit loss patterns to push you back into play.",
        "description": "When you lose big, a VIP host appears with bonuses, free spins, and a sympathetic voice. Their job is to retain you, not help you.",
        "how_it_works": "Operators track your lifetime value and trigger outreach at maximum vulnerability — after big losses or signs of self-exclusion thoughts.",
        "how_to_spot": "If hosts only reach out after losses (never after wins), they're working a retention script.",
        "severity": "high",
    },
]


# ============= Routes =============
@api_router.get("/")
async def root():
    return {"message": "Casino Spotter API"}


@api_router.post("/auth/signup", response_model=AuthResp)
async def signup(req: SignupReq, request: FastAPIRequest):
    # IP-based rate limit: max 5 signups per hour per IP (anti-bot before advertising launch)
    ip = request.headers.get("x-forwarded-for", "").split(",")[0].strip() \
        or (request.client.host if request.client else "unknown")
    one_hour_ago = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
    recent_signups = await db.signup_attempts.count_documents({
        "ip": ip,
        "created_at": {"$gte": one_hour_ago},
    })
    if recent_signups >= 5:
        raise HTTPException(
            status_code=429,
            detail="Too many signups from this network in the last hour. Try again later.",
        )
    await db.signup_attempts.insert_one({
        "ip": ip,
        "email": req.email,
        "created_at": datetime.now(timezone.utc).isoformat(),
    })

    existing = await db.users.find_one({"email": req.email})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    user_id = str(uuid.uuid4())
    user_doc = {
        "id": user_id,
        "email": req.email,
        "name": req.name,
        "password": hash_password(req.password),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "signup_source": (req.signup_source or "direct")[:60],
    }
    await db.users.insert_one(user_doc)

    # Send welcome email (best-effort, fire-and-forget)
    if RESEND_API_KEY:
        try:
            asyncio.create_task(_send_onboarding_email(user_doc, "welcome"))
        except Exception:
            logger.exception("Failed to schedule welcome email")

    return AuthResp(
        token=create_token(user_id),
        user=build_user_out({**user_doc, "id": user_id}),
    )


@api_router.post("/auth/login", response_model=AuthResp)
async def login(req: LoginReq):
    user = await db.users.find_one({"email": req.email}, {"_id": 0})
    if not user or not verify_password(req.password, user["password"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    return AuthResp(
        token=create_token(user["id"]),
        user=build_user_out(user),
    )


@api_router.get("/auth/me", response_model=UserOut)
async def me(user=Depends(get_current_user)):
    return build_user_out(user)

ONBOARDING_EMAILS = {
    "welcome": {
        "subject": "Welcome to Casino Spotter — your forensic tools are ready",
        "html_template": """<h1 style="font-family:Arial;color:#00ff41;letter-spacing:.05em;">WELCOME, {name}</h1>
<p>Your account is live. You've got three free forensic tools:</p>
<ul style="line-height:1.7;">
  <li><a href="{site}/analyze" style="color:#00ff41;">1 free video scan</a> — Gemini 3 Flash analyses frame-by-frame</li>
  <li><a href="{site}/legitimacy" style="color:#00ff41;">1 free casino trust report</a> — Claude Sonnet 4.5 forensic audit</li>
  <li><a href="{site}/live" style="color:#00ff41;">60-second live capture trial</a> — real-time pattern detection</li>
</ul>
<p>If you only do one thing this week: scan one game you've been suspicious of. The first time you see "near-miss programming" flagged in a clip you uploaded yourself, you'll understand why we built this.</p>
<p style="margin-top:24px;"><a href="{site}/dashboard" style="display:inline-block;background:#00ff41;color:#000;padding:14px 22px;font-weight:700;text-decoration:none;">START SCANNING &gt;_</a></p>
<p style="color:#888;font-size:11px;margin-top:32px;">Gambling problem? Call 1-800-GAMBLER or visit BeGambleAware.org. Unsubscribe anytime in your <a href="{site}/dashboard" style="color:#888;">dashboard</a>.</p>""",
    },
    "day2": {
        "subject": "5 techniques the casinos hope you never learn about",
        "html_template": """<h1 style="font-family:Arial;color:#00ff41;letter-spacing:.05em;">{name}, the rabbit hole goes deep</h1>
<p>You signed up a couple of days ago. Here are 5 manipulation techniques every player should know:</p>
<ol style="line-height:1.8;">
  <li><a href="{site}/techniques/near-miss" style="color:#00ff41;">Near-miss programming</a></li>
  <li><a href="{site}/techniques/slow-reveal" style="color:#00ff41;">Losses disguised as wins</a></li>
  <li><a href="{site}/techniques/bonus-traps" style="color:#00ff41;">Wagering requirement math</a></li>
  <li><a href="{site}/techniques/delayed-withdrawal" style="color:#00ff41;">The KYC stall</a></li>
  <li><a href="{site}/techniques/false-rtp" style="color:#00ff41;">Hidden RTP variants</a></li>
</ol>
<p>The 4 articles above are the most-read pieces on the site. If you haven't yet, give the near-miss one a few minutes.</p>
<p style="margin-top:24px;"><a href="{site}/techniques" style="display:inline-block;background:#00ff41;color:#000;padding:14px 22px;font-weight:700;text-decoration:none;">SEE ALL TECHNIQUES &gt;_</a></p>
<p style="color:#888;font-size:11px;margin-top:32px;">Want fewer emails? <a href="{site}/dashboard" style="color:#888;">Unsubscribe in dashboard</a>.</p>""",
    },
    "day5": {
        "subject": "Unlock unlimited forensic tools",
        "html_template": """<h1 style="font-family:Arial;color:#00ff41;letter-spacing:.05em;">{name} — one more thing</h1>
<p>If you've been scanning, you've probably hit (or are close to hitting) your free-tier quota. Premium unlocks the rest:</p>
<ul style="line-height:1.8;">
  <li>Unlimited video forensic scans</li>
  <li>Unlimited casino trust reports</li>
  <li>Unlimited 3-minute live capture sessions</li>
  <li>Weekly forensic digest by email</li>
</ul>
<p><strong>$9.99/month. Cancel anytime.</strong></p>
<p>If you've already upgraded — thank you, ignore this.</p>
<p style="margin-top:24px;"><a href="{site}/pricing" style="display:inline-block;background:#00ff41;color:#000;padding:14px 22px;font-weight:700;text-decoration:none;">GO PREMIUM &gt;_</a></p>
<p style="color:#888;font-size:11px;margin-top:32px;">This is the last automated email. We don't spam.</p>""",
    },
}


async def _send_onboarding_email(user_doc: dict, kind: str):
    """Send one of the onboarding emails. Records in `email_log` so we never double-send."""
    if not RESEND_API_KEY:
        return
    if kind not in ONBOARDING_EMAILS:
        return
    already = await db.email_log.find_one({"user_id": user_doc["id"], "kind": kind})
    if already:
        return
    template = ONBOARDING_EMAILS[kind]
    site = os.environ.get("SITE_URL", "").rstrip("/") or "https://casforensics.org"
    name = (user_doc.get("name") or "operator").split("@")[0][:24]
    html = template["html_template"].format(name=name, site=site)
    try:
        await asyncio.to_thread(resend.Emails.send, {
            "from": SENDER_EMAIL,
            "to": [user_doc["email"]],
            "subject": template["subject"],
            "html": html,
        })
        await db.email_log.insert_one({
            "user_id": user_doc["id"],
            "email": user_doc["email"],
            "kind": kind,
            "sent_at": datetime.now(timezone.utc).isoformat(),
        })
        logger.info(f"[ONBOARDING] sent {kind} to {user_doc['email']}")
    except Exception as e:
        logger.exception(f"Failed to send {kind} email to {user_doc['email']}: {e}")


@api_router.post("/admin/onboarding/run")
async def admin_run_onboarding(user=Depends(get_current_user)):
    """Manually trigger day-2 / day-5 onboarding emails for eligible users. Safe to call daily.
    Idempotent thanks to the email_log dedupe in _send_onboarding_email."""
    if not is_admin_user(user):
        raise HTTPException(403, "Admin only")

    now = datetime.now(timezone.utc)
    two_days_ago = (now - timedelta(days=2)).isoformat()
    three_days_ago = (now - timedelta(days=3)).isoformat()
    five_days_ago = (now - timedelta(days=5)).isoformat()
    six_days_ago = (now - timedelta(days=6)).isoformat()

    # Day-2 cohort: signed up between 2-3 days ago, day2 email not yet sent
    day2_candidates = await db.users.find(
        {"created_at": {"$gte": three_days_ago, "$lte": two_days_ago},
         "email_digest_subscribed": {"$ne": False}},
        {"_id": 0},
    ).to_list(500)

    # Day-5 cohort: signed up between 5-6 days ago
    day5_candidates = await db.users.find(
        {"created_at": {"$gte": six_days_ago, "$lte": five_days_ago},
         "email_digest_subscribed": {"$ne": False}},
        {"_id": 0},
    ).to_list(500)

    sent = {"day2": 0, "day5": 0, "skipped": 0}
    for u in day2_candidates:
        already = await db.email_log.find_one({"user_id": u["id"], "kind": "day2"})
        if already:
            sent["skipped"] += 1
            continue
        await _send_onboarding_email(u, "day2")
        sent["day2"] += 1
    for u in day5_candidates:
        already = await db.email_log.find_one({"user_id": u["id"], "kind": "day5"})
        if already:
            sent["skipped"] += 1
            continue
        await _send_onboarding_email(u, "day5")
        sent["day5"] += 1

    return {
        "ok": True,
        "sent": sent,
        "candidates": {
            "day2": len(day2_candidates),
            "day5": len(day5_candidates),
        },
    }




def _password_reset_email(name: str, link: str) -> dict:
    safe_name = name or "operator"
    html = f"""<!doctype html>
<html><body style="margin:0;padding:0;background:#0a0a0a;font-family:'JetBrains Mono',monospace;color:#fff;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#0a0a0a;padding:40px 16px;">
    <tr><td align="center">
      <table width="560" cellpadding="0" cellspacing="0" style="background:#0d0d0d;border:1px solid rgba(0,255,65,0.25);border-radius:8px;padding:32px;">
        <tr><td>
          <div style="font-size:11px;letter-spacing:.3em;color:#00ff41;text-transform:uppercase;margin-bottom:8px;">&gt; secure terminal</div>
          <h1 style="font-family:Unbounded,Arial,sans-serif;font-size:24px;color:#fff;margin:0 0 12px;">Reset your password</h1>
          <p style="font-size:13px;line-height:1.6;color:rgba(255,255,255,0.75);margin:0 0 24px;">Hey {safe_name}, we received a request to reset the password on your Casino Spotter account. Click the button below to choose a new one. This link expires in 1 hour and can only be used once.</p>
          <a href="{link}" style="display:inline-block;background:#00ff41;color:#000;text-decoration:none;font-weight:700;letter-spacing:.15em;font-size:12px;padding:14px 22px;border-radius:4px;">RESET PASSWORD &gt;_</a>
          <p style="font-size:11px;line-height:1.6;color:rgba(255,255,255,0.5);margin:24px 0 0;">Or copy &amp; paste this link into your browser:<br/><span style="color:#00ff41;word-break:break-all;">{link}</span></p>
          <hr style="border:0;border-top:1px solid rgba(0,255,65,0.15);margin:24px 0;"/>
          <p style="font-size:11px;color:rgba(255,255,255,0.4);margin:0;">Didn't request this? You can safely ignore this email — your password won't change.</p>
        </td></tr>
      </table>
    </td></tr>
  </table>
</body></html>"""
    text = f"Reset your Casino Spotter password\n\nHey {safe_name}, use the link below to choose a new password. It expires in 1 hour and can only be used once.\n\n{link}\n\nDidn't request this? Safely ignore this email."
    return {"subject": "Reset your Casino Spotter password", "html": html, "text": text}


@api_router.post("/auth/forgot-password")
async def forgot_password(req: ForgotPasswordReq, request: FastAPIRequest):
    email_lc = req.email.lower()
    # Case-insensitive email lookup (defensive — emails are typically stored lowercase already)
    user = await db.users.find_one(
        {"email": {"$regex": f"^{re.escape(email_lc)}$", "$options": "i"}},
        {"_id": 0},
    )
    generic_resp = {"ok": True, "message": "If an account exists with that email, a reset link has been sent."}

    if not user:
        return generic_resp

    # Invalidate any outstanding reset tokens for this user
    now_iso = datetime.now(timezone.utc).isoformat()
    await db.password_resets.update_many(
        {"user_id": user["id"], "used_at": None},
        {"$set": {"used_at": now_iso}},
    )

    token = secrets.token_urlsafe(32)
    expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
    await db.password_resets.insert_one({
        "id": str(uuid.uuid4()),
        "user_id": user["id"],
        "token": token,
        "expires_at": expires_at.isoformat(),
        "used_at": None,
        "created_at": now_iso,
    })

    origin = (req.origin_url or "").rstrip("/")
    if not origin:
        origin = os.environ.get("SITE_URL", "").rstrip("/")
    if not origin:
        host = request.headers.get("x-forwarded-host") or request.url.hostname
        scheme = request.headers.get("x-forwarded-proto") or "https"
        origin = f"{scheme}://{host}" if host else ""
    reset_link = f"{origin}/reset-password?token={token}"

    email_sent = False
    email_error = None
    if RESEND_API_KEY:
        content = _password_reset_email(user.get("name", ""), reset_link)
        try:
            await asyncio.to_thread(
                resend.Emails.send,
                {
                    "from": SENDER_EMAIL,
                    "to": [user["email"]],
                    "subject": content["subject"],
                    "html": content["html"],
                    "text": content["text"],
                },
            )
            email_sent = True
        except Exception as e:
            email_error = str(e)
            logger.exception(f"Failed to send reset email to {user['email']}: {e}")

    # Always log the reset link so admin can recover it from supervisor logs even
    # when Resend domain isn't verified yet.
    logger.info(f"[PASSWORD-RESET] user={user['email']} link={reset_link}")

    resp = dict(generic_resp)
    resp["email_sent"] = email_sent
    # Surface the link in the API response ONLY when the requester is the admin
    # (so the admin can recover their own account during preview / DNS pending).
    if ADMIN_EMAIL and email_lc == ADMIN_EMAIL:
        resp["debug_link"] = reset_link
        if email_error:
            resp["debug_error"] = email_error
    return resp


@api_router.post("/auth/reset-password", response_model=AuthResp)
async def reset_password(req: ResetPasswordReq):
    if len(req.password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")

    record = await db.password_resets.find_one({"token": req.token}, {"_id": 0})
    if not record:
        raise HTTPException(status_code=400, detail="Invalid or expired reset link")
    if record.get("used_at"):
        raise HTTPException(status_code=400, detail="This reset link has already been used")
    try:
        expires_at = datetime.fromisoformat(record["expires_at"])
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid reset link")
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if datetime.now(timezone.utc) > expires_at:
        raise HTTPException(status_code=400, detail="Reset link has expired. Request a new one.")

    user = await db.users.find_one({"id": record["user_id"]}, {"_id": 0})
    if not user:
        raise HTTPException(status_code=400, detail="Account no longer exists")

    new_hash = hash_password(req.password)
    now_iso = datetime.now(timezone.utc).isoformat()
    await db.users.update_one({"id": user["id"]}, {"$set": {"password": new_hash}})
    await db.password_resets.update_one(
        {"id": record["id"]},
        {"$set": {"used_at": now_iso}},
    )
    # Invalidate any other outstanding tokens
    await db.password_resets.update_many(
        {"user_id": user["id"], "used_at": None, "id": {"$ne": record["id"]}},
        {"$set": {"used_at": now_iso}},
    )

    refreshed = await db.users.find_one({"id": user["id"]}, {"_id": 0, "password": 0})
    return AuthResp(
        token=create_token(user["id"]),
        user=build_user_out(refreshed),
    )


async def check_free_quota(user: dict, key: str, limit: int):
    """Check quota WITHOUT incrementing. Raise 402 if exhausted."""
    if user.get("is_premium") or is_admin_user(user):
        return
    if int(user.get(key, 0)) >= limit:
        raise HTTPException(
            status_code=402,
            detail="Free quota exhausted. Upgrade to Premium ($9.99/mo) for unlimited.",
        )


async def bump_free_quota(user: dict, key: str):
    """Increment quota after a successful operation. No-op for premium / admin users."""
    if user.get("is_premium") or is_admin_user(user):
        return
    await db.users.update_one({"id": user["id"]}, {"$inc": {key: 1}})


# Backwards-compat alias kept for older call sites (does check + increment)
async def consume_free_quota(user: dict, key: str, limit: int):
    await check_free_quota(user, key, limit)
    await bump_free_quota(user, key)


@api_router.get("/stats/public")
async def public_stats():
    casinos_analyzed = await db.legitimacy_reports.count_documents({})
    games_scanned = await db.analyses.count_documents({})
    scam_reports = await db.scam_posts.count_documents({})
    users = await db.users.count_documents({})
    cutoff = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
    scams_today = await db.scam_posts.count_documents({"created_at": {"$gte": cutoff}})
    return {
        "casinos_analyzed": casinos_analyzed,
        "games_scanned": games_scanned,
        "scam_reports": scam_reports,
        "scams_today": scams_today,
        "users": users,
        "techniques_documented": len(TECHNIQUES_SEED),
    }


@api_router.get("/activity/recent")
async def recent_activity(limit: int = 8):
    events = []
    async for d in db.legitimacy_reports.find({}, {"_id": 0, "casino_name": 1, "trust_score": 1, "created_at": 1, "slug": 1}).sort("created_at", -1).limit(limit):
        events.append({"type": "trust_check", "label": f"{d.get('casino_name','?')} trust check", "detail": f"{d.get('trust_score','?')}/100", "slug": d.get("slug"), "created_at": d.get("created_at")})
    async for d in db.scam_posts.find({}, {"_id": 0, "casino_name": 1, "title": 1, "created_at": 1, "id": 1}).sort("created_at", -1).limit(limit):
        events.append({"type": "scam_report", "label": f"Scam report: {d.get('casino_name','?')}", "detail": d.get("title", "")[:60], "slug": None, "post_id": d.get("id"), "created_at": d.get("created_at")})
    async for d in db.analyses.find({}, {"_id": 0, "casino_name": 1, "game_type": 1, "created_at": 1, "techniques_detected": 1}).sort("created_at", -1).limit(limit):
        techs = d.get("techniques_detected") or []
        events.append({"type": "ai_scan", "label": f"{d.get('game_type','?')} scan", "detail": (techs[0] if techs else "analyzed"), "slug": None, "created_at": d.get("created_at")})
    events.sort(key=lambda e: e.get("created_at", ""), reverse=True)
    return events[:limit]


def _technique_with_article(t: dict) -> dict:
    """Merge the long-form article (if exists) into the technique dict."""
    article = TECHNIQUE_ARTICLES.get(t["slug"])
    if article:
        return {**t, "article": article}
    return t


@api_router.get("/techniques", response_model=List[TechniqueOut])
async def list_techniques():
    return [TechniqueOut(**_technique_with_article(t)) for t in TECHNIQUES_SEED]


@api_router.get("/techniques/{slug}", response_model=TechniqueOut)
async def get_technique(slug: str):
    for t in TECHNIQUES_SEED:
        if t["slug"] == slug:
            return TechniqueOut(**_technique_with_article(t))
    raise HTTPException(404, "Technique not found")


@api_router.post("/analysis/upload", response_model=AnalysisOut)
async def analyze_media(
    file: UploadFile = File(...),
    game_type: str = Form(...),
    casino_name: str = Form(""),
    user=Depends(get_current_user),
):
    await check_free_quota(user, "free_video_scans_used", FREE_VIDEO_SCANS_LIMIT)
    ext = (file.filename or "").split(".")[-1].lower()
    if ext not in ("mp4", "mov", "webm", "png", "jpg", "jpeg", "gif", "webp"):
        raise HTTPException(400, "Unsupported file type")

    is_video = ext in ("mp4", "mov", "webm")
    media_type = "video" if is_video else "image"

    file_id = str(uuid.uuid4())
    save_path = UPLOAD_DIR / f"{file_id}.{ext}"
    with save_path.open("wb") as f:
        shutil.copyfileobj(file.file, f)

    mime_map = {
        "mp4": "video/mp4",
        "mov": "video/quicktime",
        "webm": "video/webm",
        "png": "image/png",
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "gif": "image/gif",
        "webp": "image/webp",
    }

    system_msg = (
        "You are an expert in casino game integrity, behavioral psychology, and online gambling forensics. "
        "Analyze the supplied media (video or screenshot) from an online casino game. "
        "Identify ANY manipulation, dark-pattern, or potentially deceptive technique the operator may be using "
        "(near-miss programming, slow reveal, loss-disguised-as-wins, false RTP, rigged RNG, shill chat, "
        "delayed withdrawals, bonus traps, etc). "
        "Respond in this exact format:\n"
        "VERDICT: <one sentence summary>\n"
        "TECHNIQUES_DETECTED: <comma-separated short slugs>\n"
        "DETAILED_ANALYSIS: <3-6 paragraphs explaining what you see, the psychology involved, "
        "and why it's manipulative. Use plain language for a non-expert.>\n"
        "PROTECT_YOURSELF: <3 concrete bullet tips>"
    )

    try:
        chat = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=f"analysis-{file_id}",
            system_message=system_msg,
        ).with_model("gemini", "gemini-3-flash-preview")

        file_content = FileContentWithMimeType(
            file_path=str(save_path),
            mime_type=mime_map[ext],
        )
        prompt = (
            f"Game type: {game_type}\n"
            f"Casino: {casino_name or 'unspecified'}\n\n"
            f"Analyze this {media_type} and explain what manipulation techniques (if any) "
            f"the casino is using on this player."
        )
        response = await chat.send_message(
            UserMessage(text=prompt, file_contents=[file_content])
        )
        response_text = str(response)
    except Exception as e:
        logger.exception("Gemini analysis failed")
        raise HTTPException(500, f"Analysis failed: {str(e)}")

    techniques = []
    for line in response_text.split("\n"):
        if line.upper().startswith("TECHNIQUES_DETECTED:"):
            raw = line.split(":", 1)[1].strip()
            techniques = [t.strip() for t in raw.split(",") if t.strip()]
            break

    record_id = str(uuid.uuid4())
    record = {
        "id": record_id,
        "user_id": user["id"],
        "media_type": media_type,
        "game_type": game_type,
        "casino_name": casino_name or None,
        "file_name": file.filename or f"{file_id}.{ext}",
        "file_path": f"{file_id}.{ext}",
        "analysis": response_text,
        "techniques_detected": techniques,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.analyses.insert_one(record)
    await bump_free_quota(user, "free_video_scans_used")
    return AnalysisOut(**{k: v for k, v in record.items() if k != "file_path"})


@api_router.get("/analysis/history", response_model=List[AnalysisOut])
async def history(user=Depends(get_current_user)):
    docs = await db.analyses.find(
        {"user_id": user["id"]}, {"_id": 0, "file_path": 0}
    ).sort("created_at", -1).to_list(200)
    return [AnalysisOut(**d) for d in docs]


@api_router.get("/analysis/{analysis_id}", response_model=AnalysisOut)
async def get_analysis(analysis_id: str, user=Depends(get_current_user)):
    doc = await db.analyses.find_one(
        {"id": analysis_id, "user_id": user["id"]},
        {"_id": 0, "file_path": 0},
    )
    if not doc:
        raise HTTPException(404, "Not found")
    return AnalysisOut(**doc)


# ============= Live screen-capture mode =============
LIVE_CADENCE_SECONDS = 15
LIVE_PREMIUM_MAX_SECONDS = 180          # 3 min hard cap
LIVE_TRIAL_MAX_SECONDS = 60             # free 60s trial (one per user)


@api_router.post("/live/session/start", response_model=LiveSessionStartResp)
async def live_session_start(req: LiveSessionStartReq, user=Depends(get_current_user)):
    is_unlimited = bool(user.get("is_premium")) or is_admin_user(user)
    if not is_unlimited and user.get("live_trial_used"):
        raise HTTPException(
            status_code=402,
            detail="Free 60s live-mode trial already used. Upgrade to Premium ($9.99/mo) for unlimited 3-min sessions.",
        )

    is_trial = not is_unlimited
    max_seconds = LIVE_TRIAL_MAX_SECONDS if is_trial else LIVE_PREMIUM_MAX_SECONDS
    session_id = str(uuid.uuid4())
    await db.live_sessions.insert_one({
        "id": session_id,
        "user_id": user["id"],
        "game_type": req.game_type,
        "casino_name": (req.casino_name or "").strip() or None,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "ended_at": None,
        "is_trial": is_trial,
        "max_seconds": max_seconds,
        "cadence_seconds": LIVE_CADENCE_SECONDS,
        "frames": [],
        "techniques_aggregated": [],
        "summary": None,
    })
    # NOTE: We deliberately do NOT flip live_trial_used here. We flip it only
    # after the first successful frame is analyzed (see /live/frame). This
    # prevents a cancelled OS share dialog from burning the user's only trial.

    return LiveSessionStartResp(
        session_id=session_id,
        cadence_seconds=LIVE_CADENCE_SECONDS,
        max_seconds=max_seconds,
        is_trial=is_trial,
    )


def _strip_data_url(data_url: str) -> tuple[str, bytes]:
    """Returns (ext, raw_bytes)."""
    if not data_url.startswith("data:"):
        raise HTTPException(400, "Invalid frame data URL")
    try:
        header, b64 = data_url.split(",", 1)
        # header like: data:image/jpeg;base64
        mime = header.split(";")[0].replace("data:", "")
        ext = "jpg" if "jpeg" in mime else mime.split("/")[-1]
        raw = base64.b64decode(b64)
    except Exception:
        raise HTTPException(400, "Could not decode frame")
    if len(raw) > 4 * 1024 * 1024:  # 4 MB per frame ceiling
        raise HTTPException(400, "Frame too large (max 4MB)")
    return ext, raw


@api_router.post("/live/frame", response_model=LiveFrameResp)
async def live_frame(req: LiveFrameReq, user=Depends(get_current_user)):
    session = await db.live_sessions.find_one(
        {"id": req.session_id, "user_id": user["id"]}, {"_id": 0}
    )
    if not session:
        raise HTTPException(404, "Session not found")
    if session.get("ended_at"):
        raise HTTPException(400, "Session already ended")
    max_seconds = int(session.get("max_seconds", LIVE_PREMIUM_MAX_SECONDS))
    if int(req.elapsed_seconds) >= max_seconds:
        raise HTTPException(400, "Session time limit reached")

    ext, raw = _strip_data_url(req.frame_data_url)
    file_id = str(uuid.uuid4())
    save_path = UPLOAD_DIR / f"live-{file_id}.{ext}"
    save_path.write_bytes(raw)

    mime = "image/jpeg" if ext in ("jpg", "jpeg") else f"image/{ext}"
    system_msg = (
        "You are a real-time casino-game forensic analyst observing a player's screen frame. "
        "Identify any visible manipulation, dark pattern, or psychological trick the operator "
        "is using IN THIS SPECIFIC FRAME (near-miss programming, loss-disguised-as-win, "
        "slow-reveal, false RTP display, fake live-dealer shills, push-notification urgency, "
        "bonus traps, etc). Be terse — this analysis fires every 15 seconds.\n\n"
        "Respond EXACTLY in this format on two lines and nothing else:\n"
        "TECHNIQUES: <comma-separated short slugs, or 'none'>\n"
        "NOTE: <one sentence (max 25 words) explaining what you observed>"
    )

    techniques: list = []
    note = ""
    try:
        chat = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=f"live-{req.session_id}-{file_id}",
            system_message=system_msg,
        ).with_model("gemini", "gemini-3-flash-preview")
        file_content = FileContentWithMimeType(file_path=str(save_path), mime_type=mime)
        prompt = (
            f"Game: {session.get('game_type','slot')} | "
            f"Casino: {session.get('casino_name') or 'unknown'} | "
            f"Elapsed: {req.elapsed_seconds}s. Analyze this single live frame."
        )
        response = await chat.send_message(UserMessage(text=prompt, file_contents=[file_content]))
        response_text = str(response)
        for line in response_text.split("\n"):
            stripped = line.strip()
            if stripped.upper().startswith("TECHNIQUES:"):
                raw_t = stripped.split(":", 1)[1].strip()
                if raw_t and raw_t.lower() != "none":
                    techniques = [t.strip() for t in raw_t.split(",") if t.strip()]
            elif stripped.upper().startswith("NOTE:"):
                note = stripped.split(":", 1)[1].strip()
    except Exception as e:
        logger.exception("Live frame analysis failed")
        note = f"frame skipped: {str(e)[:80]}"
    finally:
        try:
            save_path.unlink(missing_ok=True)
        except Exception:
            pass

    frame_idx = len(session.get("frames", []))
    frame_doc = {
        "idx": frame_idx,
        "elapsed_seconds": int(req.elapsed_seconds),
        "techniques_detected": techniques,
        "note": note,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    # Merge techniques into aggregated set
    aggregated = set(session.get("techniques_aggregated", []))
    aggregated.update(techniques)

    await db.live_sessions.update_one(
        {"id": req.session_id},
        {
            "$push": {"frames": frame_doc},
            "$set": {"techniques_aggregated": sorted(aggregated)},
        },
    )

    # If this is a trial session AND the first successful frame, only NOW burn
    # the user's trial — so cancelling the OS share dialog doesn't waste it.
    if session.get("is_trial") and frame_idx == 0 and not user.get("live_trial_used"):
        await db.users.update_one(
            {"id": user["id"]},
            {"$set": {"live_trial_used": True}},
        )

    remaining = max(0, max_seconds - int(req.elapsed_seconds) - LIVE_CADENCE_SECONDS)
    return LiveFrameResp(
        frame_idx=frame_idx,
        techniques_detected=techniques,
        note=note,
        should_continue=remaining > 0,
        remaining_seconds=remaining,
    )


@api_router.post("/live/session/end", response_model=LiveSessionOut)
async def live_session_end(req: LiveSessionEndReq, user=Depends(get_current_user)):
    session = await db.live_sessions.find_one(
        {"id": req.session_id, "user_id": user["id"]}, {"_id": 0}
    )
    if not session:
        raise HTTPException(404, "Session not found")

    if not session.get("ended_at"):
        # Generate a brief summary from the frames
        frames = session.get("frames", [])
        aggregated = session.get("techniques_aggregated", [])
        summary = ""
        if frames:
            try:
                lines = "\n".join(
                    f"- t={f['elapsed_seconds']}s: {', '.join(f.get('techniques_detected') or ['no-flag'])} — {f.get('note','')}"
                    for f in frames
                )
                summary_prompt = (
                    f"You observed {len(frames)} live frames from a {session.get('game_type')} session "
                    f"on casino '{session.get('casino_name') or 'unknown'}'. Per-frame notes:\n{lines}\n\n"
                    "Write a 4-6 sentence editorial summary in plain English for the player: "
                    "what manipulation patterns showed up over the session, what to watch for next time, "
                    "and one concrete protective action. Do NOT use markdown."
                )
                chat = LlmChat(
                    api_key=EMERGENT_LLM_KEY,
                    session_id=f"live-summary-{req.session_id}",
                    system_message="You are a casino-forensics analyst summarizing a live observation session.",
                ).with_model("gemini", "gemini-3-flash-preview")
                summary = str(await chat.send_message(UserMessage(text=summary_prompt)))
            except Exception:
                logger.exception("Live summary failed")
                summary = (
                    f"Session observed {len(frames)} frames. "
                    f"Techniques flagged: {', '.join(aggregated) if aggregated else 'none'}."
                )
        else:
            summary = "Session ended before any frames were analyzed."

        await db.live_sessions.update_one(
            {"id": req.session_id},
            {"$set": {
                "ended_at": datetime.now(timezone.utc).isoformat(),
                "summary": summary,
            }},
        )
        session["ended_at"] = datetime.now(timezone.utc).isoformat()
        session["summary"] = summary

    return _live_session_to_out(session, include_frames=True)


def _live_session_to_out(d: dict, include_frames: bool = True) -> LiveSessionOut:
    return LiveSessionOut(
        id=d["id"],
        game_type=d.get("game_type", "slot"),
        casino_name=d.get("casino_name"),
        started_at=d["started_at"],
        ended_at=d.get("ended_at"),
        is_trial=bool(d.get("is_trial")),
        max_seconds=int(d.get("max_seconds", LIVE_PREMIUM_MAX_SECONDS)),
        cadence_seconds=int(d.get("cadence_seconds", LIVE_CADENCE_SECONDS)),
        frame_count=len(d.get("frames", [])),
        techniques_aggregated=d.get("techniques_aggregated", []),
        summary=d.get("summary"),
        frames=[LiveFrameOut(**f) for f in d.get("frames", [])] if include_frames else [],
        public_slug=d.get("public_slug"),
    )


def _build_live_headline(d: dict) -> str:
    techs = d.get("techniques_aggregated") or []
    casino = d.get("casino_name") or "an unnamed casino"
    game = d.get("game_type") or "game"
    if not techs:
        return f"{casino}: {game} session — no manipulation patterns flagged"
    head = ", ".join(techs[:3])
    suffix = f" (+{len(techs) - 3} more)" if len(techs) > 3 else ""
    return f"{casino}: live {game} capture flagged {head}{suffix}"


@api_router.get("/live/sessions", response_model=List[LiveSessionOut])
async def live_session_list(user=Depends(get_current_user)):
    docs = await db.live_sessions.find(
        {"user_id": user["id"]}, {"_id": 0}
    ).sort("started_at", -1).to_list(100)
    return [_live_session_to_out(d, include_frames=False) for d in docs]


@api_router.get("/live/session/{session_id}", response_model=LiveSessionOut)
async def live_session_detail(session_id: str, user=Depends(get_current_user)):
    d = await db.live_sessions.find_one({"id": session_id, "user_id": user["id"]}, {"_id": 0})
    if not d:
        raise HTTPException(404, "Session not found")
    return _live_session_to_out(d, include_frames=True)


@api_router.post("/live/session/{session_id}/publish", response_model=LiveSessionOut)
async def live_session_publish(session_id: str, user=Depends(get_current_user)):
    d = await db.live_sessions.find_one({"id": session_id, "user_id": user["id"]}, {"_id": 0})
    if not d:
        raise HTTPException(404, "Session not found")
    if not (d.get("techniques_aggregated") or []):
        raise HTTPException(
            status_code=400,
            detail="Only sessions with at least one flagged technique can be promoted to a public report.",
        )
    if d.get("public_slug"):
        # Idempotent — already published, just return as-is
        return _live_session_to_out(d, include_frames=True)

    slug_base = d.get("casino_name") or d.get("game_type") or "live-session"
    public_slug = make_slug(f"live-{slug_base}")
    headline = _build_live_headline(d)
    now_iso = datetime.now(timezone.utc).isoformat()

    await db.live_sessions.update_one(
        {"id": session_id},
        {"$set": {
            "public_slug": public_slug,
            "headline": headline,
            "published_at": now_iso,
        }},
    )
    d["public_slug"] = public_slug
    d["headline"] = headline
    d["published_at"] = now_iso
    return _live_session_to_out(d, include_frames=True)


@api_router.post("/live/session/{session_id}/unpublish", response_model=LiveSessionOut)
async def live_session_unpublish(session_id: str, user=Depends(get_current_user)):
    d = await db.live_sessions.find_one({"id": session_id, "user_id": user["id"]}, {"_id": 0})
    if not d:
        raise HTTPException(404, "Session not found")
    await db.live_sessions.update_one(
        {"id": session_id},
        {"$unset": {"public_slug": "", "headline": "", "published_at": ""}},
    )
    d.pop("public_slug", None)
    return _live_session_to_out(d, include_frames=True)


@api_router.get("/live/public", response_model=List[PublicLiveSessionOut])
async def list_public_live_sessions(limit: int = 20):
    docs = await db.live_sessions.find(
        {"public_slug": {"$exists": True, "$ne": None}},
        {"_id": 0, "user_id": 0, "id": 0, "is_trial": 0, "max_seconds": 0, "cadence_seconds": 0},
    ).sort("published_at", -1).to_list(min(limit, 100))
    out = []
    for d in docs:
        out.append(PublicLiveSessionOut(
            public_slug=d["public_slug"],
            game_type=d.get("game_type", "slot"),
            casino_name=d.get("casino_name"),
            started_at=d["started_at"],
            ended_at=d.get("ended_at"),
            frame_count=len(d.get("frames", [])),
            techniques_aggregated=d.get("techniques_aggregated", []),
            summary=d.get("summary"),
            frames=[LiveFrameOut(**f) for f in d.get("frames", [])],
            headline=d.get("headline") or _build_live_headline(d),
            published_at=d.get("published_at") or d["started_at"],
        ))
    return out


@api_router.get("/live/public/{slug}", response_model=PublicLiveSessionOut)
async def get_public_live_session(slug: str):
    d = await db.live_sessions.find_one(
        {"public_slug": slug},
        {"_id": 0, "user_id": 0, "id": 0, "is_trial": 0, "max_seconds": 0, "cadence_seconds": 0},
    )
    if not d:
        raise HTTPException(404, "Public live report not found")
    return PublicLiveSessionOut(
        public_slug=d["public_slug"],
        game_type=d.get("game_type", "slot"),
        casino_name=d.get("casino_name"),
        started_at=d["started_at"],
        ended_at=d.get("ended_at"),
        frame_count=len(d.get("frames", [])),
        techniques_aggregated=d.get("techniques_aggregated", []),
        summary=d.get("summary"),
        frames=[LiveFrameOut(**f) for f in d.get("frames", [])],
        headline=d.get("headline") or _build_live_headline(d),
        published_at=d.get("published_at") or d["started_at"],
    )



# ============= Right-of-response (Disputes) =============
async def _validate_dispute_target(target_type: str, slug: Optional[str], target_id: Optional[str]):
    """Return True if the target actually exists. Prevents spam disputes on non-existent reports."""
    if target_type == "trust":
        if not slug:
            return False
        d = await db.legitimacy_reports.find_one({"slug": slug, "public": True}, {"_id": 0, "id": 1})
        return d is not None
    if target_type == "live":
        if not slug:
            return False
        d = await db.live_sessions.find_one({"public_slug": slug}, {"_id": 0, "id": 1})
        return d is not None
    if target_type == "scam_post":
        if not target_id:
            return False
        d = await db.scams.find_one({"id": target_id}, {"_id": 0, "id": 1})
        return d is not None
    return False


@api_router.post("/disputes", response_model=DisputeOut)
async def submit_dispute(req: DisputeReq, request: FastAPIRequest):
    """Public endpoint — anyone can file a right-of-response. Goes to admin moderation queue."""
    ok = await _validate_dispute_target(req.target_type, req.target_slug, req.target_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Referenced report does not exist or is not public")

    # Light per-email + per-IP rate limit (max 3 pending per email in last 24h)
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
    recent_count = await db.disputes.count_documents({
        "contact_email": req.contact_email.lower(),
        "submitted_at": {"$gte": cutoff},
    })
    if recent_count >= 3:
        raise HTTPException(
            status_code=429,
            detail="Too many disputes submitted from this email in the last 24 hours.",
        )

    dispute_id = str(uuid.uuid4())
    doc = {
        "id": dispute_id,
        "target_type": req.target_type,
        "target_slug": req.target_slug,
        "target_id": req.target_id,
        "casino_name": req.casino_name.strip(),
        "contact_email": req.contact_email.lower(),
        "contact_name": (req.contact_name or "").strip(),
        "role": (req.role or "").strip(),
        "response_text": req.response_text.strip(),
        "status": "pending",
        "submitted_at": datetime.now(timezone.utc).isoformat(),
        "reviewed_at": None,
        "review_notes": None,
        "submitter_ip": request.headers.get("x-forwarded-for", "").split(",")[0].strip()
            or (request.client.host if request.client else ""),
    }
    await db.disputes.insert_one(doc)

    # Notify admin via Resend (best-effort)
    if RESEND_API_KEY and ADMIN_EMAIL:
        try:
            html = f"""<p>New right-of-response dispute filed.</p>
<ul>
  <li><strong>Type:</strong> {req.target_type}</li>
  <li><strong>Target:</strong> {req.target_slug or req.target_id}</li>
  <li><strong>Casino:</strong> {req.casino_name}</li>
  <li><strong>From:</strong> {req.contact_name or '—'} &lt;{req.contact_email}&gt; ({req.role or 'no role given'})</li>
</ul>
<blockquote style="border-left:3px solid #00ff41;padding-left:12px;color:#555;">{req.response_text}</blockquote>
<p>Moderate at /admin/disputes</p>"""
            await asyncio.to_thread(resend.Emails.send, {
                "from": SENDER_EMAIL,
                "to": [ADMIN_EMAIL],
                "subject": f"[Dispute] {req.casino_name} — {req.target_type}",
                "html": html,
            })
        except Exception:
            logger.exception("Failed to email admin about dispute")

    return DisputeOut(**{k: v for k, v in doc.items() if k != "submitter_ip"})


@api_router.get("/disputes/public/{target_type}/{slug}", response_model=List[PublicDisputeOut])
async def list_public_disputes(target_type: str, slug: str):
    """Returns APPROVED disputes for a given public report (operator responses)."""
    if target_type not in ("trust", "live"):
        return []
    docs = await db.disputes.find(
        {"target_type": target_type, "target_slug": slug, "status": "approved"},
        {"_id": 0, "contact_email": 0, "submitter_ip": 0},
    ).sort("reviewed_at", 1).to_list(20)
    return [
        PublicDisputeOut(
            casino_name=d["casino_name"],
            contact_name=d.get("contact_name") or None,
            role=d.get("role") or None,
            response_text=d["response_text"],
            approved_at=d.get("reviewed_at") or d["submitted_at"],
        )
        for d in docs
    ]


@api_router.get("/admin/disputes", response_model=List[DisputeOut])
async def admin_list_disputes(status_filter: Optional[str] = None, user=Depends(get_current_user)):
    if not is_admin_user(user):
        raise HTTPException(403, "Admin only")
    q = {}
    if status_filter in ("pending", "approved", "rejected"):
        q["status"] = status_filter
    docs = await db.disputes.find(q, {"_id": 0, "submitter_ip": 0}).sort("submitted_at", -1).to_list(200)
    return [DisputeOut(**d) for d in docs]


@api_router.get("/admin/signup-sources")
async def admin_signup_sources(user=Depends(get_current_user)):
    """Attribution analytics — total signups grouped by source."""
    if not is_admin_user(user):
        raise HTTPException(403, "Admin only")
    pipeline = [
        {"$group": {
            "_id": {"$ifNull": ["$signup_source", "direct"]},
            "count": {"$sum": 1},
            "premium_count": {"$sum": {"$cond": [{"$eq": ["$is_premium", True]}, 1, 0]}},
        }},
        {"$sort": {"count": -1}},
    ]
    rows = [r async for r in db.users.aggregate(pipeline)]
    return [
        {"source": r["_id"], "signups": r["count"], "premium_converts": r.get("premium_count", 0)}
        for r in rows
    ]


# Estimated cost (USD) per LLM call type. Used by the admin dashboard for burn-rate alerts.
LLM_COST_ESTIMATES = {
    "video_analysis": 0.18,       # Gemini 3 Flash with ~30-90s video upload
    "legitimacy_report": 0.06,    # Claude Sonnet 4.5 ~2k tokens
    "live_frame": 0.012,          # Gemini 3 Flash single image
    "live_summary": 0.02,         # Gemini 3 Flash text-only summary
    "video_compare": 0.20,        # Gemini compare endpoint
}


@api_router.get("/admin/dashboard")
async def admin_dashboard(user=Depends(get_current_user)):
    """One-call snapshot of everything an operator needs: signups, conversions,
    LLM burn estimates, MRR, pending moderation queues. Read-only."""
    if not is_admin_user(user):
        raise HTTPException(403, "Admin only")

    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
    seven_days_ago = (now - timedelta(days=7)).isoformat()
    thirty_days_ago = (now - timedelta(days=30)).isoformat()

    # --- User counts ---
    users_total = await db.users.count_documents({})
    users_premium = await db.users.count_documents({"is_premium": True})
    users_today = await db.users.count_documents({"created_at": {"$gte": today_start}})
    users_7d = await db.users.count_documents({"created_at": {"$gte": seven_days_ago}})

    # --- MRR (Premium subscribers × $9.99) ---
    mrr = round(users_premium * 9.99, 2)
    arr = round(mrr * 12, 2)

    # --- LLM usage today and 7d ---
    analyses_today = await db.analyses.count_documents({"created_at": {"$gte": today_start}})
    analyses_7d = await db.analyses.count_documents({"created_at": {"$gte": seven_days_ago}})
    legitimacy_today = await db.legitimacy_reports.count_documents(
        {"created_at": {"$gte": today_start}, "served_from_cache": {"$ne": True}}
    )
    legitimacy_7d = await db.legitimacy_reports.count_documents(
        {"created_at": {"$gte": seven_days_ago}, "served_from_cache": {"$ne": True}}
    )
    legitimacy_cache_hits_7d = await db.legitimacy_reports.count_documents(
        {"created_at": {"$gte": seven_days_ago}, "served_from_cache": True}
    )

    # Live sessions — count frames + summary calls
    live_today_pipeline = [
        {"$match": {"started_at": {"$gte": today_start}}},
        {"$project": {"frame_count": {"$size": {"$ifNull": ["$frames", []]}}, "ended_at": 1}},
        {"$group": {
            "_id": None,
            "frame_calls": {"$sum": "$frame_count"},
            "summary_calls": {"$sum": {"$cond": [{"$ne": ["$ended_at", None]}, 1, 0]}},
        }},
    ]
    live_today_rows = [r async for r in db.live_sessions.aggregate(live_today_pipeline)]
    live_today = live_today_rows[0] if live_today_rows else {"frame_calls": 0, "summary_calls": 0}

    live_7d_pipeline = [
        {"$match": {"started_at": {"$gte": seven_days_ago}}},
        {"$project": {"frame_count": {"$size": {"$ifNull": ["$frames", []]}}, "ended_at": 1}},
        {"$group": {
            "_id": None,
            "frame_calls": {"$sum": "$frame_count"},
            "summary_calls": {"$sum": {"$cond": [{"$ne": ["$ended_at", None]}, 1, 0]}},
        }},
    ]
    live_7d_rows = [r async for r in db.live_sessions.aggregate(live_7d_pipeline)]
    live_7d = live_7d_rows[0] if live_7d_rows else {"frame_calls": 0, "summary_calls": 0}

    cost_today = round(
        analyses_today * LLM_COST_ESTIMATES["video_analysis"]
        + legitimacy_today * LLM_COST_ESTIMATES["legitimacy_report"]
        + live_today["frame_calls"] * LLM_COST_ESTIMATES["live_frame"]
        + live_today["summary_calls"] * LLM_COST_ESTIMATES["live_summary"],
        2,
    )
    cost_7d = round(
        analyses_7d * LLM_COST_ESTIMATES["video_analysis"]
        + legitimacy_7d * LLM_COST_ESTIMATES["legitimacy_report"]
        + live_7d["frame_calls"] * LLM_COST_ESTIMATES["live_frame"]
        + live_7d["summary_calls"] * LLM_COST_ESTIMATES["live_summary"],
        2,
    )
    cache_savings_7d = round(legitimacy_cache_hits_7d * LLM_COST_ESTIMATES["legitimacy_report"], 2)

    # --- Moderation queues ---
    pending_disputes = await db.disputes.count_documents({"status": "pending"})
    pending_verifieds = await db.verified_applications.count_documents({"status": "pending"})

    # --- Recent activity ---
    recent_scams = await db.scam_posts.find({}, {"_id": 0}).sort("created_at", -1).to_list(5)
    recent_signups = await db.users.find(
        {}, {"_id": 0, "id": 1, "email": 1, "created_at": 1, "signup_source": 1, "is_premium": 1}
    ).sort("created_at", -1).to_list(8)

    # --- Top signup sources (last 30d) ---
    source_pipeline = [
        {"$match": {"created_at": {"$gte": thirty_days_ago}}},
        {"$group": {
            "_id": {"$ifNull": ["$signup_source", "direct"]},
            "count": {"$sum": 1},
            "premium": {"$sum": {"$cond": [{"$eq": ["$is_premium", True]}, 1, 0]}},
        }},
        {"$sort": {"count": -1}},
        {"$limit": 8},
    ]
    sources = [r async for r in db.users.aggregate(source_pipeline)]
    sources_out = [
        {"source": s["_id"], "signups_30d": s["count"], "premium_30d": s.get("premium", 0)}
        for s in sources
    ]

    return {
        "users": {
            "total": users_total,
            "premium": users_premium,
            "today": users_today,
            "seven_days": users_7d,
        },
        "revenue": {
            "mrr_usd": mrr,
            "arr_usd": arr,
            "premium_count": users_premium,
        },
        "llm_costs": {
            "estimated_today_usd": cost_today,
            "estimated_7d_usd": cost_7d,
            "cache_savings_7d_usd": cache_savings_7d,
            "breakdown_today": {
                "video_analysis_calls": analyses_today,
                "legitimacy_report_calls": legitimacy_today,
                "live_frame_calls": live_today["frame_calls"],
                "live_summary_calls": live_today["summary_calls"],
            },
            "breakdown_7d": {
                "video_analysis_calls": analyses_7d,
                "legitimacy_report_calls": legitimacy_7d,
                "legitimacy_cache_hits": legitimacy_cache_hits_7d,
                "live_frame_calls": live_7d["frame_calls"],
                "live_summary_calls": live_7d["summary_calls"],
            },
        },
        "moderation": {
            "pending_disputes": pending_disputes,
            "pending_verified_apps": pending_verifieds,
        },
        "recent_signups": recent_signups,
        "recent_scams": recent_scams,
        "top_sources_30d": sources_out,
    }


@api_router.post("/admin/disputes/{dispute_id}/moderate", response_model=DisputeOut)
async def admin_moderate_dispute(dispute_id: str, req: DisputeModerateReq, user=Depends(get_current_user)):
    if not is_admin_user(user):
        raise HTTPException(403, "Admin only")
    d = await db.disputes.find_one({"id": dispute_id}, {"_id": 0})
    if not d:
        raise HTTPException(404, "Dispute not found")
    now_iso = datetime.now(timezone.utc).isoformat()
    await db.disputes.update_one(
        {"id": dispute_id},
        {"$set": {
            "status": req.status,
            "reviewed_at": now_iso,
            "review_notes": req.review_notes or "",
        }},
    )
    d.update({"status": req.status, "reviewed_at": now_iso, "review_notes": req.review_notes or ""})
    d.pop("submitter_ip", None)
    return DisputeOut(**d)


# Known scam/legit casinos lookup data
KNOWN_CASINOS = {
    "scams": [
        "lucky31", "winorama-old", "casinopanda-rogue", "redbet-rogue",
        "fortunelounge-2018", "freespin", "captainjack-2010",
    ],
    "reputable": [
        "bet365", "william hill", "betmgm", "draftkings", "caesars",
        "leovegas", "casumo", "mr green", "unibet", "pokerstars casino",
    ],
}


@api_router.post("/legitimacy/research", response_model=LegitimacyOut)
async def research_casino(req: LegitimacyReq, user=Depends(get_current_user)):
    await check_free_quota(user, "free_trust_checks_used", FREE_TRUST_CHECKS_LIMIT)
    name_lower = req.casino_name.lower().strip()

    # ============ LLM RESULT CACHE (cost control before advertising) ============
    # Reuse a recent identical-query report for 24h. Saves $0.05-$0.10 per cache hit.
    # Cached responses are also surfaced to the requester via their own report record.
    cache_cutoff = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
    cached = await db.legitimacy_reports.find_one(
        {
            "casino_name_lower": name_lower,
            "created_at": {"$gte": cache_cutoff},
            "is_cache_seed": True,  # only canonical, ad-safe entries
        },
        {"_id": 0},
        sort=[("created_at", -1)],
    )
    if cached:
        # Clone the cached payload but reassign ownership + bump quota for the new user
        new_id = str(uuid.uuid4())
        new_slug = make_slug(req.casino_name) + "-" + new_id[:6]
        clone = {
            **cached,
            "id": new_id,
            "slug": new_slug,
            "user_id": user["id"],
            "created_at": datetime.now(timezone.utc).isoformat(),
            "public": False,
            "is_cache_seed": False,
            "served_from_cache": True,
        }
        await db.legitimacy_reports.insert_one(clone)
        await bump_free_quota(user, "free_trust_checks_used")
        return LegitimacyOut(**{k: v for k, v in clone.items() if k not in ("user_id", "is_cache_seed", "casino_name_lower")})

    db_hint = "no direct match in our curated database"
    for s in KNOWN_CASINOS["scams"]:
        if s in name_lower or name_lower in s:
            db_hint = f"FLAGGED in our curated database as a known rogue/blacklisted operator: '{s}'"
            break
    if db_hint == "no direct match in our curated database":
        for r in KNOWN_CASINOS["reputable"]:
            if r in name_lower or name_lower in r:
                db_hint = f"PRESENT in our curated list of reputable, well-licensed operators: '{r}'"
                break

    system_msg = (
        "You are an online-gambling regulatory and forensic analyst. Given a casino name (and optional URL), "
        "produce a trust assessment based on publicly known information about licensing (MGA, UKGC, Curacao, "
        "Kahnawake, etc.), player complaints, payment history, RNG audits, and ownership transparency. "
        "Be objective and use measured, defensible language. NEVER state as fact that an operator is a 'scam' "
        "or is engaged in criminal conduct — instead, describe observed patterns ('reports of delayed withdrawals', "
        "'concerns about license verification', 'multiple unresolved complaints on AskGamblers'). "
        "If you don't know the operator, say so and rely on red-flag heuristics. "
        "Respond EXACTLY in this format:\n"
        "TRUST_SCORE: <integer 0-100>\n"
        "VERDICT: <one-line verdict, choose from: 'Reputable', 'Generally Trusted', 'Caution Advised', 'High Risk', 'Insufficient Information'>\n"
        "RED_FLAGS: <comma-separated short phrases describing observed patterns, or 'none'>\n"
        "GREEN_FLAGS: <comma-separated short phrases, or 'none'>\n"
        "REPORT: <3-5 paragraph plain-language analysis. Frame all concerns as observations and reports, not accusations.>"
    )

    try:
        chat = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=f"legit-{uuid.uuid4()}",
            system_message=system_msg,
        ).with_model("anthropic", "claude-sonnet-4-5-20250929")

        prompt = (
            f"Casino name: {req.casino_name}\n"
            f"Casino URL: {req.casino_url or 'not provided'}\n"
            f"Internal database hint: {db_hint}\n\n"
            "Produce the trust assessment."
        )
        response = await chat.send_message(UserMessage(text=prompt))
        text = str(response)
    except Exception as e:
        logger.exception("Claude legit failed")
        raise HTTPException(500, f"Research failed: {str(e)}")

    trust_score = 50
    verdict = "Unknown"
    red_flags: List[str] = []
    green_flags: List[str] = []
    report_lines: List[str] = []
    capture_report = False
    for line in text.split("\n"):
        u = line.upper()
        if u.startswith("TRUST_SCORE:"):
            try:
                trust_score = int("".join(c for c in line.split(":", 1)[1] if c.isdigit()) or 50)
            except Exception:
                trust_score = 50
        elif u.startswith("VERDICT:"):
            verdict = line.split(":", 1)[1].strip()
        elif u.startswith("RED_FLAGS:"):
            raw = line.split(":", 1)[1].strip()
            if raw.lower() != "none":
                red_flags = [x.strip() for x in raw.split(",") if x.strip()]
        elif u.startswith("GREEN_FLAGS:"):
            raw = line.split(":", 1)[1].strip()
            if raw.lower() != "none":
                green_flags = [x.strip() for x in raw.split(",") if x.strip()]
        elif u.startswith("REPORT:"):
            capture_report = True
            after = line.split(":", 1)[1].strip()
            if after:
                report_lines.append(after)
        elif capture_report:
            report_lines.append(line)

    report = "\n".join(report_lines).strip() or text

    record_id = str(uuid.uuid4())
    doc = {
        "id": record_id,
        "user_id": user["id"],
        "casino_name": req.casino_name,
        "casino_name_lower": name_lower,
        "casino_url": req.casino_url,
        "trust_score": max(0, min(100, trust_score)),
        "verdict": verdict,
        "report": report,
        "red_flags": red_flags,
        "green_flags": green_flags,
        "slug": make_slug(req.casino_name),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "is_cache_seed": True,           # eligible for 24h cache reuse
        "served_from_cache": False,
    }
    await db.legitimacy_reports.insert_one(doc)
    await bump_free_quota(user, "free_trust_checks_used")
    public_doc = {k: v for k, v in doc.items() if k not in ("user_id", "is_cache_seed", "casino_name_lower")}
    return LegitimacyOut(**public_doc)


@api_router.get("/legitimacy/history", response_model=List[LegitimacyOut])
async def legit_history(user=Depends(get_current_user)):
    docs = await db.legitimacy_reports.find(
        {"user_id": user["id"]}, {"_id": 0}
    ).sort("created_at", -1).to_list(200)
    # Backfill slug for old records that don't have one
    for d in docs:
        if not d.get("slug"):
            d["slug"] = make_slug(d.get("casino_name", "casino"))
            await db.legitimacy_reports.update_one({"id": d["id"]}, {"$set": {"slug": d["slug"]}})
    return [LegitimacyOut(**d) for d in docs]


@api_router.get("/legitimacy/public/{slug}", response_model=PublicLegitimacyOut)
async def public_legitimacy_report(slug: str):
    doc = await db.legitimacy_reports.find_one(
        {"slug": slug},
        {"_id": 0, "user_id": 0, "id": 0},
    )
    if not doc:
        raise HTTPException(404, "Report not found")
    return PublicLegitimacyOut(**doc)


# ============= Casino score alerts (email capture) =============
class CasinoAlertReq(BaseModel):
    email: EmailStr
    casino_slug: str
    casino_name: str


@api_router.post("/alerts/subscribe-casino")
async def subscribe_casino_alert(req: CasinoAlertReq):
    # Idempotent: don't double-subscribe same email+slug
    existing = await db.casino_alerts.find_one(
        {"email": req.email.lower(), "casino_slug": req.casino_slug}
    )
    if existing:
        return {"subscribed": True, "already": True}
    await db.casino_alerts.insert_one({
        "id": str(uuid.uuid4()),
        "email": req.email.lower(),
        "casino_slug": req.casino_slug,
        "casino_name": req.casino_name,
        "active": True,
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    return {"subscribed": True, "already": False}


# ============= Verified Badge Program ($299/year) =============
class VerifiedApplicationReq(BaseModel):
    casino_name: str = Field(..., min_length=2, max_length=120)
    contact_name: str = Field(..., min_length=2, max_length=120)
    contact_email: EmailStr
    casino_url: str = Field(..., min_length=4, max_length=500)
    license: str = Field("", max_length=200)
    notes: Optional[str] = Field("", max_length=2000)


@api_router.post("/verified/apply")
async def verified_apply(req: VerifiedApplicationReq):
    record_id = str(uuid.uuid4())
    await db.verified_applications.insert_one({
        "id": record_id,
        **req.model_dump(),
        "status": "pending",
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    return {"application_id": record_id, "status": "received"}


@api_router.get("/verified/applications")
async def list_verified_applications(user=Depends(require_admin)):
    docs = await db.verified_applications.find({}, {"_id": 0}).sort("created_at", -1).to_list(500)
    return docs


@api_router.get("/legitimacy/public", response_model=List[PublicLegitimacyOut])
async def list_public_reports(limit: int = 20):
    docs = await db.legitimacy_reports.find(
        {"slug": {"$exists": True}},
        {"_id": 0, "user_id": 0, "id": 0},
    ).sort("created_at", -1).to_list(min(limit, 100))
    return [PublicLegitimacyOut(**d) for d in docs]


# ============= Scam Wall =============
class ScamPostReq(BaseModel):
    casino_name: str = Field(..., min_length=2, max_length=120)
    title: str = Field(..., min_length=4, max_length=200)
    story: str = Field(..., min_length=20, max_length=5000)
    evidence_url: Optional[str] = None


class ScamPostOut(BaseModel):
    id: str
    user_id: str
    author_name: str
    casino_name: str
    title: str
    story: str
    evidence_url: Optional[str]
    upvotes: int
    downvotes: int
    score: int
    my_vote: Optional[str]
    created_at: str


class VoteReq(BaseModel):
    vote: str  # "up" | "down" | "none"


async def _enrich_scam(doc: dict, user_id: Optional[str]) -> dict:
    upvotes = await db.scam_votes.count_documents({"scam_id": doc["id"], "vote": "up"})
    downvotes = await db.scam_votes.count_documents({"scam_id": doc["id"], "vote": "down"})
    # Add curated baseline for seeded reports (curated from public OP threads).
    upvotes += int(doc.get("seed_upvotes", 0) or 0)
    downvotes += int(doc.get("seed_downvotes", 0) or 0)
    my_vote = None
    if user_id:
        v = await db.scam_votes.find_one({"scam_id": doc["id"], "user_id": user_id}, {"_id": 0})
        if v:
            my_vote = v.get("vote")
    doc["upvotes"] = upvotes
    doc["downvotes"] = downvotes
    doc["score"] = upvotes - downvotes
    doc["my_vote"] = my_vote
    return doc


async def get_optional_user(authorization: Optional[str] = None):
    return None


@api_router.post("/scams", response_model=ScamPostOut)
async def create_scam(req: ScamPostReq, user=Depends(get_current_user)):
    post_id = str(uuid.uuid4())
    doc = {
        "id": post_id,
        "user_id": user["id"],
        "author_name": user["name"],
        "casino_name": req.casino_name.strip(),
        "title": req.title.strip(),
        "story": req.story.strip(),
        "evidence_url": req.evidence_url,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.scam_posts.insert_one(doc)
    enriched = await _enrich_scam({k: v for k, v in doc.items() if k != "_id"}, user["id"])
    return ScamPostOut(**enriched)


@api_router.get("/scams", response_model=List[ScamPostOut])
async def list_scams(sort: str = "top", credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False))):
    user_id = None
    if credentials:
        try:
            payload = jwt.decode(credentials.credentials, JWT_SECRET, algorithms=[JWT_ALGO])
            user_id = payload.get("sub")
        except jwt.PyJWTError:
            user_id = None

    docs = await db.scam_posts.find({}, {"_id": 0}).to_list(500)
    enriched = [await _enrich_scam(d, user_id) for d in docs]
    if sort == "new":
        enriched.sort(key=lambda d: d["created_at"], reverse=True)
    else:
        enriched.sort(key=lambda d: (d["score"], d["created_at"]), reverse=True)
    return [ScamPostOut(**d) for d in enriched]


@api_router.get("/scams/{post_id}", response_model=ScamPostOut)
async def get_scam(post_id: str, credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False))):
    user_id = None
    if credentials:
        try:
            payload = jwt.decode(credentials.credentials, JWT_SECRET, algorithms=[JWT_ALGO])
            user_id = payload.get("sub")
        except jwt.PyJWTError:
            pass

    doc = await db.scam_posts.find_one({"id": post_id}, {"_id": 0})
    if not doc:
        raise HTTPException(404, "Scam post not found")
    enriched = await _enrich_scam(doc, user_id)
    return ScamPostOut(**enriched)


@api_router.post("/scams/{post_id}/vote", response_model=ScamPostOut)
async def vote_scam(post_id: str, req: VoteReq, user=Depends(get_current_user)):
    if req.vote not in ("up", "down", "none"):
        raise HTTPException(400, "vote must be up, down, or none")
    post = await db.scam_posts.find_one({"id": post_id}, {"_id": 0})
    if not post:
        raise HTTPException(404, "Scam post not found")

    if req.vote == "none":
        await db.scam_votes.delete_one({"scam_id": post_id, "user_id": user["id"]})
    else:
        await db.scam_votes.update_one(
            {"scam_id": post_id, "user_id": user["id"]},
            {"$set": {"scam_id": post_id, "user_id": user["id"], "vote": req.vote,
                      "updated_at": datetime.now(timezone.utc).isoformat()}},
            upsert=True,
        )
    enriched = await _enrich_scam(post, user["id"])
    return ScamPostOut(**enriched)


@api_router.post("/admin/seed-scam-wall")
async def seed_scam_wall(user=Depends(require_admin)):
    """Idempotent seed of curated, attribution-linked Scam Wall reports."""
    from scam_wall_seed import build_seed_docs
    docs = build_seed_docs()
    inserted = 0
    updated = 0
    for d in docs:
        existing = await db.scam_posts.find_one({"id": d["id"]}, {"_id": 0, "id": 1})
        if existing:
            await db.scam_posts.update_one(
                {"id": d["id"]},
                {"$set": d},
            )
            updated += 1
        else:
            await db.scam_posts.insert_one(d)
            inserted += 1
    return {"inserted": inserted, "updated": updated, "total": len(docs)}


# ============= Affiliate Casinos (Monetization) =============
class AffiliateCasinoReq(BaseModel):
    name: str = Field(..., min_length=2, max_length=120)
    url: str = Field(..., min_length=4, max_length=500)
    license: str = Field("", max_length=120)
    badge: str = Field("", max_length=60)
    description: str = Field("", max_length=400)
    logo_url: Optional[str] = None
    payout_note: str = Field("", max_length=80)
    sort_order: int = 0
    active: bool = True


class AffiliateCasinoOut(BaseModel):
    id: str
    name: str
    url: str
    license: str
    badge: str
    description: str
    logo_url: Optional[str]
    payout_note: str
    sort_order: int
    active: bool
    created_at: str


class ClickReq(BaseModel):
    affiliate_id: str
    source: str = "unknown"


@api_router.get("/affiliates/casinos", response_model=List[AffiliateCasinoOut])
async def list_affiliates():
    docs = await db.affiliate_casinos.find({"active": True}, {"_id": 0}).to_list(200)
    docs.sort(key=lambda d: (d.get("sort_order", 0), d.get("created_at", "")))
    return [AffiliateCasinoOut(**d) for d in docs]


@api_router.get("/affiliates/casinos/all", response_model=List[AffiliateCasinoOut])
async def list_affiliates_all(user=Depends(require_admin)):
    docs = await db.affiliate_casinos.find({}, {"_id": 0}).to_list(500)
    docs.sort(key=lambda d: (d.get("sort_order", 0), d.get("created_at", "")))
    return [AffiliateCasinoOut(**d) for d in docs]


@api_router.post("/affiliates/casinos", response_model=AffiliateCasinoOut)
async def create_affiliate(req: AffiliateCasinoReq, user=Depends(require_admin)):
    cid = str(uuid.uuid4())
    doc = {
        "id": cid,
        **req.model_dump(),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.affiliate_casinos.insert_one(doc)
    return AffiliateCasinoOut(**{k: v for k, v in doc.items() if k != "_id"})


@api_router.put("/affiliates/casinos/{cid}", response_model=AffiliateCasinoOut)
async def update_affiliate(cid: str, req: AffiliateCasinoReq, user=Depends(require_admin)):
    existing = await db.affiliate_casinos.find_one({"id": cid}, {"_id": 0})
    if not existing:
        raise HTTPException(404, "Casino not found")
    updated = {**existing, **req.model_dump()}
    await db.affiliate_casinos.update_one({"id": cid}, {"$set": req.model_dump()})
    return AffiliateCasinoOut(**updated)


@api_router.delete("/affiliates/casinos/{cid}")
async def delete_affiliate(cid: str, user=Depends(require_admin)):
    res = await db.affiliate_casinos.delete_one({"id": cid})
    if res.deleted_count == 0:
        raise HTTPException(404, "Casino not found")
    return {"deleted": cid}


@api_router.post("/affiliates/click")
async def log_click(
    req: ClickReq,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False)),
):
    user_id = None
    if credentials:
        try:
            payload = jwt.decode(credentials.credentials, JWT_SECRET, algorithms=[JWT_ALGO])
            user_id = payload.get("sub")
        except jwt.PyJWTError:
            pass
    await db.affiliate_clicks.insert_one({
        "id": str(uuid.uuid4()),
        "affiliate_id": req.affiliate_id,
        "user_id": user_id,
        "source": req.source,
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    return {"ok": True}


@api_router.get("/affiliates/stats")
async def affiliate_stats(user=Depends(require_admin)):
    pipeline = [
        {"$group": {"_id": "$affiliate_id", "clicks": {"$sum": 1}}},
    ]
    counts = {}
    async for row in db.affiliate_clicks.aggregate(pipeline):
        counts[row["_id"]] = row["clicks"]
    casinos = await db.affiliate_casinos.find({}, {"_id": 0}).to_list(200)
    return [
        {"id": c["id"], "name": c["name"], "clicks": counts.get(c["id"], 0), "active": c.get("active", True)}
        for c in casinos
    ]


# ============= Stripe Subscription (Premium) =============
class CheckoutReq(BaseModel):
    origin_url: str


@api_router.post("/stripe/checkout")
async def create_premium_checkout(req: CheckoutReq, http_request: FastAPIRequest, user=Depends(get_current_user)):
    host_url = str(http_request.base_url).rstrip("/")
    webhook_url = f"{host_url}/api/webhook/stripe"
    stripe_checkout = StripeCheckout(api_key=STRIPE_API_KEY, webhook_url=webhook_url)

    origin = req.origin_url.rstrip("/")
    success_url = f"{origin}/pricing/success?session_id={{CHECKOUT_SESSION_ID}}"
    cancel_url = f"{origin}/pricing"

    checkout_req = CheckoutSessionRequest(
        amount=float(PREMIUM_MONTHLY_USD),
        currency="usd",
        success_url=success_url,
        cancel_url=cancel_url,
        metadata={"user_id": user["id"], "plan": "premium_monthly"},
    )
    session: CheckoutSessionResponse = await stripe_checkout.create_checkout_session(checkout_req)

    await db.payment_transactions.insert_one({
        "id": str(uuid.uuid4()),
        "session_id": session.session_id,
        "user_id": user["id"],
        "amount": float(PREMIUM_MONTHLY_USD),
        "currency": "usd",
        "metadata": {"plan": "premium_monthly"},
        "payment_status": "initiated",
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    return {"url": session.url, "session_id": session.session_id}


@api_router.get("/stripe/checkout/status/{session_id}")
async def stripe_checkout_status(session_id: str, http_request: FastAPIRequest, user=Depends(get_current_user)):
    tx = await db.payment_transactions.find_one({"session_id": session_id}, {"_id": 0})
    if not tx:
        raise HTTPException(404, "Transaction not found")

    # Try the Stripe proxy; fall back to local payment_transactions record if proxy is unavailable.
    try:
        host_url = str(http_request.base_url).rstrip("/")
        webhook_url = f"{host_url}/api/webhook/stripe"
        stripe_checkout = StripeCheckout(api_key=STRIPE_API_KEY, webhook_url=webhook_url)
        status: CheckoutStatusResponse = await stripe_checkout.get_checkout_status(session_id)
        proxy_ok = True
    except Exception as e:
        logger.warning(f"Stripe status proxy unavailable, using local record: {e}")
        proxy_ok = False

    if proxy_ok:
        # Only upgrade once
        if status.payment_status == "paid" and tx.get("payment_status") != "paid":
            await db.payment_transactions.update_one(
                {"session_id": session_id},
                {"$set": {"payment_status": "paid", "status": status.status,
                          "paid_at": datetime.now(timezone.utc).isoformat()}},
            )
            await db.users.update_one(
                {"id": tx["user_id"]},
                {"$set": {"is_premium": True, "premium_since": datetime.now(timezone.utc).isoformat()}},
            )
        elif status.status == "expired":
            await db.payment_transactions.update_one(
                {"session_id": session_id},
                {"$set": {"payment_status": "expired", "status": status.status}},
            )
        return {
            "status": status.status,
            "payment_status": status.payment_status,
            "amount_total": int(status.amount_total),
            "currency": status.currency,
            "source": "stripe",
        }

    # Fallback: rely on local record (updated by webhook). Return what we know.
    return {
        "status": tx.get("status", "open"),
        "payment_status": tx.get("payment_status", "initiated"),
        "amount_total": int(float(tx.get("amount", 0)) * 100),
        "currency": tx.get("currency", "usd"),
        "source": "local_fallback",
    }


@app.post("/api/webhook/stripe")
async def stripe_webhook(request: FastAPIRequest):
    body = await request.body()
    sig = request.headers.get("Stripe-Signature", "")
    host_url = str(request.base_url).rstrip("/")
    stripe_checkout = StripeCheckout(api_key=STRIPE_API_KEY, webhook_url=f"{host_url}/api/webhook/stripe")
    try:
        evt = await stripe_checkout.handle_webhook(body, sig)
    except Exception as e:
        logger.exception("Stripe webhook error")
        raise HTTPException(400, str(e))
    if evt.payment_status == "paid" and evt.session_id:
        tx = await db.payment_transactions.find_one({"session_id": evt.session_id}, {"_id": 0})
        if tx and tx.get("payment_status") != "paid":
            await db.payment_transactions.update_one(
                {"session_id": evt.session_id},
                {"$set": {"payment_status": "paid", "paid_at": datetime.now(timezone.utc).isoformat()}},
            )
            await db.users.update_one(
                {"id": tx["user_id"]},
                {"$set": {"is_premium": True}},
            )
    return {"received": True}


# ============= Deep Audit (one-off $24.99) =============
class DeepAuditReq(BaseModel):
    casino_name: str = Field(..., min_length=2, max_length=120)
    casino_url: Optional[str] = None
    extra_context: Optional[str] = Field("", max_length=2000)
    origin_url: str


@api_router.post("/audit/checkout")
async def deep_audit_checkout(req: DeepAuditReq, http_request: FastAPIRequest, user=Depends(get_current_user)):
    host_url = str(http_request.base_url).rstrip("/")
    webhook_url = f"{host_url}/api/webhook/stripe"
    stripe_checkout = StripeCheckout(api_key=STRIPE_API_KEY, webhook_url=webhook_url)

    origin = req.origin_url.rstrip("/")
    success_url = f"{origin}/audit/result?session_id={{CHECKOUT_SESSION_ID}}"
    cancel_url = f"{origin}/audit"

    checkout_req = CheckoutSessionRequest(
        amount=float(DEEP_AUDIT_USD),
        currency="usd",
        success_url=success_url,
        cancel_url=cancel_url,
        metadata={
            "user_id": user["id"],
            "plan": "deep_audit",
            "casino_name": req.casino_name,
            "casino_url": req.casino_url or "",
            "extra_context": (req.extra_context or "")[:1500],
        },
    )
    session = await stripe_checkout.create_checkout_session(checkout_req)
    await db.payment_transactions.insert_one({
        "id": str(uuid.uuid4()),
        "session_id": session.session_id,
        "user_id": user["id"],
        "amount": float(DEEP_AUDIT_USD),
        "currency": "usd",
        "metadata": {
            "plan": "deep_audit",
            "casino_name": req.casino_name,
            "casino_url": req.casino_url,
            "extra_context": req.extra_context or "",
        },
        "payment_status": "initiated",
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    return {"url": session.url, "session_id": session.session_id}


@api_router.get("/audit/result/{session_id}")
async def deep_audit_result(session_id: str, http_request: FastAPIRequest, user=Depends(get_current_user)):
    tx = await db.payment_transactions.find_one({"session_id": session_id, "user_id": user["id"]}, {"_id": 0})
    if not tx:
        raise HTTPException(404, "Audit not found")

    # If already generated, return cached
    if tx.get("audit_result"):
        return {"status": "complete", **tx["audit_result"]}

    # Confirm payment first
    try:
        host_url = str(http_request.base_url).rstrip("/")
        stripe_checkout = StripeCheckout(api_key=STRIPE_API_KEY, webhook_url=f"{host_url}/api/webhook/stripe")
        status_resp = await stripe_checkout.get_checkout_status(session_id)
        paid = status_resp.payment_status == "paid"
    except Exception:
        paid = tx.get("payment_status") == "paid"

    if not paid:
        return {"status": "pending", "payment_status": tx.get("payment_status", "initiated")}

    # Mark paid (idempotent)
    if tx.get("payment_status") != "paid":
        await db.payment_transactions.update_one(
            {"session_id": session_id},
            {"$set": {"payment_status": "paid", "paid_at": datetime.now(timezone.utc).isoformat()}},
        )

    # Generate deep audit
    md = tx.get("metadata") or {}
    name = md.get("casino_name", "Unknown casino")
    url = md.get("casino_url") or "not provided"
    ctx = md.get("extra_context") or ""

    system_msg = (
        "You are a senior online-gambling forensics analyst preparing a paid premium audit report. "
        "Be thorough, specific, and cite reasoning. Cover: license verification, ownership and corporate "
        "transparency, RNG audit status, RTP disclosure, complaint history (Casinomeister, AskGamblers, "
        "ThePogg, Trustpilot trends), withdrawal patterns (delays, KYC weaponization), bonus terms (WR, "
        "max-bet caps, game weighting), responsible-gambling tooling, jurisdictional protection for the "
        "player. Output in this EXACT format:\n"
        "TRUST_SCORE: <0-100>\n"
        "VERDICT: <single line>\n"
        "EXECUTIVE_SUMMARY: <3-4 sentence laypeople summary>\n"
        "LICENSING: <paragraph>\n"
        "OWNERSHIP: <paragraph>\n"
        "RNG_AND_RTP: <paragraph>\n"
        "COMPLAINTS_HISTORY: <paragraph>\n"
        "WITHDRAWAL_RISK: <paragraph>\n"
        "BONUS_TERMS_ANALYSIS: <paragraph>\n"
        "RESPONSIBLE_GAMBLING: <paragraph>\n"
        "FINAL_RECOMMENDATION: <paragraph with specific protect-yourself steps>\n"
        "RED_FLAGS: <comma-separated>\n"
        "GREEN_FLAGS: <comma-separated>"
    )

    try:
        chat = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=f"audit-{session_id}",
            system_message=system_msg,
        ).with_model("anthropic", "claude-sonnet-4-5-20250929")

        prompt = (
            f"Casino: {name}\nURL: {url}\nUser-supplied context: {ctx or '(none)'}\n\n"
            "Deliver the full premium audit."
        )
        response = await chat.send_message(UserMessage(text=prompt))
        text = str(response)
    except Exception as e:
        logger.exception("Deep audit LLM failed")
        raise HTTPException(500, f"Audit generation failed: {str(e)}")

    audit = {
        "casino_name": name,
        "casino_url": url if url != "not provided" else None,
        "report": text,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.payment_transactions.update_one(
        {"session_id": session_id},
        {"$set": {"audit_result": audit}},
    )
    return {"status": "complete", **audit}


# ============= SEO =============
@app.get("/api/sitemap.xml")
async def sitemap(request: FastAPIRequest):
    # Use SITE_URL env if provided, else derive from request host
    base = os.environ.get("SITE_URL", "").rstrip("/")
    if not base:
        host = request.headers.get("x-forwarded-host") or request.url.hostname
        scheme = request.headers.get("x-forwarded-proto") or "https"
        base = f"{scheme}://{host}" if host else "https://scam-spotter-casino.preview.emergentagent.com"
    static_urls = ["/", "/techniques", "/reports", "/scams", "/pricing", "/compare"]
    docs = await db.legitimacy_reports.find({"slug": {"$exists": True}}, {"_id": 0, "slug": 1, "created_at": 1}).to_list(2000)
    techniques = [t["slug"] for t in TECHNIQUES_SEED]

    items = []
    for u in static_urls:
        items.append(f"<url><loc>{base}{u}</loc><changefreq>weekly</changefreq></url>")
    items.append(f"<url><loc>{base}/verified</loc><changefreq>monthly</changefreq><priority>0.7</priority></url>")
    for t in techniques:
        # Long-form articles get higher priority + monthly lastmod
        if t in TECHNIQUE_ARTICLES:
            lastmod = TECHNIQUE_ARTICLES[t].get("updated_date") or TECHNIQUE_ARTICLES[t].get("published_date", "")
            items.append(
                f"<url><loc>{base}/techniques/{t}</loc>"
                f"<lastmod>{lastmod}</lastmod>"
                f"<changefreq>monthly</changefreq><priority>0.9</priority></url>"
            )
        else:
            items.append(f"<url><loc>{base}/techniques/{t}</loc><changefreq>monthly</changefreq><priority>0.6</priority></url>")
    for d in docs:
        lastmod = (d.get("created_at") or "")[:10]
        items.append(f"<url><loc>{base}/report/{d['slug']}</loc><lastmod>{lastmod}</lastmod><changefreq>weekly</changefreq><priority>0.8</priority></url>")

    live_pubs = await db.live_sessions.find(
        {"public_slug": {"$exists": True, "$ne": None}},
        {"_id": 0, "public_slug": 1, "published_at": 1},
    ).to_list(2000)
    for d in live_pubs:
        lastmod = (d.get("published_at") or "")[:10]
        items.append(f"<url><loc>{base}/live-report/{d['public_slug']}</loc><lastmod>{lastmod}</lastmod><changefreq>weekly</changefreq><priority>0.8</priority></url>")

    xml = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + "\n".join(items) + "\n</urlset>"
    return Response(content=xml, media_type="application/xml")


# ============= Email Digest (Resend) =============
def make_unsub_token(user_id: str) -> str:
    return jwt.encode({"sub": user_id, "purpose": "unsub"}, JWT_SECRET, algorithm=JWT_ALGO)


async def build_digest_html(site_url: str) -> dict:
    """Build the weekly digest content. Returns {subject, html, text, casino_count}."""
    cutoff = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
    # Lowest 5 trust scores in last 7 days (fallback: all-time lowest 5 if <5 recent)
    docs = await db.legitimacy_reports.find(
        {"created_at": {"$gte": cutoff}},
        {"_id": 0, "casino_name": 1, "trust_score": 1, "verdict": 1, "slug": 1},
    ).sort("trust_score", 1).limit(5).to_list(5)
    if len(docs) < 5:
        docs = await db.legitimacy_reports.find(
            {}, {"_id": 0, "casino_name": 1, "trust_score": 1, "verdict": 1, "slug": 1},
        ).sort("trust_score", 1).limit(5).to_list(5)

    # Highest trust this week for the "safer alternative" CTA (must have slug)
    high = await db.legitimacy_reports.find(
        {"slug": {"$exists": True}}, {"_id": 0, "casino_name": 1, "trust_score": 1, "slug": 1},
    ).sort("trust_score", -1).limit(1).to_list(1)
    safe = high[0] if high else None

    # Top affiliate (active, lowest sort_order)
    affs = await db.affiliate_casinos.find({"active": True}, {"_id": 0}).sort("sort_order", 1).limit(1).to_list(1)
    aff = affs[0] if affs else None

    rows_html = ""
    for d in docs:
        slug = d.get("slug", "")
        score = d.get("trust_score", 0)
        color = "#ff3b30" if score < 45 else ("#ffcc00" if score < 75 else "#00ff41")
        link_open = f'<a href="{site_url}/report/{slug}" style="color:#fff;text-decoration:none;">' if slug else "<div>"
        link_close = "</a>" if slug else "</div>"
        rows_html += f"""
        <tr><td style="padding:14px 0;border-bottom:1px solid #1f1f1f;">
          {link_open}
            <table width="100%" cellpadding="0" cellspacing="0"><tr>
              <td style="font-family:monospace;font-size:14px;color:#fff;">{d.get('casino_name','?')}</td>
              <td align="right" style="font-family:monospace;font-size:22px;font-weight:700;color:{color};">{score}/100</td>
            </tr><tr>
              <td colspan="2" style="font-family:monospace;font-size:11px;color:#888;padding-top:4px;">&gt; {d.get('verdict','')}</td>
            </tr></table>
          {link_close}
        </td></tr>"""

    safe_block = ""
    if safe:
        safe_block = f"""
        <tr><td style="padding:16px;background:#0a0a0a;border:1px solid #00ff41;border-radius:2px;">
          <p style="margin:0 0 6px;font-family:monospace;font-size:10px;letter-spacing:.2em;text-transform:uppercase;color:#00ff41;">// safer alternative this week</p>
          <a href="{site_url}/report/{safe['slug']}" style="color:#fff;font-family:'Unbounded',sans-serif;font-size:18px;text-decoration:none;">
            {safe['casino_name']} <span style="color:#00ff41;">— {safe['trust_score']}/100</span>
          </a>
        </td></tr><tr><td style="height:14px;"></td></tr>"""

    aff_block = ""
    if aff:
        aff_block = f"""
        <tr><td style="padding:16px;background:#0a0a0a;border:1px solid #2a2a2a;border-radius:2px;">
          <p style="margin:0 0 4px;font-family:monospace;font-size:10px;color:#888;">Sponsored ·  Licensed operator</p>
          <a href="{aff['url']}" style="color:#00ff41;font-family:'Unbounded',sans-serif;font-size:16px;text-decoration:none;">
            Try {aff['name']} &gt;_
          </a>
          <p style="margin:6px 0 0;font-family:monospace;font-size:11px;color:#aaa;">{aff.get('description','')[:140]}</p>
        </td></tr>"""

    html = f"""
    <html><body style="margin:0;padding:0;background:#050505;color:#fff;font-family:monospace;">
    <table width="100%" cellpadding="0" cellspacing="0" style="background:#050505;padding:40px 0;">
      <tr><td align="center">
        <table width="600" cellpadding="0" cellspacing="0" style="background:#050505;">
          <tr><td style="padding:0 24px 24px;">
            <p style="margin:0;font-family:monospace;font-size:11px;letter-spacing:.3em;text-transform:uppercase;color:#00ff41;">&gt;_ Casino Spotter</p>
            <h1 style="margin:8px 0 4px;font-family:'Unbounded',sans-serif;font-size:32px;font-weight:900;color:#fff;letter-spacing:-1px;">THIS WEEK'S WORST</h1>
            <p style="margin:0;font-family:monospace;font-size:12px;color:#888;">The 5 lowest-trust casinos right now</p>
          </td></tr>
          <tr><td style="padding:0 24px;">
            <table width="100%" cellpadding="0" cellspacing="0">{rows_html}</table>
          </td></tr>
          <tr><td style="height:30px;"></td></tr>
          <tr><td style="padding:0 24px;">
            <table width="100%" cellpadding="0" cellspacing="0">{safe_block}{aff_block}</table>
          </td></tr>
          <tr><td style="padding:30px 24px;text-align:center;">
            <a href="{site_url}/reports" style="display:inline-block;background:#00ff41;color:#000;font-family:'Unbounded',sans-serif;font-weight:700;font-size:12px;text-decoration:none;padding:12px 24px;letter-spacing:.05em;text-transform:uppercase;">View all reports &gt;_</a>
          </td></tr>
          <tr><td style="padding:20px 24px;text-align:center;border-top:1px solid #1f1f1f;">
            <p style="margin:0;font-family:monospace;font-size:10px;color:#666;">
              18+ · BeGambleAware · Educational use only<br>
              You're receiving this because you signed up at Casino Spotter.<br>
              <a href="{{unsub_link}}" style="color:#888;">Unsubscribe</a>
            </p>
          </td></tr>
        </table>
      </td></tr>
    </table>
    </body></html>"""

    text = "Casino Spotter — Weekly Digest\n\nTHIS WEEK'S WORST:\n"
    for d in docs:
        text += f"  {d['trust_score']:>3}/100  {d['casino_name']} — {d.get('verdict','')}\n"
    if safe:
        text += f"\nSafer alternative: {safe['casino_name']} ({safe['trust_score']}/100)\n{site_url}/report/{safe['slug']}\n"
    text += f"\nAll reports: {site_url}/reports\n\nUnsubscribe: {{unsub_link}}\n"

    return {
        "subject": f"{len(docs)} worst casinos this week · Casino Spotter",
        "html": html,
        "text": text,
        "casino_count": len(docs),
    }


@api_router.get("/digest/preview")
async def digest_preview(user=Depends(require_admin)):
    site_url = os.environ.get("SITE_URL", "https://scam-spotter-casino.preview.emergentagent.com").rstrip("/")
    content = await build_digest_html(site_url)
    sample = content["html"].replace("{unsub_link}", f"{site_url}/unsubscribe?token=SAMPLE")
    return {"subject": content["subject"], "html": sample, "casino_count": content["casino_count"]}


class DigestSendReq(BaseModel):
    test_only: bool = False


@api_router.post("/digest/send")
async def digest_send(req: DigestSendReq, user=Depends(require_admin)):
    if not RESEND_API_KEY:
        raise HTTPException(500, "RESEND_API_KEY not configured")
    site_url = os.environ.get("SITE_URL", "https://scam-spotter-casino.preview.emergentagent.com").rstrip("/")
    content = await build_digest_html(site_url)

    # Recipients: admin only if test, otherwise all subscribed users
    if req.test_only:
        recipients = [{"id": user["id"], "email": user["email"]}]
    else:
        recipients = await db.users.find(
            {"email_digest_subscribed": {"$ne": False}},
            {"_id": 0, "id": 1, "email": 1},
        ).to_list(5000)

    sent = 0
    failures = []
    for r in recipients:
        unsub_link = f"{site_url}/unsubscribe?token={make_unsub_token(r['id'])}"
        params = {
            "from": SENDER_EMAIL,
            "to": [r["email"]],
            "subject": content["subject"],
            "html": content["html"].replace("{unsub_link}", unsub_link),
            "text": content["text"].replace("{unsub_link}", unsub_link),
        }
        try:
            await asyncio.to_thread(resend.Emails.send, params)
            sent += 1
        except Exception as e:
            logger.exception(f"Failed to email {r['email']}: {e}")
            failures.append({"email": r["email"], "error": str(e)})

    await db.digest_runs.insert_one({
        "id": str(uuid.uuid4()),
        "sent": sent,
        "failures": failures,
        "test_only": req.test_only,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "sent_by": user["id"],
    })
    return {"sent": sent, "failures": len(failures), "total": len(recipients)}


@api_router.patch("/user/preferences", response_model=UserOut)
async def update_preferences(req: DigestPrefReq, user=Depends(get_current_user)):
    await db.users.update_one(
        {"id": user["id"]},
        {"$set": {"email_digest_subscribed": bool(req.subscribed)}},
    )
    updated = await db.users.find_one({"id": user["id"]}, {"_id": 0, "password": 0})
    return build_user_out(updated)


@app.get("/api/unsubscribe")
async def public_unsubscribe(token: str):
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGO])
        if payload.get("purpose") != "unsub":
            raise HTTPException(400, "Invalid token")
        user_id = payload.get("sub")
    except jwt.PyJWTError:
        raise HTTPException(400, "Invalid or expired token")
    res = await db.users.update_one({"id": user_id}, {"$set": {"email_digest_subscribed": False}})
    if res.matched_count == 0:
        raise HTTPException(404, "User not found")
    return {"unsubscribed": True}


app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get("CORS_ORIGINS", "*").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("shutdown")
async def shutdown():
    client.close()
