# Casino Spotter — PRD

## Original problem statement
> "I would like an app that explains techniques and tricks that online casinos use to cheat you or give false hope. The app or bot would observe a game being played and explain the technique. It would also be able to research if the casino is legitimate or a scam."

## User choices (Feb 2026)
- Game observation: short video clips + screenshots upload
- AI: Gemini 3 Flash (multimodal media analysis) + Claude Sonnet 4.5 (casino trust research)
- Casino legitimacy: curated blacklist DB + AI research (both)
- Auth: simple email/password JWT
- Theme: green neon + black (mandated)

## Architecture
- FastAPI backend, MongoDB (motor), JWT auth via PyJWT + bcrypt
- emergentintegrations.LlmChat for Gemini (FileContentWithMimeType for video/image) and Claude
- React 19 + react-router v7 + Tailwind + shadcn/ui + sonner
- Fonts: Unbounded (headings), JetBrains Mono (body)

## User personas
- Casino-curious recreational player wanting to spot manipulation
- Concerned spouse/relative researching a partner's gambling site
- Researcher/journalist documenting industry dark patterns

## Core requirements
1. Upload video/screenshot → AI explains manipulation techniques in plain English
2. Casino legitimacy lookup → trust score, red/green flags, narrative report
3. Library of known cheating tricks (educational, severity-ranked)
4. Private dashboard with user's analysis history
5. Auth: email + password signup/login/me

