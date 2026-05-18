import { Link } from "react-router-dom";
import { ArrowLeft, Copy, Check } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";

const APPLICATION_DRAFT = `Site Name: Casino Spotter
Site URL: https://scam-spotter-casino.preview.emergentagent.com
Site Type: Educational / consumer-protection tool

Site Description:
Casino Spotter is an AI-powered consumer-protection platform for online casino players. It uses Google Gemini multimodal AI to analyze user-uploaded video clips and screenshots of casino sessions, then explains in plain language any manipulation techniques being used (near-miss programming, losses-disguised-as-wins, RTP manipulation, etc.). It also runs Claude-powered trust assessments on any casino operator and maintains a community "Scam Wall" where players publish and vote on operator complaints.

Audience:
Recreational online casino players in English-speaking markets (UK, IE, CA, AU, NZ, US-regulated states) who have either been scammed by a rogue operator or who want to verify a casino before depositing. Estimated 18–55, gambling-active.

Monthly Traffic:
Currently pre-launch / soft launch. Projected 1,000–5,000 monthly visitors in the first 90 days based on niche keyword research (terms like "is X casino legit", "casino near-miss", "delayed casino withdrawal").

How We'll Promote:
Affiliate links appear contextually — only after a user has just learned their current casino is risky (low trust score, or AI-flagged manipulation). We exclusively promote operators with UKGC, MGA, or US state licensing. All links carry rel="nofollow sponsored" and a clear 18+ / BeGambleAware disclaimer. We do not target self-excluded users and we follow ASA/FTC disclosure rules.

Why We're a Strong Affiliate Partner:
Our audience has the highest possible purchase intent — they are actively researching where to play next, having just left or rejected a competitor. Educational/trust-led content has historically converted at 3–5× the rate of pure-affiliate review sites because we build credibility first, recommend second.

Preferred Payout Model: Hybrid (CPA + Rev Share)
Preferred Payment Method: Wise / bank transfer
Contact: [your email here]`;

