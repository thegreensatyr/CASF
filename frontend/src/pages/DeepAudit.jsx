import { useEffect, useState } from "react";
import { useNavigate, useSearchParams, Link } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { api } from "../lib/api";
import { toast } from "sonner";
import { Loader2, FileSearch, ShieldAlert, CreditCard } from "lucide-react";

export default function DeepAudit() {
  const { user } = useAuth();
  const nav = useNavigate();
  const [params] = useSearchParams();
  const prefill = params.get("prefill") || "";
  const [form, setForm] = useState({ casino_name: prefill, casino_url: "", extra_context: "" });
  const [busy, setBusy] = useState(false);

  useEffect(() => { document.title = "Deep Casino Audit · $24.99 · Casino Spotter"; }, []);

  const submit = async (e) => {
    e.preventDefault();
    if (!user) { toast.error("Sign in first"); nav("/login"); return; }
    setBusy(true);
    try {
      const { data } = await api.post("/audit/checkout", {
        ...form,
        origin_url: window.location.origin,
      });
      window.location.href = data.url;
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Checkout failed");
      setBusy(false);
    }
  };

  return (
    <div className="max-w-3xl mx-auto px-6 md:px-12 py-12">
      <div className="flex items-center gap-3 mb-3">
        <FileSearch className="w-7 h-7 text-[var(--neon)]" />
        <p className="text-xs uppercase tracking-[0.3em] text-[var(--neon)]">// premium one-off</p>
      </div>
      <h1 className="font-heading text-4xl md:text-6xl tracking-tighter mb-2">DEEP CASINO AUDIT</h1>
      <p className="text-base text-white/70 font-mono mb-2 max-w-2xl leading-relaxed">
        A premium investigative report on any casino — far deeper than the standard trust check.
      </p>
      <div className="font-heading text-5xl text-[var(--neon)] mb-2">$24.99</div>
      <p className="text-[11px] text-white/40 font-mono mb-10">one-off · secure Stripe checkout · delivered in ~60 seconds</p>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-10">
        {[
          "Full licensing & ownership trace",
          "RNG audit + RTP disclosure check",
          "Complaint history (Casinomeister, AskGamblers, ThePogg)",
          "Withdrawal-risk pattern analysis",
          "Bonus-terms forensic breakdown",
          "Responsible-gambling tool assessment",
          "Personal protect-yourself recommendations",
          "Saved permanently to your dashboard",
        ].map((f, i) => (
          <div key={i} className="text-xs font-mono text-white/80 flex items-start gap-2">
            <ShieldAlert className="w-3 h-3 text-[var(--neon)] mt-0.5 shrink-0" />
            <span>{f}</span>
          </div>
        ))}
      </div>

      <form onSubmit={submit} className="panel p-6 space-y-5" data-testid="deep-audit-form">
        <Field label="CASINO NAME *" value={form.casino_name} onChange={(v)=>setForm({...form, casino_name:v})} testid="audit-name" />
        <Field label="CASINO URL (optional)" value={form.casino_url} onChange={(v)=>setForm({...form, casino_url:v})} testid="audit-url" placeholder="https://" />
        <label className="block">
          <span className="block text-xs uppercase tracking-widest text-white/60 mb-1 font-heading">YOUR CONCERNS (optional)</span>
          <textarea
            data-testid="audit-context"
            value={form.extra_context}
            onChange={(e)=>setForm({...form, extra_context: e.target.value})}
            rows={4}
            maxLength={2000}
            className="input-neon resize-y"
            placeholder="What happened? Delayed withdrawal? Voided winnings? Suspicious bonus? Anything specific will be folded into the report."
          />
          <span className="text-[10px] text-white/40 font-mono">{form.extra_context.length}/2000</span>
        </label>
        <button className="btn-neon w-full flex items-center justify-center gap-2" disabled={busy} data-testid="audit-submit">
          {busy ? (<><Loader2 className="w-4 h-4 animate-spin" /> REDIRECTING TO CHECKOUT...</>) : (<><CreditCard className="w-4 h-4" /> ORDER FOR $24.99 &gt;_</>)}
        </button>
        <p className="text-[10px] text-white/40 font-mono text-center">
          Stripe-secured payment · Refund within 24h if AI fails to generate report
        </p>
      </form>
    </div>
  );
}

function Field({ label, value, onChange, testid, placeholder }) {
  return (
    <label className="block">
      <span className="block text-xs uppercase tracking-widest text-white/60 mb-1 font-heading">{label}</span>
      <input
        data-testid={testid}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        required={label.includes("*")}
        className="input-neon"
      />
    </label>
  );
}

export function DeepAuditResult() {
  const [params] = useSearchParams();
  const sid = params.get("session_id");
  const [data, setData] = useState(null);
  const [attempts, setAttempts] = useState(0);
  const [error, setError] = useState(null);

  useEffect(() => { document.title = "Deep Audit Result · Casino Spotter"; }, []);

  useEffect(() => {
    if (!sid) { setError("Missing session ID"); return; }
    let cancelled = false;
    const poll = async (n) => {
      if (cancelled) return;
      if (n >= 12) { setError("Audit is taking longer than expected. Refresh in a moment."); return; }
      try {
        const { data } = await api.get(`/audit/result/${sid}`);
        if (data.status === "complete") { setData(data); return; }
      } catch (e) { /* keep polling */ }
      setAttempts(n + 1);
      setTimeout(() => poll(n + 1), 4000);
    };
    poll(0);
    return () => { cancelled = true; };
  }, [sid]);

  if (error) {
    return (
      <div className="max-w-md mx-auto px-6 py-24 text-center">
        <p className="font-mono text-sm text-white/70 mb-4">{error}</p>
        <Link to="/audit" className="btn-ghost">Try again &gt;_</Link>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="max-w-md mx-auto px-6 py-24 text-center">
        <Loader2 className="w-10 h-10 text-[var(--neon)] mx-auto mb-4 animate-spin" />
        <h1 className="font-heading text-2xl mb-2">Generating your audit...</h1>
        <p className="text-xs font-mono text-white/60">Polling Claude Sonnet 4.5 ({attempts}/12)</p>
        <p className="text-[10px] font-mono text-white/40 mt-2">First check: payment confirmation · Then: AI investigation</p>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto px-6 md:px-12 py-12">
      <p className="text-xs uppercase tracking-[0.3em] text-[var(--neon)] mb-2">// deep audit · paid report</p>
      <h1 className="font-heading text-4xl md:text-5xl tracking-tighter mb-4">{data.casino_name}</h1>
      <p className="text-[10px] font-mono text-white/40 mb-8">Generated {new Date(data.generated_at).toLocaleString()} · Saved to your account</p>
      <div className="panel p-8" data-testid="audit-result">
        <pre className="whitespace-pre-wrap text-sm font-mono text-white/85 leading-relaxed">{data.report}</pre>
      </div>
      <div className="mt-8 flex gap-3">
        <Link to="/audit" className="btn-ghost text-xs">Order another &gt;_</Link>
        <Link to="/dashboard" className="btn-ghost text-xs">Back to dashboard</Link>
      </div>
    </div>
  );
}
