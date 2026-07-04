import { useState } from "react";
import { api } from "../lib/api";
import { toast } from "sonner";
import { Search, Loader2, ShieldCheck, ShieldAlert, ShieldX, Share2, Copy, Check, MessageSquareWarning, X } from "lucide-react";
import TrustedCasinoCTA from "../components/TrustedCasinoCTA";
import QuotaBanner from "../components/QuotaBanner";

export default function Legitimacy() {
  const [name, setName] = useState("");
  const [url, setUrl] = useState("");
  const [busy, setBusy] = useState(false);
  const [report, setReport] = useState(null);
  const [showDisagree, setShowDisagree] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    if (!name.trim()) return toast.error("Casino name required");
    setBusy(true); setReport(null);
    try {
      const { data } = await api.post("/legitimacy/research", {
        casino_name: name, casino_url: url || null,
      }, { timeout: 120000 });
      setReport(data);
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Lookup failed");
    } finally { setBusy(false); }
  };

  const scoreBadge = (s) => {
    if (s >= 75) return { Icon: ShieldCheck, color: "text-[var(--neon)] border-[var(--neon)]", label: "TRUSTED" };
    if (s >= 45) return { Icon: ShieldAlert, color: "text-[var(--warn)] border-[var(--warn)]", label: "CAUTIOUS" };
    return { Icon: ShieldX, color: "text-[var(--danger)] border-[var(--danger)]", label: "AVOID" };
  };

  return (
    <div className="max-w-6xl mx-auto px-6 md:px-12 py-12">
      <p className="text-xs uppercase tracking-[0.3em] text-[var(--neon)] mb-2">// trust check</p>
      <h1 className="font-heading text-4xl md:text-5xl tracking-tighter mb-2">VERIFY A CASINO</h1>
      <p className="text-sm text-white/60 font-mono mb-10">
        &gt; Curated blacklist + Claude Sonnet 4.5 forensic review.
      </p>

      <QuotaBanner type="trust" />

      <form onSubmit={submit} className="panel p-6 space-y-4 mb-6" data-testid="legit-form">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <label className="block">
            <span className="block text-xs uppercase tracking-widest text-white/60 mb-1 font-heading">CASINO NAME *</span>
            <input data-testid="legit-name" value={name} onChange={(e)=>setName(e.target.value)} className="input-neon" required/>
          </label>
          <label className="block">
            <span className="block text-xs uppercase tracking-widest text-white/60 mb-1 font-heading">URL (optional)</span>
            <input data-testid="legit-url" value={url} onChange={(e)=>setUrl(e.target.value)} className="input-neon" placeholder="https://"/>
          </label>
        </div>
        <button className="btn-neon" disabled={busy} data-testid="legit-submit">
          {busy ? (<span className="flex items-center gap-2"><Loader2 className="w-4 h-4 animate-spin"/>INVESTIGATING...</span>) : (<span className="flex items-center gap-2"><Search className="w-4 h-4"/>RUN TRUST CHECK &gt;_</span>)}
        </button>
      </form>

      {busy && (
        <div className="panel p-6 scanlines text-[var(--neon)] font-mono text-xs space-y-1">
          <div>&gt; checking curated blacklist...</div>
          <div>&gt; querying claude-sonnet-4.5...</div>
          <div>&gt; cross-referencing licensing jurisdictions</div>
          <div className="caret">&gt; compiling report</div>
        </div>
      )}

      {report && (() => {
        const b = scoreBadge(report.trust_score);
        const { Icon } = b;
        const shareUrl = `${window.location.origin}/report/${report.slug}`;
        const copyShare = () => {
          navigator.clipboard.writeText(shareUrl);
          toast.success("Public link copied — paste it anywhere");
        };
        return (
          <>
          <div className="flex items-center justify-between flex-wrap gap-3 mb-4 panel p-3 px-4">
            <div className="text-xs font-mono text-white/70 flex items-center gap-2">
              <Share2 className="w-3 h-3 text-[var(--neon)]" />
              <span>Public share URL:</span>
              <code className="text-[var(--neon)] text-[11px]" data-testid="share-url">{shareUrl}</code>
            </div>
            <button onClick={copyShare} className="btn-ghost text-xs flex items-center gap-1" data-testid="copy-share-url">
              <Copy className="w-3 h-3" /> Copy
            </button>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4" data-testid="legit-report">
            <div className={`panel p-6 ${b.color} border-2`}>
              <Icon className="w-8 h-8 mb-3" />
              <div className="text-[10px] uppercase tracking-[0.3em] text-white/60">trust score</div>
              <div className="font-heading text-5xl mt-1">{report.trust_score}<span className="text-white/40 text-2xl">/100</span></div>
              <div className={`mt-3 tag ${b.color}`}>{b.label}</div>
              <p className="text-xs font-mono text-white/70 mt-4">{report.verdict}</p>
              <button
                onClick={() => setShowDisagree(true)}
                data-testid="disagree-with-score-btn"
                className="mt-5 w-full inline-flex items-center justify-center gap-2 text-[10px] uppercase tracking-widest text-white/60 hover:text-[var(--neon)] transition border border-white/15 hover:border-[var(--neon)]/60 px-3 py-2 rounded"
              >
                <MessageSquareWarning className="w-3 h-3" /> disagree with score?
              </button>
            </div>

            <div className="panel p-6 md:col-span-2">
              <h3 className="font-heading text-lg mb-3 text-[var(--neon)]">// Report</h3>
              <p className="text-sm font-mono text-white/85 whitespace-pre-line leading-relaxed">{report.report}</p>
            </div>

            <div className="panel p-6 border-[var(--danger)]/40">
              <h3 className="font-heading text-sm mb-3 text-[var(--danger)] uppercase tracking-widest">Red flags</h3>
              {report.red_flags.length ? (
                <ul className="text-xs font-mono space-y-1 text-white/80">
                  {report.red_flags.map((f,i)=>(<li key={i}>&gt; {f}</li>))}
                </ul>
              ) : (<p className="text-xs text-white/40 font-mono">none detected</p>)}
            </div>

            <div className="panel p-6 border-[var(--neon)]/30 md:col-span-2">
              <h3 className="font-heading text-sm mb-3 text-[var(--neon)] uppercase tracking-widest">Green flags</h3>
              {report.green_flags.length ? (
                <ul className="text-xs font-mono space-y-1 text-white/80">
                  {report.green_flags.map((f,i)=>(<li key={i}>&gt; {f}</li>))}
                </ul>
              ) : (<p className="text-xs text-white/40 font-mono">none detected</p>)}
            </div>
          </div>

          <details className="mt-6 panel p-5 border border-white/10 text-xs font-mono text-white/70" data-testid="score-methodology">
            <summary className="cursor-pointer text-[var(--neon)] hover:text-white transition uppercase tracking-[0.2em] text-[11px]">
              // how is this score calculated?
            </summary>
            <div className="mt-4 space-y-3 leading-relaxed">
              <p>
                Scores are generated by <span className="text-[var(--neon)]">Claude Sonnet 4.5</span> analyzing publicly available signals: licensing jurisdiction (UKGC, MGA, Curacao, Kahnawake…), independent audit history (eCOGRA, iTech, GLI), regulator fines, published player complaints on AskGamblers / Trustpilot / CasinoGuru, and ownership transparency.
              </p>
              <div className="grid grid-cols-1 md:grid-cols-5 gap-2 mt-3 text-[10px]">
                <div className="panel p-2 border border-[var(--danger)]/40"><span className="text-[var(--danger)]">0–25</span><br/>Documented fraud</div>
                <div className="panel p-2 border border-[var(--danger)]/30"><span className="text-[var(--warn)]">25–45</span><br/>Confirmed problems</div>
                <div className="panel p-2 border border-[var(--warn)]/30"><span className="text-[var(--warn)]">45–60</span><br/>Unknown / new</div>
                <div className="panel p-2 border border-[var(--neon)]/30"><span className="text-[var(--neon)]">60–75</span><br/>Solid track record</div>
                <div className="panel p-2 border border-[var(--neon)]/50"><span className="text-[var(--neon)]">75–100</span><br/>Trusted brand</div>
              </div>
              <p className="pt-2 border-t border-white/10 mt-4">
                <span className="text-[var(--neon)]">Limitation:</span> the AI cannot see your firsthand experience. If you or someone you trust got paid promptly by this operator, that&apos;s real evidence the AI missed. Community signals from our Scam Wall are now factored into future scores — post a report on the Wall (positive or negative) and it helps calibrate.
              </p>
            </div>
          </details>
          </>
        );
      })()}

      {report && report.trust_score < 60 && (
        <TrustedCasinoCTA source={`legitimacy:${report.casino_name}`} headline="SAFER ALTERNATIVES" />
      )}

      {showDisagree && report && (
        <DisagreeModal
          report={report}
          onClose={() => setShowDisagree(false)}
        />
      )}
    </div>
  );
}

