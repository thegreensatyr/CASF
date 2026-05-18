import { useState } from "react";
import { api } from "../lib/api";
import { toast } from "sonner";
import { Search, Loader2, ShieldCheck, ShieldAlert, ShieldX } from "lucide-react";

export default function Legitimacy() {
  const [name, setName] = useState("");
  const [url, setUrl] = useState("");
  const [busy, setBusy] = useState(false);
  const [report, setReport] = useState(null);

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
        return (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4" data-testid="legit-report">
            <div className={`panel p-6 ${b.color} border-2`}>
              <Icon className="w-8 h-8 mb-3" />
              <div className="text-[10px] uppercase tracking-[0.3em] text-white/60">trust score</div>
              <div className="font-heading text-5xl mt-1">{report.trust_score}<span className="text-white/40 text-2xl">/100</span></div>
              <div className={`mt-3 tag ${b.color}`}>{b.label}</div>
              <p className="text-xs font-mono text-white/70 mt-4">{report.verdict}</p>
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
        );
      })()}
    </div>
  );
}
