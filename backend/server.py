import os
import re
import uuid
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


class LoginReq(BaseModel):
    email: EmailStr
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


class DigestPrefReq(BaseModel):
    subscribed: bool


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


class TechniqueOut(BaseModel):
    slug: str
    name: str
    category: str
    short: str
    description: str
    how_it_works: str
    how_to_spot: str
    severity: str


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
        "description": "A legitimate RNG is independently audited (eCOGRA, iTech Labs, GLI). Scam casinos either fake certifications or run uncertified games.",
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
async def signup(req: SignupReq):
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
    }
    await db.users.insert_one(user_doc)
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


async def check_free_quota(user: dict, key: str, limit: int):
    """Check quota WITHOUT incrementing. Raise 402 if exhausted."""
    if user.get("is_premium"):
        return
    if int(user.get(key, 0)) >= limit:
        raise HTTPException(
            status_code=402,
            detail="Free quota exhausted. Upgrade to Premium ($9.99/mo) for unlimited.",
        )


async def bump_free_quota(user: dict, key: str):
    """Increment quota after a successful operation. No-op for premium users."""
    if user.get("is_premium"):
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


@api_router.get("/techniques", response_model=List[TechniqueOut])
async def list_techniques():
    return [TechniqueOut(**t) for t in TECHNIQUES_SEED]


@api_router.get("/techniques/{slug}", response_model=TechniqueOut)
async def get_technique(slug: str):
    for t in TECHNIQUES_SEED:
        if t["slug"] == slug:
            return TechniqueOut(**t)
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
        "Be objective. If you don't know the operator, say so and rely on red-flag heuristics. "
        "Respond EXACTLY in this format:\n"
        "TRUST_SCORE: <integer 0-100>\n"
        "VERDICT: <one-line verdict like 'Reputable', 'Cautious', 'Avoid', 'Likely Scam'>\n"
        "RED_FLAGS: <comma-separated short phrases, or 'none'>\n"
        "GREEN_FLAGS: <comma-separated short phrases, or 'none'>\n"
        "REPORT: <3-5 paragraph plain-language report>"
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
        "casino_url": req.casino_url,
        "trust_score": max(0, min(100, trust_score)),
        "verdict": verdict,
        "report": report,
        "red_flags": red_flags,
        "green_flags": green_flags,
        "slug": make_slug(req.casino_name),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.legitimacy_reports.insert_one(doc)
    await bump_free_quota(user, "free_trust_checks_used")
    return LegitimacyOut(**doc)


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
    for t in techniques:
        items.append(f"<url><loc>{base}/techniques/{t}</loc><changefreq>monthly</changefreq></url>")
    for d in docs:
        lastmod = (d.get("created_at") or "")[:10]
        items.append(f"<url><loc>{base}/report/{d['slug']}</loc><lastmod>{lastmod}</lastmod><changefreq>weekly</changefreq><priority>0.8</priority></url>")

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
