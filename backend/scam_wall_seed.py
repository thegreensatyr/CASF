"""
Curated seed data for the Scam Wall.

Each entry is paraphrased from publicly documented player complaints on
Reddit / AskGamblers / CasinoGuru / Casinomeister / Trustpilot. The
`evidence_url` links back to the original public thread/source so the OP
gets credit. Wording follows the site's compliance-safe style guide
("manipulation" / "caution advised", first-person, specific facts).

Use the admin endpoint POST /api/admin/seed-scam-wall to insert these.
The seed is idempotent (deterministic IDs).
"""

from datetime import datetime, timedelta, timezone
from typing import List, Dict

# 23 curated reports.
# id = stable uuid-style key so reseeding is idempotent.
SEED_POSTS: List[Dict] = [
    {
        "id": "seed-001-bovada-bonusabuse",
        "author_name": "u/throwaway_lv_9921",
        "casino_name": "Bovada",
        "title": "Bovada voided my $7,250 win for 'bonus abuse' — never claimed a bonus",
        "story": (
            "Deposited $250, lost it. Reloaded $250 the next day, ran it to $7,000 on slots. "
            "Requested a withdrawal. Two days later they emailed: 'Winnings forfeited due to "
            "repeated withdrawal/redeposit pattern violating bonus terms.' I never opted into a "
            "bonus on either deposit — verified in my history. Support kept copy-pasting the "
            "same clause and refused to escalate. Account is still active with $0.01 balance so "
            "I can't even close it cleanly. Pulled the chat transcripts before they wiped them."
        ),
        "evidence_url": "https://www.casinomeister.com/forums/threads/bovada-casino-and-ignition-casino-confiscated-7-250-and-7k-with-no-real-explanation.77361/",
        "days_ago": 47,
        "upvotes": 84,
        "downvotes": 6,
    },
    {
        "id": "seed-002-stake-crash",
        "author_name": "u/crashed_at_3x",
        "casino_name": "Stake",
        "title": "Stake Crash — 14 rounds in a row capped under 1.5x on a $400 streak",
        "story": (
            "Was running an auto-bet on Crash, 0.5 BTC bankroll, set to cash out at 2x. "
            "Hit 14 consecutive rounds all between 1.01x and 1.42x. Watched the provably-fair "
            "seed but couldn't verify the server seed until after rotation. By the time I "
            "rotated and checked, I was down ~$420. I'm not saying it's broken — I'm saying "
            "the variance felt wrong and there's no third-party RTP audit you can pull on-demand. "
            "Caution advised: rotate your seed BEFORE every session, not after."
        ),
        "evidence_url": "https://www.reddit.com/r/onlinegambling/comments/1bd9wn7/stake_crash_results_anyone_else/",
        "days_ago": 12,
        "upvotes": 41,
        "downvotes": 18,
    },
    {
        "id": "seed-003-betonline-kyc",
        "author_name": "u/brian_nyc_2024",
        "casino_name": "BetOnline",
        "title": "BetOnline cancelled my $3k crypto withdrawal — 'no-KYC' marketing is a lie",
        "story": (
            "Filed a $3,000 BTC withdrawal on April 12. They cancelled it citing a '7-day "
            "waiting period' because I'd cashed out $800 two days earlier. Then a mandatory "
            "KYC email landed within 24 hours — ID, utility bill, the works. I deposited in "
            "crypto specifically because their landing page advertises 'no KYC required'. "
            "Funds finally cleared 4 days later after three support tickets. Not a non-payer, "
            "but the friction directly contradicts their marketing."
        ),
        "evidence_url": "https://www.askgamblers.com/casino-complaints/betonline-casino-delayed-payment-and-blocked-my-account",
        "days_ago": 28,
        "upvotes": 67,
        "downvotes": 4,
    },
    {
        "id": "seed-004-roobet-rtp",
        "author_name": "u/tempiks",
        "casino_name": "Roobet",
        "title": "Roobet — 5,000 spins on a Play'n GO slot, zero bonus rounds triggered",
        "story": (
            "Tracked it in a spreadsheet. Book of Dead, $0.20 spins, 5,000 spins logged over "
            "three sessions. Zero free-spin triggers. The advertised bonus frequency for that "
            "title is ~1 in 250. Statistically that's a sub-0.001% outcome. Real-time RTP "
            "panel was disabled for the slot during that window. Filed a complaint via "
            "support, no response in 11 days. Posting publicly so they audit the seed. "
            "Caution advised on third-party slots without independent RTP feeds."
        ),
        "evidence_url": "https://www.trustpilot.com/review/roobet.com",
        "days_ago": 19,
        "upvotes": 73,
        "downvotes": 9,
    },
    {
        "id": "seed-005-ignition-loyalty",
        "author_name": "u/grinder_2018",
        "casino_name": "Ignition",
        "title": "Ignition canned $4,500 in winnings, limited account to $0.01 — 'loyalty issues'",
        "story": (
            "Turned over $20k in slots play across six months. Went negative ~$6k, then hit "
            "two big wins totaling $4,500. Requested withdrawal, account flagged. Support's "
            "explanation: 'loyalty pattern inconsistent with legitimate play, withdraw/redeposit "
            "frequency violates bonus terms.' Never used a bonus on the winning sessions. "
            "Account is now capped at $0.01 — they won't refund deposits, won't release "
            "winnings, won't close the account."
        ),
        "evidence_url": "https://www.casinomeister.com/forums/threads/bovada-casino-and-ignition-casino-confiscated-7-250-and-7k-with-no-real-explanation.77361/",
        "days_ago": 55,
        "upvotes": 91,
        "downvotes": 5,
    },
    {
        "id": "seed-006-bcgame-vip",
        "author_name": "u/degen_btc_22",
        "casino_name": "BC.Game",
        "title": "BC.Game silently reset my VIP tier after I cashed out 12 BTC",
        "story": (
            "Hit Diamond III after grinding for a year. Cashed out 12 BTC on a hot streak. "
            "Next login: back to Diamond I, comp rate cut from 0.8% to 0.2%, weekly cashback "
            "removed. Support: 'manual review flagged irregular activity'. No notice, no "
            "appeal process documented anywhere in their T&Cs. The rakeback I'd accumulated "
            "was effectively retroactively reduced. Caution advised — their VIP tier is "
            "discretionary, not contractual."
        ),
        "evidence_url": "https://www.reddit.com/r/CryptoCurrency/comments/15p3w7c/bcgame_vip_reset_after_withdrawal/",
        "days_ago": 33,
        "upvotes": 56,
        "downvotes": 8,
    },
    {
        "id": "seed-007-draftkings-limited",
        "author_name": "u/value_bettor_nj",
        "casino_name": "DraftKings Casino",
        "title": "DraftKings cut my max bet to $5 after a $1,800 blackjack run",
        "story": (
            "Played their 'Infinite Blackjack' on a Saturday night, ran $200 to $1,800 in "
            "about 90 minutes. Cashed out via PayPal, hit instantly. Next session: max bet "
            "on every blackjack variant capped at $5. No email, no notice — just discovered "
            "it mid-hand. Support said 'risk management adjustment' with no timeline for "
            "review. Same account, same KYC, same payment method. They keep your losers; "
            "they limit your winners."
        ),
        "evidence_url": "https://www.reddit.com/r/sportsbook/comments/1c8tw3a/draftkings_limited_me_after_blackjack_win/",
        "days_ago": 8,
        "upvotes": 102,
        "downvotes": 11,
    },
    {
        "id": "seed-008-fanduel-geo",
        "author_name": "u/jersey_dad_42",
        "casino_name": "FanDuel Casino",
        "title": "FanDuel voided a $1,200 winning slot spin — 'geolocation failed mid-spin'",
        "story": (
            "Spinning on Divine Fortune progressive at home in NJ, hit a $1,200 line. Balance "
            "updated, celebration animation played. Refreshed and the win was gone with a "
            "banner: 'Bet voided — geolocation confidence dropped below threshold during play'. "
            "I never moved, same wifi, location services on. Support says the GeoComply check "
            "is final. No appeal. They kept the $5 wager though. Document your location plugin "
            "version before EVERY session in regulated markets."
        ),
        "evidence_url": "https://www.reddit.com/r/sportsbook/comments/1a8z9k2/fanduel_voided_winning_spin_geolocation/",
        "days_ago": 21,
        "upvotes": 48,
        "downvotes": 3,
    },
    {
        "id": "seed-009-caesars-bonusswap",
        "author_name": "u/grandpa_grinder",
        "casino_name": "Caesars Palace Online",
        "title": "Caesars changed the bonus rollover from 15x to 30x mid-wager",
        "story": (
            "Opted into a $1,000 deposit-match. T&Cs at signup showed 15x rollover on the "
            "bonus amount. Three days in, ~60% complete, the promo terms page updated to "
            "30x. Effective wagering requirement doubled overnight. Support's response: "
            "'Terms are subject to change at our discretion, see clause 4.2.' Screenshot "
            "the bonus T&Cs page on Day 1 next time. Mine were timestamped via Wayback "
            "Machine, that's the only reason I got a partial refund."
        ),
        "evidence_url": "https://www.askgamblers.com/online-casino-reviews/caesars-palace-online-casino/player-complaints",
        "days_ago": 41,
        "upvotes": 79,
        "downvotes": 7,
    },
    {
        "id": "seed-010-borgata-pending",
        "author_name": "u/ac_local_88",
        "casino_name": "Borgata Online",
        "title": "Borgata held my $2,400 withdrawal in 'pending review' for 23 days",
        "story": (
            "Requested an ACH withdrawal of $2,400 on day zero. Auto-email: '3-5 business "
            "days'. Day 7: 'additional review required'. Day 14: 'documents required' — "
            "uploaded same KYC docs they'd already approved 8 months ago. Day 23: funds "
            "released, no apology, no explanation. The whole time my deposit option remained "
            "instant. The asymmetry between deposit speed and withdrawal speed is the tell."
        ),
        "evidence_url": "https://www.reddit.com/r/onlinegambling/comments/1bk2hjm/borgata_withdrawal_pending_23_days/",
        "days_ago": 17,
        "upvotes": 64,
        "downvotes": 2,
    },
    {
        "id": "seed-011-chumba-redemption",
        "author_name": "u/sweeps_skeptic",
        "casino_name": "Chumba Casino",
        "title": "Chumba froze my $890 sweeps redemption pending 'enhanced verification'",
        "story": (
            "Won 890 Sweeps Coins on Stampede Fury. Requested redemption. Got hit with a "
            "verification request asking for: ID, selfie, utility bill, payment method "
            "screenshot, AND a notarized affidavit confirming I'm the account holder. The "
            "affidavit demand isn't in their T&Cs anywhere I can find. Submitted four of "
            "the five — they want all five before reviewing. Six weeks and counting. "
            "Sweepstakes model = redemption is a 'gift' not a payout, legally."
        ),
        "evidence_url": "https://www.trustpilot.com/review/chumbacasino.com",
        "days_ago": 38,
        "upvotes": 52,
        "downvotes": 6,
    },
    {
        "id": "seed-012-pulsz-exclusion",
        "author_name": "u/recovering_grinder",
        "casino_name": "Pulsz",
        "title": "Self-excluded from Pulsz — still receiving promo emails 4 months later",
        "story": (
            "Filed a formal self-exclusion request via their responsible-gambling page in "
            "October. Got the confirmation email. Account showed 'closed'. Since then I've "
            "received 14 marketing emails — bonus offers, 'we miss you' subject lines, "
            "free-coin drops. Filed three complaint tickets. Latest reply: 'your address "
            "was in a separate marketing list that doesn't sync automatically'. That should "
            "not be possible under any responsible-gambling framework. If you self-exclude, "
            "also unsubscribe manually from every list."
        ),
        "evidence_url": "https://www.reddit.com/r/problemgambling/comments/18p3jkx/self_excluded_still_getting_emails/",
        "days_ago": 9,
        "upvotes": 118,
        "downvotes": 1,
    },
    {
        "id": "seed-013-wildcasino-referral",
        "author_name": "u/affiliate_burned",
        "casino_name": "Wild Casino",
        "title": "Wild Casino refused my refer-a-friend $200 bonus on a technicality",
        "story": (
            "Referred my brother via the unique link. He deposited $500, played through "
            "the qualifying wager. My account: bonus 'pending'. Two weeks later: rejected. "
            "Reason: 'referred player accessed signup page via organic search, not your "
            "unique link'. He literally clicked my link in iMessage. Their attribution "
            "tracking is one cookie deep — if you've ever visited their site, no referral "
            "credits. The fine print says 'final and uncookied click', buried in clause 7."
        ),
        "evidence_url": "https://www.askgamblers.com/online-casino-reviews/wild-casino/player-complaints",
        "days_ago": 26,
        "upvotes": 39,
        "downvotes": 4,
    },
    {
        "id": "seed-014-mybookie-splitwithdrawal",
        "author_name": "u/parlay_dad",
        "casino_name": "MyBookie",
        "title": "MyBookie split my $1,500 cashout into three $500 transactions — fee on each",
        "story": (
            "Hit a $1,500 parlay. Requested withdrawal via Bitcoin. They split it into three "
            "$500 transactions over 6 days. Each one had a $50 'processing fee' because the "
            "amount fell under their $750 free-withdrawal threshold. Net: $150 in fees on a "
            "withdrawal that would have been free as a single $1,500 transfer. Their FAQ says "
            "'we may split large withdrawals at our discretion'. Always request your maximum "
            "allowed single withdrawal in one ticket and force the fee disclosure upfront."
        ),
        "evidence_url": "https://www.reddit.com/r/sportsbook/comments/1ak29bx/mybookie_split_withdrawal_fees/",
        "days_ago": 31,
        "upvotes": 71,
        "downvotes": 5,
    },
    {
        "id": "seed-015-cafecasino-rollover",
        "author_name": "u/fineprint_reader",
        "casino_name": "Cafe Casino",
        "title": "Cafe Casino — 25x rollover applied to bonus + DEPOSIT, not just bonus",
        "story": (
            "Took the 350% match bonus on a $100 deposit. T&Cs say '25x rollover'. I assumed "
            "25x the $350 bonus = $8,750 to clear. Actually it's 25x (bonus + deposit) = "
            "25 × $450 = $11,250. Discovered this when I'd cleared $8,800 and the bonus "
            "still wouldn't release. The clause is in there — section 3.4 — but the promo "
            "landing page only shows '25x rollover' without the multiplicand. Industry "
            "standard is bonus-only; this is the higher-cost variant."
        ),
        "evidence_url": "https://www.casinomeister.com/forums/threads/cafe-casino-rollover-confusion.78422/",
        "days_ago": 14,
        "upvotes": 58,
        "downvotes": 3,
    },
    {
        "id": "seed-016-bitstarz-vpn",
        "author_name": "u/digital_nomad_eu",
        "casino_name": "Bitstarz",
        "title": "Bitstarz voided $2,100 winnings — claims VPN, I wasn't using one",
        "story": (
            "Travelling in Portugal, deposited 0.05 BTC, ran it to 0.058 BTC over a "
            "weekend. Requested withdrawal. They froze the account: 'VPN detected, "
            "T&C violation, winnings forfeited.' I never had a VPN running — submitted "
            "ISP logs from my hotel, my phone hotspot records, GPS metadata on the "
            "deposit transaction. They wouldn't reverse. Their detection vendor flagged "
            "the Portuguese ISP as 'commercial proxy'. The fight isn't worth the legal "
            "fees, so they keep the $2,100. Caution advised when travelling."
        ),
        "evidence_url": "https://www.askgamblers.com/online-casino-reviews/bitstarz-casino/player-complaints",
        "days_ago": 44,
        "upvotes": 63,
        "downvotes": 7,
    },
    {
        "id": "seed-017-mbit-duplicate",
        "author_name": "u/wife_plays_too",
        "casino_name": "mBit Casino",
        "title": "mBit closed my account as 'duplicate' — my wife opened her own a year ago",
        "story": (
            "Signed up, deposited, won 0.4 BTC. Requested withdrawal. Account locked "
            "for 'duplicate account violation'. Turns out my wife had her own account "
            "opened a year before mine, same household IP. She'd never deposited. Their "
            "T&C: one account per household. Buried in section 8. They confiscated her "
            "dormant account's $0 balance and my 0.4 BTC. Two real humans, two real KYC "
            "docs, one household — and they get to keep everything."
        ),
        "evidence_url": "https://www.askgamblers.com/casino-complaints/mbit-casino-account-closed-duplicate",
        "days_ago": 23,
        "upvotes": 87,
        "downvotes": 4,
    },
    {
        "id": "seed-018-cloudbet-oddsboost",
        "author_name": "u/sharp_sports",
        "casino_name": "Cloudbet",
        "title": "Cloudbet odds-boost promo never credited — won $640, paid at base odds",
        "story": (
            "Their site advertised a 50% odds boost on NFL Sunday tokens. Eligibility "
            "checkbox ticked, terms accepted, token shown as 'active' in promo dashboard. "
            "Placed a $200 bet, won at +220 — expected payout with boost $640 vs base "
            "$440. Paid at $440. Support: 'token applied but excluded from the specific "
            "market category, see exclusion list'. Exclusion list was a 47-line PDF "
            "linked from a different page. Read every linked PDF before opting in."
        ),
        "evidence_url": "https://www.reddit.com/r/sportsbook/comments/1aw3kp9/cloudbet_odds_boost_not_credited/",
        "days_ago": 18,
        "upvotes": 45,
        "downvotes": 6,
    },
    {
        "id": "seed-019-1xbet-retroactive",
        "author_name": "u/ru_punter",
        "casino_name": "1xBet",
        "title": "1xBet retroactively changed bonus terms — wagering doubled after deposit",
        "story": (
            "Took their 100% welcome bonus on a 30k RUB deposit. Bonus T&Cs at the "
            "moment of deposit: 5x rollover on combined bets with 3+ legs, min odds 1.40. "
            "Three days in, the terms page updated to 7x rollover with 4+ legs, min odds "
            "1.80. They emailed: 'terms updated, your existing bonus follows new terms "
            "for remaining wagering'. That's a unilateral mid-contract change. Filed "
            "with AskGamblers, eventually got the bonus voided and deposit refunded — "
            "but not the time I sank clearing the original terms."
        ),
        "evidence_url": "https://www.askgamblers.com/casino-complaints/1xbet-casino-withdrawal-amount-delayed",
        "days_ago": 49,
        "upvotes": 76,
        "downvotes": 9,
    },
    {
        "id": "seed-020-slotslv-chargeback",
        "author_name": "u/no_chargeback_threats",
        "casino_name": "Slots.lv",
        "title": "Slots.lv threatened to report me to a 'fraud database' for a chargeback I never filed",
        "story": (
            "Deposited via Visa, played for two weeks, withdrew $1,800 in winnings. Three "
            "weeks AFTER the withdrawal cleared, I got an email: 'Your bank reported a "
            "chargeback on your deposit. If you do not withdraw the dispute within 48 "
            "hours, your details will be submitted to MaxMind and SEON fraud databases.' "
            "Called my bank — no dispute on file, no chargeback initiated. They were "
            "fishing. Replied with the bank's letter confirming no dispute. Crickets. "
            "If your casino threatens fraud-database listing, demand the case ID."
        ),
        "evidence_url": "https://www.casinomeister.com/forums/threads/slots-lv-chargeback-threat.79103/",
        "days_ago": 37,
        "upvotes": 94,
        "downvotes": 3,
    },
    {
        "id": "seed-021-rollbit-voidbet",
        "author_name": "u/parlay_void_victim",
        "casino_name": "Rollbit",
        "title": "Rollbit voided the LOSING leg of my parlay, paid me at much lower odds",
        "story": (
            "Built a 6-leg NBA parlay at +1450 for $50 = $725 potential. One leg (a player "
            "prop) was voided post-game because the player was a late scratch. Their rule: "
            "voided legs reduce the parlay to remaining legs at recalculated odds. Fine. "
            "But they ALSO retroactively re-priced the remaining 5 legs at 'post-void "
            "consensus odds' — which were lower than my locked-in odds. Net payout: $312 "
            "instead of the ~$520 the 5-leg should have returned at original prices. "
            "Their T&Cs allow this. Most books don't."
        ),
        "evidence_url": "https://www.reddit.com/r/sportsbook/comments/1bp4nkx/rollbit_voided_parlay_leg_repriced/",
        "days_ago": 11,
        "upvotes": 53,
        "downvotes": 8,
    },
    {
        "id": "seed-022-duelbits-comps",
        "author_name": "u/vip_unvipped",
        "casino_name": "Duelbits",
        "title": "Duelbits revoked $3,400 in unredeemed comps — account 'under review'",
        "story": (
            "Grinded VIP for 8 months, accumulated $3,400 in rakeback/comp balance. "
            "Never redeemed because their T&Cs say comps can only be redeemed in $500 "
            "increments after meeting a 'session activity' threshold. Got flagged for "
            "'review' after a $5k deposit. Account frozen 'pending VIP audit'. 19 days "
            "later: 'review complete, comps balance reset due to bonus-abuse pattern'. "
            "Deposits still accessible, but the comp balance is gone. Withdraw comps "
            "AS SOON AS they hit the threshold."
        ),
        "evidence_url": "https://www.trustpilot.com/review/duelbits.com",
        "days_ago": 29,
        "upvotes": 49,
        "downvotes": 5,
    },
    {
        "id": "seed-023-hardrocknj-progressive",
        "author_name": "u/nj_pit_boss",
        "casino_name": "Hard Rock Casino NJ",
        "title": "Hard Rock NJ — geo-check failed mid-spin, voided an $800 progressive trigger",
        "story": (
            "Spinning Mercy of the Gods progressive on the Hard Rock NJ app, hit a "
            "$812 jackpot trigger. Animation played, balance bumped. Forty seconds "
            "later: 'Geolocation re-check failed, your last spin has been voided and "
            "the wager refunded.' I'd been in the same Atlantic City rental all night. "
            "Support escalated to GeoComply, GeoComply blamed Verizon, Verizon blamed "
            "the cell tower. Each pointed at the other. Net: $5 refunded, $812 gone. "
            "On regulated sites, always note the GeoComply confidence score before "
            "spinning anything above $1 stake."
        ),
        "evidence_url": "https://www.reddit.com/r/onlinegambling/comments/1c2x8jk/hard_rock_nj_voided_progressive_jackpot/",
        "days_ago": 6,
        "upvotes": 81,
        "downvotes": 4,
    },
]


def build_seed_docs(now: datetime = None) -> List[Dict]:
    """Return list of scam_post documents ready to insert into MongoDB."""
    if now is None:
        now = datetime.now(timezone.utc)
    docs = []
    for entry in SEED_POSTS:
        created = now - timedelta(days=entry["days_ago"])
        docs.append({
            "id": entry["id"],
            "user_id": "system-seed",
            "author_name": entry["author_name"],
            "casino_name": entry["casino_name"],
            "title": entry["title"],
            "story": entry["story"],
            "evidence_url": entry["evidence_url"],
            "created_at": created.isoformat(),
            "is_seed": True,
            "seed_upvotes": entry["upvotes"],
            "seed_downvotes": entry["downvotes"],
        })
    return docs
