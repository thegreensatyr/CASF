import os
import uuid
import logging
import shutil
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import List, Optional

import bcrypt
import jwt
from dotenv import load_dotenv
from fastapi import FastAPI, APIRouter, HTTPException, Depends, UploadFile, File, Form, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.staticfiles import StaticFiles
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, EmailStr, Field

from emergentintegrations.llm.chat import LlmChat, UserMessage, FileContentWithMimeType

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

UPLOAD_DIR = ROOT_DIR / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

MONGO_URL = os.environ["MONGO_URL"]
DB_NAME = os.environ["DB_NAME"]
EMERGENT_LLM_KEY = os.environ["EMERGENT_LLM_KEY"]
JWT_SECRET = os.environ["JWT_SECRET"]
JWT_ALGO = "HS256"
JWT_EXP_DAYS = 7

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
    created_at: str


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
        user=UserOut(id=user_id, email=req.email, name=req.name),
    )


@api_router.post("/auth/login", response_model=AuthResp)
async def login(req: LoginReq):
    user = await db.users.find_one({"email": req.email}, {"_id": 0})
    if not user or not verify_password(req.password, user["password"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    return AuthResp(
        token=create_token(user["id"]),
        user=UserOut(id=user["id"], email=user["email"], name=user["name"], is_admin=is_admin_user(user)),
    )


@api_router.get("/auth/me", response_model=UserOut)
async def me(user=Depends(get_current_user)):
    return UserOut(id=user["id"], email=user["email"], name=user["name"], is_admin=is_admin_user(user))


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
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.legitimacy_reports.insert_one(doc)
    return LegitimacyOut(**doc)


@api_router.get("/legitimacy/history", response_model=List[LegitimacyOut])
async def legit_history(user=Depends(get_current_user)):
    docs = await db.legitimacy_reports.find(
        {"user_id": user["id"]}, {"_id": 0}
    ).sort("created_at", -1).to_list(200)
    return [LegitimacyOut(**d) for d in docs]


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
