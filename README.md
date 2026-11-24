# CasinoForensicsUnit website

Plain HTML, CSS and a little JavaScript. No paywalls, no page builder, no third-party badges.

## What's here

| File / folder | What it is |
|---|---|
| `index.html` | Home page |
| `check-a-site.html` | Site checker page (tool not switched on yet — form is disabled on purpose) |
| `casinos.html` | Verified casino list (empty until real, sourced records exist) |
| `scam-wall.html` | Scam Wall (empty until real, sourced entries exist) |
| `psychology.html` | Psychology Library (DRAFT — needs your review) |
| `how-we-rate.html` | The CFU Verified standard (DRAFT — needs your approval) |
| `disclosure.html` | Affiliate disclosure (DRAFT — needs your review) |
| `responsible-gambling.html` | Helpline and support info |
| `css/style.css` | All the colors and styling (citrus palette is at the top) |
| `assets/logo.svg`, `assets/logo-mark.svg` | The copper-wire logo (full lockup with name, and the mark alone used in the header and browser tab) |
| `data/casinos.json` | The casino records. Starts empty. |
| `scripts/deploy-check.js` | The launch gate. Blocks deploy if anything is unfinished or unsourced. |

## The rules this site is built on

The last site went live with made-up stats. So:

1. **No number, rating or claim goes on the site without a real source.**
2. **A casino only appears if every field has a source link (https) and a "checked on" date.** The page code refuses to show incomplete records.
3. **The launch check must pass before you deploy.** Run `node scripts/deploy-check.js`. Right now it is *supposed* to fail, because the three draft pages still need your approval.

## Still needed before launch

- [x] Logo: redrawn from scratch in copper wire (`assets/logo.svg` full version, `assets/logo-mark.svg` header/icon). Swap in your original later if you find it.
- [ ] You read and approve (or change) the wording of the three DRAFT pages, then the `<!-- DRAFT ... -->` line at the top of each is removed
- [ ] The scoring/standard on `how-we-rate.html` approved by you
- [ ] Real casino records added to `data/casinos.json`, with sources
- [ ] A domain name and a hosting choice (Netlify, linked to a GitHub repo)

## Adding a casino (once it has really passed the standard)

Each record in `data/casinos.json` looks like this. Every part must be real, and every `sourceUrl` must be a real link to the evidence:

```json
{
  "name": "Casino Name",
  "status": "verified",
  "type": "real-money or sweepstakes",
  "payoutMethods": ["cash", "crypto"],
  "verifiedOn": "YYYY-MM-DD",
  "license": { "value": "what the license/legal status is", "sourceUrl": "https://...", "checkedOn": "YYYY-MM-DD" },
  "redemptionTest": { "value": "what you tested, amount, how long it took", "sourceUrl": "https://... (or screenshot link)", "checkedOn": "YYYY-MM-DD" },
  "termsReviewed": { "value": "the key rules, quoted", "sourceUrl": "https://...", "checkedOn": "YYYY-MM-DD" },
  "stateAvailability": { "value": "where it is available / restricted", "sourceUrl": "https://...", "checkedOn": "YYYY-MM-DD" }
}
```

Ask Claude to add a record and it will refuse to fill in anything you haven't given it.

## To look at the site on your computer

Ask Claude to start the preview, or open `index.html` in Chrome.