export default function MonetizationGuide() {
  const [copied, setCopied] = useState(false);

  const copy = () => {
    navigator.clipboard.writeText(APPLICATION_DRAFT);
    setCopied(true);
    toast.success("Copied to clipboard");
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="max-w-4xl mx-auto px-6 md:px-12 py-12">
      <Link to="/admin/affiliates" className="inline-flex items-center gap-2 text-xs uppercase tracking-widest mb-6" data-testid="back-to-admin">
        <ArrowLeft className="w-3 h-3" /> Back to admin
      </Link>
      <p className="text-xs uppercase tracking-[0.3em] text-[var(--neon)] mb-2">// monetization playbook</p>
      <h1 className="font-heading text-4xl md:text-5xl tracking-tighter mb-3">QUICK-START GUIDE</h1>
      <p className="text-sm text-white/60 font-mono mb-10">&gt; From zero to your first affiliate dollar in ~7 days.</p>

      <Step n="01" title="Pick an affiliate network">
        <p>Affiliate networks are platforms that connect your site to dozens of casinos with one signup. Start with ONE:</p>
        <table className="w-full text-xs font-mono mt-4 border border-[var(--border)]">
          <thead>
            <tr className="bg-[var(--surface-2)]">
              <th className="text-left p-2 uppercase tracking-widest text-[var(--neon)]">Network</th>
              <th className="text-left p-2 uppercase tracking-widest text-[var(--neon)]">Casinos</th>
              <th className="text-left p-2 uppercase tracking-widest text-[var(--neon)]">URL</th>
            </tr>
          </thead>
          <tbody>
            <Row name="Income Access (Paysafe)" casinos="Bet365, BetMGM, LeoVegas, PokerStars + 100 more" url="incomeaccess.com" recommended />
            <Row name="NetRefer" casinos="PokerStars, Betsson, Mr Green" url="netrefer.com" />
            <Row name="MyAffiliates" casinos="Industry standard, many operators" url="myaffiliates.com" />
            <Row name="AffPower" casinos="30+ casino brands" url="affpower.com" />
          </tbody>
        </table>
        <p className="text-[10px] text-white/50 mt-3">&gt; Recommended: Income Access — biggest catalogue, fastest approval (2–7 days).</p>
      </Step>

      <Step n="02" title="Apply to the network">
        <p>They'll ask "describe your site". Use this draft (edit the contact line):</p>
        <div className="panel p-4 mt-4 scanlines relative">
          <button
            onClick={copy}
            className="absolute top-3 right-3 btn-ghost text-[10px] flex items-center gap-1"
            data-testid="copy-application"
          >
            {copied ? <><Check className="w-3 h-3"/> Copied</> : <><Copy className="w-3 h-3"/> Copy</>}
          </button>
          <pre className="text-[11px] font-mono text-white/85 whitespace-pre-wrap leading-relaxed pr-20">{APPLICATION_DRAFT}</pre>
        </div>
        <p className="text-[10px] text-white/50 mt-3">&gt; Most networks approve in 2–7 days. They verify your site is real content (yours is ✓).</p>
      </Step>

      <Step n="03" title="Pick the payout model">
        <ul className="space-y-2 mt-2">
          <li><span className="text-[var(--neon)] font-bold">CPA (Cost Per Acquisition)</span> — $50–$300 flat per depositing player. Predictable, one-shot.</li>
          <li><span className="text-[var(--neon)] font-bold">Revenue Share</span> — 25–45% of casino's lifetime profit from that player. Compounds for years.</li>
          <li><span className="text-[var(--neon)] font-bold">Hybrid</span> — smaller CPA + smaller rev share. Best of both. <span className="text-white/60">Recommended for starting out.</span></li>
        </ul>
      </Step>

      <Step n="04" title="Generate tracking links & plug in">
        <p>Once approved, in the network dashboard:</p>
        <ol className="list-decimal list-inside space-y-1 mt-2 text-white/80">
          <li>Browse the casino marketplace</li>
          <li>Pick 3–5 reputable casinos (<span className="text-[var(--neon)]">UKGC, MGA, or US state-licensed only</span>)</li>
          <li>Click "Get tracking link" — you'll receive a URL like <code className="text-[var(--neon)]">casino.com/?aff=YOUR_ID</code></li>
          <li>Go to <Link to="/admin/affiliates" className="text-[var(--neon)] underline">/admin/affiliates</Link> in this app</li>
          <li>Edit each demo casino (BetMGM/LeoVegas/PokerStars) and paste your real tracking link in the URL field</li>
          <li>Save. Your CTAs are now live and earning.</li>
        </ol>
      </Step>

      <Step n="05" title="Watch the numbers">
        <p>Every CTA click is logged to <Link to="/admin/affiliates" className="text-[var(--neon)] underline">/admin/affiliates</Link>. Once a week:</p>
        <ul className="list-disc list-inside space-y-1 mt-2 text-white/80">
          <li>See which casino gets the most clicks → push that one harder (raise sort order)</li>
          <li>Cross-check with your network's dashboard → which clicks actually converted into deposits</li>
          <li>Kill low-converters, replace them</li>
        </ul>
        <p className="text-[10px] text-white/50 mt-3">&gt; Realistic month-1 outcome: $0–$500. Month-6: $1,000–$5,000. Year-2: $10k+/mo if traffic grows.</p>
      </Step>

      <div className="panel p-6 mt-12 border-[var(--warn)]/40">
        <h3 className="font-heading text-sm text-[var(--warn)] uppercase tracking-widest mb-3">// compliance checklist</h3>
        <ul className="text-xs font-mono text-white/85 space-y-2">
          <li>✓ Only promote UKGC / MGA / US state-licensed operators (never offshore)</li>
          <li>✓ Already added: <code>rel="nofollow sponsored"</code> on all CTAs</li>
          <li>✓ Already added: 18+ + BeGambleAware disclaimer below every CTA</li>
          <li>✓ Get an LLC / sole-prop registered before payouts hit your account (tax + liability)</li>
          <li>✓ Never claim casinos are "guaranteed safe" — call them "licensed" or "audited"</li>
          <li>✓ Avoid Stripe/PayPal for receiving affiliate payments → use Wise or direct bank</li>
        </ul>
      </div>

      <div className="mt-10 flex flex-wrap gap-3">
        <Link to="/admin/affiliates" className="btn-neon" data-testid="goto-admin-affiliates">Open admin panel &gt;_</Link>
        <a href="https://www.incomeaccess.com/" target="_blank" rel="noopener noreferrer" className="btn-ghost">Open Income Access</a>
      </div>
    </div>
  );
}

function Step({ n, title, children }) {
  return (
    <section className="mb-12">
      <div className="flex items-baseline gap-4 mb-4">
        <span className="font-heading text-3xl text-[var(--neon)]">{n}</span>
        <h2 className="font-heading text-xl tracking-tight">{title}</h2>
      </div>
      <div className="text-sm font-mono text-white/80 leading-relaxed pl-12">{children}</div>
    </section>
  );
}

function Row({ name, casinos, url, recommended }) {
  return (
    <tr className="border-t border-[var(--border)]">
      <td className="p-2">
        {name}
        {recommended && <span className="ml-2 tag text-[10px]">recommended</span>}
      </td>
      <td className="p-2 text-white/70">{casinos}</td>
      <td className="p-2"><a href={`https://${url}`} target="_blank" rel="noopener noreferrer">{url}</a></td>
    </tr>
  );
}
