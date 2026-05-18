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
- 100% backend test pass: 15/15 core + 18/18 scam wall = **33/33 total**

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