## Implemented (Feb 2026)
- Landing page (hero, bento features, CTA)
- Auth: signup, login, me; JWT in localStorage; protected routes
- Techniques library (8 seeded): near-miss, false-rtp, slow-reveal, bonus-traps, delayed-withdrawal, rigged-rng, live-dealer-shills, vip-manipulation
- /analyze endpoint: image/video → Gemini 3 Flash multimodal forensic report
- /legitimacy/research: Claude Sonnet 4.5 + curated reputable/scam list → trust score 0-100, verdict, flags
- Dashboard with stats + scan/lookup history cards
- **Scam Wall**: community submissions + up/down voting (auth required to post/vote; public to view). Sort by Top or New. One vote per user per post (upsert; switchable; removable).
- **Affiliate CTAs (monetization)**: admin-managed casino list shown contextually on (a) low-trust legitimacy reports, (b) technique detail pages, (c) scam wall list, (d) public reports. Click tracking + per-casino stats. `rel="nofollow sponsored"`, 18+ disclaimer.
- Admin role via `ADMIN_EMAIL` env var; `/admin/affiliates` CRUD page with click stats; `/admin/guide` monetization quick-start with ready-to-paste affiliate-network application draft.
- **Public shareable trust reports**: `/report/:slug` (no auth) + `/reports` directory with search/filter/sort. Auto-generated SEO-friendly slugs. Schema.org Review JSON-LD per report for Google ⭐ ratings. Copy/X/Reddit share buttons.
- **Compare casinos**: `/compare` — pick up to 3, full side-by-side panel with red/green flags, license, verdict.
- **Freemium + Stripe**: 1 trust check + 1 video scan free, then $9.99/mo Premium via Stripe checkout. `/pricing` page; payment success polling; webhook + local-fallback for unreliable Stripe proxy.
- **Email digest (Resend)**: `/admin/digest` for admin send + iframe preview. Weekly "Top 5 worst casinos + 1 trusted alternative + 1 affiliate CTA + unsub link" HTML email. User can toggle subscription from `/dashboard`. One-click unsub at `/unsubscribe?token=...`.
- **SEO**: `/api/sitemap.xml` (39+ URLs, dynamic host), `/robots.txt`, per-page `<title>` updates.
- **Live activity feed + community quote + authority bar + animated counters** on landing page.
- **Forgot password** (Feb 2026): `/forgot-password` + `/reset-password` pages, single-use tokens (1h TTL) stored in `password_resets`, Resend email + supervisor log fallback + admin `debug_link` in response (for preview while DNS pending).
- **Live screen-capture mode** (Feb 2026): `/live` page uses `navigator.mediaDevices.getDisplayMedia` to share screen/tab, captures frames every 15s, Gemini 3 Flash analyzes per-frame. Sessions are 60s for free trial / 180s for Premium & admin. Trial gating: 1 free 60s session, flag only burned after first successful frame (cancelling OS share dialog does NOT consume the trial). Live findings feed + auto-saved session report with AI summary. Endpoints: `/api/live/session/start`, `/api/live/frame`, `/api/live/session/end`, `/api/live/sessions`, `/api/live/session/{id}`.
- **Live Sessions dashboard timeline** (Feb 2026): new "LIVE SESSIONS" section on `/dashboard` lists past captures with sort (most recent / most flagged / least flagged) + filter by technique slug. Each card shows game type, casino, frame count, flagged-count, top 3 techniques. Click → `/live/sessions/:id` detail page with frame-by-frame timeline (flagged vs clean), AI editorial summary, and aggregated technique chips.
- **Promote-to-public-report** (Feb 2026): owners of a live session with ≥1 flagged technique can publish it via `/live/session/{id}/publish` → permanent public URL `/live-report/:slug`. SEO-indexed (added to sitemap.xml), auto-generated headline (`"{Casino}: live {game} capture flagged {top 3 techniques}"`), JSON-LD Report schema injected. Public page shows headline, technique chips, AI editorial summary, frame-by-frame evidence timeline, and a signup CTA. Unpublish supported. Public reports list at `/reports` now includes a "LIVE CAPTURE EVIDENCE" section above the trust reports grid. Endpoints: `/api/live/session/{id}/publish`, `/api/live/session/{id}/unpublish`, `/api/live/public`, `/api/live/public/{slug}`.
- **Right-of-response (Disputes) system** (Feb 2026): every `/report/:slug` (trust) and `/live-report/:slug` (live) public page now carries (a) a "Operator Response" panel rendering any approved disputes, and (b) a `LegalDisclaimer` footer with editorial-standards copy + "File a dispute" CTA + DMCA/corrections email. Public POST `/api/disputes` (rate-limited 3/24h per email, validates target exists), admin queue at `/admin/disputes` with approve/reject + internal review notes, auto-email-to-admin on submission via Resend. New page `/dispute?type=trust|live&slug=...` for operator submissions. Critical for affiliate-network approval + defamation defense.
- **Softened legal language** (Feb 2026): Claude trust-report system prompt updated to use measured language ("Reputable", "Generally Trusted", "Caution Advised", "High Risk", "Insufficient Information") instead of "Likely Scam"; AI is now explicitly instructed to "describe observed patterns" rather than assert criminal conduct. Frontpage `HowItWorks` copy + technique #1 description softened similarly. "Scam Wall" brand name retained (user-aggregated complaints with clear attribution).
- **SEO long-form articles** (Feb 2026): 4 of 8 techniques upgraded to full ~1750-word editorial articles (near-miss, delayed-withdrawal, bonus-traps, slow-reveal). Content stored in `/app/backend/technique_articles.py` and merged into `TECHNIQUES_SEED` at API read time. Frontend `/techniques/:slug` page renders the long-form with hero subhead, 9 H2 sections, FAQ panels (drives Google "People also ask"), related-technique link cards, dual CTAs (analyze + live). SEO meta tags + Open Graph + JSON-LD Article + FAQPage schemas injected. Sitemap.xml priority bumped to 0.9 for articles. "Deep dive" badge on the listing page distinguishes long-form from short dossier.
- **Reddit seeding playbook** (Feb 2026): `/app/memory/REDDIT_PLAYBOOK.md` — full operator manual for organic acquisition via r/onlinegambling, r/Crypto_Casinos, r/SlotMachineLasVegas. Covers account preparation, 5 post archetypes (story, pattern-recognition, TIL, math-breakdown, AMA), posting cadence, link-without-getting-banned rules, engagement compound tactics, and month-by-month success metrics. Pairs each post archetype to one of the 4 long-form articles.
- **Reddit landing page** (Feb 2026): `/r` (short URL for sharing) and `/from-reddit` — detects `utm_campaign=<article-slug>` and renders a tailored hero per campaign (`near-miss`, `delayed-withdrawal`, `bonus-traps`, `slow-reveal`). Single-email signup auto-generates a strong password (16-char crypto-random), shows it once with copy-button, attributes via new `signup_source` field on user doc. Backend admin endpoint `/api/admin/signup-sources` aggregates signups by source with premium-conversion counts for ROI analysis. AuthContext.signup now accepts options-object form (backwards compat preserved). Routes wired at `/r` AND `/from-reddit`.
- **Mobile navbar** (Feb 2026): hamburger toggle visible < 768px, slide-down drawer with all nav items, auth controls in drawer footer, body-scroll lock, auto-close on route change.
- **Launch-readiness P0 trio** (Feb 2026):
  - `/privacy`, `/terms`, `/editorial-standards` static pages — affiliate-network compliance + defamation defense.
  - **Cost controls**: signup rate-limit (5 per IP per hour via DB-backed `signup_attempts` collection), legitimacy-report LLM result cache (24h TTL, deduplication via `casino_name_lower` field, `is_cache_seed` / `served_from_cache` flags, savings reported in admin dashboard).
  - **Consolidated `/admin` dashboard**: `/api/admin/dashboard` single endpoint returns users/MRR/LLM costs/moderation queue/recent signups/top sources in one call. Frontend dashboard has 4 KPI cards (Users, MRR, LLM-spend-today with budget burn-rate color, Moderation queue), per-source 30d attribution table with premium conversion %, LLM cost breakdown today, recent signups list, quick-links to other admin pages. Burn-rate alert appears when daily LLM spend exceeds $25.
  - **3-email onboarding sequence**: welcome email fired immediately on signup (best-effort via Resend), day-2 (5 techniques) + day-5 (Premium pitch) triggered via `/api/admin/onboarding/run` (idempotent, safe to call daily — needs cron later). `email_log` collection dedupes.
  - **Sitewide Footer** with editorial/legal links.
- **Admin unlimited bypass** (Feb 2026): Admin users (via `ADMIN_EMAIL` env var) now bypass ALL freemium quotas — `check_free_quota` and `bump_free_quota` short-circuit on `is_admin_user(user)`, and live mode treats admin as unlimited (no trial gating, 3-min sessions). `QuotaBanner` UI also hidden for admin.
- 51/51 backend tests pre-Stripe + 12/14 post-Stripe + 18/18 forgot/live tests = current overall pass rate 100% on covered surface.

## Prioritized backlog
- **P1** — Live screen capture via `getDisplayMedia` (browser screen-share) → periodic frame analysis
- **P1** — Public, shareable trust reports (e.g. /report/:id)
- **P2** — Upload size limits + GridFS / object storage migration
- **P2** — Auto-cleanup of upload files after analysis
- **P2** — Tighten KNOWN_CASINOS substring matching (avoid false matches on short queries)
- **P2** — Real-time RTP lookup via gambling regulator open APIs (UKGC, MGA)
- **P3** — Community-submitted casino reports + moderation
- **P3** — Browser extension to flag dark patterns while you play

## Test credentials
See `/app/memory/test_credentials.md`
