import { useEffect, useMemo, useState } from "react";
import { useNavigate, useSearchParams, Link } from "react-router-dom";
import { api } from "../lib/api";
import { useAuth } from "../context/AuthContext";
import { toast } from "sonner";
import {
  ArrowRight,
  Radio,
  ScanLine,
  AlertTriangle,
  Loader2,
  ChevronRight,
} from "lucide-react";

/**
 * Reddit-attribution landing page at /r
 *
 * Detects ?utm_source=reddit and ?utm_campaign=<technique-slug> to render
 * a tailored hero matching the article that brought them in.
 *
 * Conversion path:
 *   Reddit → /r?utm_campaign=delayed-withdrawal
 *   → 60-second summary + one-field email capture
 *   → instant signup with auto-generated random password (passwordless feel)
 *   → email containing magic-link OR redirect to /legitimacy with a "scan now" CTA
 *
 * We do NOT use a magic-link flow here (Resend DNS isn't verified yet);
 * we use a one-field form that auto-generates a strong password and shows
 * it once with a "save your password" reminder. That keeps friction minimal
 * while preserving the user's ability to log back in.
 */

// Tailored copy per Reddit campaign (matches each long-form article)
const CAMPAIGN_HOOKS = {
  "near-miss": {
    eyebrow: "The thread about near-miss programming",
    headline: "Your slot machine is engineered to feel like you almost won.",
    body: "Most modern slots weight the third reel so 'two-out-of-three jackpot symbols' appears far more often than chance would predict. The UK regulator restricted the practice in 2018. Most offshore casinos still run it at full intensity. Scan any clip and our AI flags it frame-by-frame.",
    proof: "9-minute deep dive with the Kassinove & Schare (2001) research and how to spot it",
    article_slug: "near-miss",
    primary_cta: "SCAN A CLIP NOW",
    primary_to: "/analyze",
  },
  "delayed-withdrawal": {
    eyebrow: "The thread about KYC stalls",
    headline: "Your withdrawal isn't being processed. It's being engineered to expire.",
    body: "Reverse-withdrawal buttons. Document-rejection theatre. 'Source of funds' verification on a $200 deposit. These aren't accidents — they're a retention playbook designed to bore you into re-depositing. The single most important behavior: never click reverse-withdrawal.",
    proof: "11-minute breakdown of the 5-stage stall and which regulators actually enforce SLAs",
    article_slug: "delayed-withdrawal",
    primary_cta: "VERIFY A CASINO BEFORE DEPOSITING",
    primary_to: "/legitimacy",
  },
  "bonus-traps": {
    eyebrow: "The math thread about bonuses",
    headline: "Your 'free $500 bonus' has a negative expected value of $1,100.",
    body: "Welcome bonuses combine 40x+ wagering requirements, game weighting, max-bet tripwires, and bonus-deposit pooling to mathematically guarantee a loss. We did the actual math on a typical offer and the 'free' money costs you, on average, $1,100. There are a few good bonuses — they're the exception.",
    proof: "10-minute math walkthrough and what 'good' bonus terms look like",
    article_slug: "bonus-traps",
    primary_cta: "VERIFY A CASINO BEFORE DEPOSITING",
    primary_to: "/legitimacy",
  },
  "slow-reveal": {
    eyebrow: "The thread about LDWs",
    headline: "When the slot celebrates a 'win' smaller than your bet — that's not winning.",
    body: "It's called a Loss Disguised as a Win (LDW). 20 years of behavioral research, ubiquitous in modern slot design, restricted by the UK regulator in 2018, and still running full-strength on offshore casinos. The audio is the weapon. Mute it and the manipulation loses 60-70% of its power.",
    proof: "9-minute deep dive with the Dixon (2010) and Barton (2014) research",
    article_slug: "slow-reveal",
    primary_cta: "SCAN A CLIP NOW",
    primary_to: "/analyze",
  },
};

const DEFAULT_HOOK = {
  eyebrow: "From the Reddit thread",
  headline: "We built the forensic tools that show exactly how casinos manipulate you.",
  body: "AI-driven frame-by-frame analysis. Per-operator trust scores. Live screen-capture mode. A growing library of every documented manipulation pattern. Built by — and for — people who have already been burned once.",
  proof: "8 forensic techniques documented. 4 deep-dive research articles. Live scan tools.",
  article_slug: null,
  primary_cta: "SCAN YOUR FIRST GAME",
  primary_to: "/analyze",
};

function generateStrongPassword() {
  const chars = "abcdefghijkmnpqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ23456789!@#$%";
  let out = "";
  const arr = new Uint32Array(16);
  crypto.getRandomValues(arr);
  for (let i = 0; i < 16; i++) out += chars[arr[i] % chars.length];
  return out;
}