function DisagreeModal({ report, onClose }) {
  const [proposedScore, setProposedScore] = useState(String(Math.min(100, report.trust_score + 15)));
  const [reason, setReason] = useState("");
  const [firsthand, setFirsthand] = useState(true);
  const [busy, setBusy] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    const ps = parseInt(proposedScore, 10);
    if (isNaN(ps) || ps < 0 || ps > 100) return toast.error("Score must be 0-100.");
    if (reason.trim().length < 20) return toast.error("Give me at least 20 characters explaining why.");
    setBusy(true);
    try {
      await api.post("/legitimacy/disagree", {
        slug: report.slug,
        casino_name: report.casino_name,
        current_score: report.trust_score,
        proposed_score: ps,
        reason: reason.trim(),
        firsthand,
      });
      toast.success("Thanks — your calibration signal has been recorded. Every submission emails the operator directly.");
      onClose();
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Submission failed.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4"
      onClick={onClose}
      data-testid="disagree-modal-backdrop"
    >
      <div
        className="panel p-6 md:p-8 max-w-lg w-full border border-[var(--neon)]/40 relative"
        onClick={(e) => e.stopPropagation()}
        data-testid="disagree-modal"
      >
        <button
          onClick={onClose}
          className="absolute top-3 right-3 text-white/50 hover:text-white"
          aria-label="close"
          data-testid="disagree-modal-close"
        >
          <X className="w-4 h-4" />
        </button>
        <div className="text-[10px] uppercase tracking-[0.3em] text-[var(--neon)] mb-2">// calibrate the AI</div>
        <h2 className="font-heading text-2xl md:text-3xl tracking-tighter mb-2">Disagree with {report.casino_name}&apos;s score?</h2>
        <p className="text-xs text-white/60 font-mono mb-5">
          &gt; Current: <span className="text-[var(--warn)]">{report.trust_score}/100</span>.
          Your submission emails the site operator and feeds into future score calibration.
        </p>

        <form onSubmit={submit} className="space-y-4">
          <div>
            <label className="text-[10px] uppercase tracking-widest text-white/60 block mb-1">Your proposed score (0-100)</label>
            <input
              type="number"
              min="0"
              max="100"
              value={proposedScore}
              onChange={(e) => setProposedScore(e.target.value)}
              className="input-neon w-full text-2xl font-heading"
              data-testid="disagree-proposed-score"
              required
            />
          </div>

          <div>
            <label className="text-[10px] uppercase tracking-widest text-white/60 block mb-1">
              Why? (min 20 chars — be specific)
            </label>
            <textarea
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              rows={4}
              className="input-neon w-full text-xs font-mono"
              placeholder="e.g. My husband cashed out $850 in under an hour on Aug 12. Photo of TX in Cash App attached to my email if you want to see it."
              data-testid="disagree-reason"
              required
            />
            <p className="text-[10px] text-white/40 mt-1 font-mono">{reason.length} chars</p>
          </div>

          <label className="flex items-center gap-2 text-xs font-mono text-white/70 cursor-pointer" data-testid="disagree-firsthand-label">
            <input
              type="checkbox"
              checked={firsthand}
              onChange={(e) => setFirsthand(e.target.checked)}
              className="accent-[var(--neon)]"
              data-testid="disagree-firsthand"
            />
            <span>This is my own firsthand experience (I or someone in my household)</span>
          </label>

          <div className="flex items-center gap-3 pt-2">
            <button
              type="submit"
              disabled={busy}
              className="btn-neon flex-1"
              data-testid="disagree-submit"
            >
              {busy ? "Sending..." : "SUBMIT >_"}
            </button>
            <button
              type="button"
              onClick={onClose}
              className="btn-ghost text-xs"
              data-testid="disagree-cancel"
            >
              Cancel
            </button>
          </div>

          <p className="text-[10px] text-white/40 mt-2 font-mono text-center">
            Max 3 submissions per day. All submissions reviewed by a human.
          </p>
        </form>
      </div>
    </div>
  );
}