export default function FromReddit() {
  const [params] = useSearchParams();
  const nav = useNavigate();
  const { user, login, signup } = useAuth();

  const campaign = (params.get("utm_campaign") || "").toLowerCase();
  const hook = useMemo(() => CAMPAIGN_HOOKS[campaign] || DEFAULT_HOOK, [campaign]);

  const [email, setEmail] = useState("");
  const [busy, setBusy] = useState(false);
  const [generatedPassword, setGeneratedPassword] = useState("");

  useEffect(() => {
    document.title = `${hook.headline} · Casino Spotter`;
    let meta = document.querySelector('meta[name="description"]');
    if (!meta) {
      meta = document.createElement("meta");
      meta.name = "description";
      document.head.appendChild(meta);
    }
    meta.content = hook.body.slice(0, 155);
  }, [hook]);

  const handleQuickSignup = async (e) => {
    e.preventDefault();
    if (!email.includes("@")) {
      return toast.error("Enter a valid email");
    }
    setBusy(true);
    const password = generateStrongPassword();
    try {
      await signup({
        email: email.trim(),
        password,
        name: email.split("@")[0].slice(0, 24),
        signup_source: `reddit:${campaign || "generic"}`,
      });
      setGeneratedPassword(password);
      toast.success("Welcome aboard. Your password is shown once — save it.");
    } catch (err) {
      const msg = err?.response?.data?.detail || "Could not sign up";
      if (msg.toLowerCase().includes("already")) {
        // Account exists — pivot to login state
        toast.info("That email already has an account. Heading to login.");
        nav("/login");
      } else {
        toast.error(msg);
      }
    } finally {
      setBusy(false);
    }
  };

  // Already-signed-in user shortcut
  if (user && !generatedPassword) {
    return (
      <div className="max-w-3xl mx-auto px-6 py-20" data-testid="from-reddit-signed-in">
        <p className="text-xs uppercase tracking-[0.3em] text-[var(--neon)] mb-2">{hook.eyebrow}</p>
        <h1 className="font-heading text-3xl md:text-4xl tracking-tighter mb-4 leading-tight">
          You&apos;re already signed in. Go straight to the scan.
        </h1>
        <div className="flex flex-wrap gap-3">
          <Link to={hook.primary_to} className="btn-neon text-xs" data-testid="from-reddit-signed-in-cta">
            {hook.primary_cta} <ArrowRight className="w-3 h-3 inline ml-1" />
          </Link>
          {hook.article_slug && (
            <Link to={`/techniques/${hook.article_slug}`} className="btn-ghost text-xs">
              Read the full article first
            </Link>
          )}
        </div>
      </div>
    );
  }

  // Post-signup success state
  if (generatedPassword) {
    return (
      <div className="max-w-3xl mx-auto px-6 py-16" data-testid="from-reddit-success">
        <p className="text-xs uppercase tracking-[0.3em] text-[var(--neon)] mb-2">// account created</p>
        <h1 className="font-heading text-3xl md:text-4xl tracking-tighter mb-4 leading-tight">
          Welcome. Save your password — we won&apos;t show it again.
        </h1>
        <div className="panel p-5 mb-6 border border-[var(--warn)]/40 bg-black/60">
          <p className="text-[10px] uppercase tracking-widest text-[var(--warn)] mb-2">YOUR PASSWORD (one-time display)</p>
          <code className="text-base text-[var(--neon)] font-mono break-all" data-testid="from-reddit-password">{generatedPassword}</code>
          <button
            onClick={() => { navigator.clipboard.writeText(generatedPassword); toast.success("Password copied."); }}
            className="block mt-3 text-[11px] font-mono text-white/60 underline hover:text-[var(--neon)]"
            data-testid="from-reddit-copy-password"
          >
            Copy to clipboard
          </button>
          <p className="text-[10px] font-mono text-white/40 mt-3">
            We auto-generated this to save you a step. You can change it anytime under your profile.
          </p>
        </div>

        <h2 className="font-heading text-xl tracking-tight mb-3">Ready to run your first scan</h2>
        <div className="flex flex-wrap gap-3 mb-10">
          <Link to={hook.primary_to} className="btn-neon text-xs" data-testid="from-reddit-success-primary">
            {hook.primary_cta} <ArrowRight className="w-3 h-3 inline ml-1" />
          </Link>
          {hook.article_slug && (
            <Link to={`/techniques/${hook.article_slug}`} className="btn-ghost text-xs">
              Read the full article
            </Link>
          )}
        </div>
      </div>
    );
  }

  // Main landing
  return (
    <div className="max-w-5xl mx-auto px-6 md:px-12 py-12" data-testid="from-reddit-page">
      {/* Reddit attribution badge */}
      <div className="inline-flex items-center gap-2 mb-4 px-3 py-1 border border-[var(--neon)]/40 text-[10px] uppercase tracking-widest font-mono text-[var(--neon)]" data-testid="from-reddit-badge">
        <span className="w-1.5 h-1.5 rounded-full bg-[var(--neon)] animate-pulse" />
        {hook.eyebrow}
      </div>

      {/* Headline */}
      <h1 className="font-heading text-4xl md:text-6xl tracking-tighter mb-5 leading-[1.02]" data-testid="from-reddit-headline">
        {hook.headline}
      </h1>

      {/* 60-second summary */}
      <p className="text-base md:text-lg leading-relaxed text-white/85 font-mono mb-3 max-w-3xl" data-testid="from-reddit-body">
        {hook.body}
      </p>
      <p className="text-xs font-mono text-white/50 mb-10 max-w-3xl">
        &gt; {hook.proof}
      </p>

      {/* Conversion form */}
      <div className="grid grid-cols-1 lg:grid-cols-5 gap-6 mb-12">
        <div className="lg:col-span-3 panel p-6 border border-[var(--neon)]/30">
          <h2 className="text-xs uppercase tracking-[0.3em] text-[var(--neon)] mb-2">// start scanning</h2>
          <h3 className="font-heading text-2xl tracking-tight mb-3">One email. No password to invent.</h3>
          <p className="text-xs font-mono text-white/60 mb-5 leading-relaxed">
            We&apos;ll auto-generate a strong password for you and show it once. Your first scan is free.
            No credit card. We don&apos;t sell email lists.
          </p>
          <form onSubmit={handleQuickSignup} className="space-y-3" data-testid="from-reddit-form">
            <input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@email.com"
              className="input-neon"
              data-testid="from-reddit-email"
            />
            <button
              type="submit"
              disabled={busy}
              className="btn-neon w-full flex items-center justify-center gap-2 text-sm"
              data-testid="from-reddit-submit"
            >
              {busy ? <Loader2 className="w-4 h-4 animate-spin" /> : <ScanLine className="w-4 h-4" />}
              {busy ? "CREATING ACCOUNT..." : "CREATE ACCOUNT + SCAN >_"}
            </button>
            <p className="text-[10px] font-mono text-white/40 text-center">
              Already have an account? <Link to="/login" className="text-[var(--neon)] underline" data-testid="from-reddit-login-link">Sign in</Link>
            </p>
          </form>
        </div>

        <aside className="lg:col-span-2 panel p-6 bg-black/40">
          <h3 className="text-xs uppercase tracking-widest text-white/60 mb-3 font-heading">What you get</h3>
          <ul className="space-y-3 text-xs font-mono text-white/75">
            <li className="flex gap-2">
              <ChevronRight className="w-3 h-3 text-[var(--neon)] mt-0.5 shrink-0" />
              <span>1 free video scan (3 min cap) — Gemini 3 Flash frame-by-frame</span>
            </li>
            <li className="flex gap-2">
              <ChevronRight className="w-3 h-3 text-[var(--neon)] mt-0.5 shrink-0" />
              <span>1 free casino trust report — Claude Sonnet 4.5 forensic audit</span>
            </li>
            <li className="flex gap-2">
              <ChevronRight className="w-3 h-3 text-[var(--neon)] mt-0.5 shrink-0" />
              <span>1 free live screen-capture session (60s trial)</span>
            </li>
            <li className="flex gap-2">
              <ChevronRight className="w-3 h-3 text-[var(--neon)] mt-0.5 shrink-0" />
              <span>Full access to all 8 manipulation-technique articles</span>
            </li>
            <li className="flex gap-2">
              <ChevronRight className="w-3 h-3 text-[var(--neon)] mt-0.5 shrink-0" />
              <span>Scam Wall + voting on community complaints</span>
            </li>
          </ul>
        </aside>
      </div>

      {/* Read the full article CTA */}
      {hook.article_slug && (
        <div className="panel p-5 flex items-center justify-between gap-4 flex-wrap" data-testid="from-reddit-article-cta">
          <div>
            <p className="text-[10px] uppercase tracking-widest text-white/40 font-mono mb-1">prefer to read first?</p>
            <p className="text-sm font-mono text-white/80">
              The full <strong className="text-white">{CAMPAIGN_HOOKS[campaign]?.article_slug?.replace(/-/g, " ")}</strong> article with research citations.
            </p>
          </div>
          <Link to={`/techniques/${hook.article_slug}`} className="btn-ghost text-xs whitespace-nowrap">
            Read deep dive <ArrowRight className="w-3 h-3 inline ml-1" />
          </Link>
        </div>
      )}

      {/* Other techniques to explore */}
      <div className="mt-12">
        <h3 className="text-xs uppercase tracking-widest text-white/50 font-mono mb-3">Other deep-dive articles</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {Object.entries(CAMPAIGN_HOOKS)
            .filter(([slug]) => slug !== campaign)
            .map(([slug, h]) => (
              <Link
                key={slug}
                to={`/techniques/${slug}`}
                className="panel p-4 hover:bg-white/[0.02] transition group"
                data-testid={`from-reddit-other-${slug}`}
              >
                <p className="text-[10px] uppercase tracking-widest text-[var(--neon)] mb-1">technique</p>
                <p className="font-heading text-sm text-white mb-1 group-hover:text-[var(--neon)] transition">
                  {h.headline}
                </p>
              </Link>
            ))}
        </div>
      </div>
    </div>
  );
}
