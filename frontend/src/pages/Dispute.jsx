import { useState } from "react";
import { useSearchParams, Link } from "react-router-dom";
import { api } from "../lib/api";
import { toast } from "sonner";
import { Scale, ShieldCheck, Loader2 } from "lucide-react";

export default function Dispute() {
  const [params] = useSearchParams();
  const targetType = params.get("type") || "trust";
  const targetSlug = params.get("slug") || "";

  const [casinoName, setCasinoName] = useState("");
  const [contactName, setContactName] = useState("");
  const [role, setRole] = useState("");
  const [email, setEmail] = useState("");
  const [response, setResponse] = useState("");
  const [busy, setBusy] = useState(false);
  const [submitted, setSubmitted] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    if (response.trim().length < 20) {
      return toast.error("Response must be at least 20 characters.");
    }
    setBusy(true);
    try {
      await api.post("/disputes", {
        target_type: targetType,
        target_slug: targetSlug || null,
        casino_name: casinoName.trim(),
        contact_email: email.trim(),
        contact_name: contactName.trim(),
        role: role.trim(),
        response_text: response.trim(),
      });
      setSubmitted(true);
      toast.success("Dispute submitted. We'll review within 5 business days.");
    } catch (err) {
      const msg = err?.response?.data?.detail || "Submission failed";
      toast.error(msg);
    } finally {
      setBusy(false);
    }
  };

  if (submitted) {
    return (
      <div className="max-w-2xl mx-auto px-6 py-20 text-center" data-testid="dispute-submitted">
        <ShieldCheck className="w-12 h-12 text-[var(--neon)] mx-auto mb-4" />
        <h1 className="font-heading text-3xl mb-2">Dispute received</h1>
        <p className="text-sm text-white/70 font-mono mb-2 leading-relaxed">
          Thanks. Your right-of-response has been logged and routed to our editorial team.
        </p>
        <p className="text-xs text-white/50 font-mono mb-8 leading-relaxed">
          We review every submission within 5 business days. If approved, your response will be
          attached publicly to the report at <span className="text-[var(--neon)]">{targetSlug}</span>.
          Urgent legal matters: <a href="mailto:corrections@casforensics.org" className="text-[var(--neon)] underline">corrections@casforensics.org</a>.
        </p>
        <Link to="/" className="btn-ghost text-xs">&lt; Back to home</Link>
      </div>
    );
  }

  return (
    <div className="max-w-2xl mx-auto px-6 py-12" data-testid="dispute-page">
      <p className="text-xs uppercase tracking-[0.3em] text-[var(--neon)] mb-2">// editorial process</p>
      <h1 className="font-heading text-3xl md:text-4xl tracking-tighter mb-3 flex items-center gap-3">
        <Scale className="w-7 h-7 text-[var(--neon)]" /> RIGHT OF RESPONSE
      </h1>
      <p className="text-sm text-white/70 font-mono mb-2 leading-relaxed">
        If you represent an operator named in one of our reports and believe the analysis is
        inaccurate, you can submit a formal response. If we accept it, your response will be
        attached publicly to the report.
      </p>
      <p className="text-xs text-white/50 font-mono mb-8 leading-relaxed">
        We do <strong>not</strong> remove reports on request — they reflect AI forensic analysis
        of publicly available material — but we do publish operator responses alongside them.
      </p>

      <form onSubmit={submit} className="panel p-6 space-y-5" data-testid="dispute-form">
        <div>
          <label className="text-[10px] uppercase tracking-widest text-white/60 font-heading block mb-1">REPORT TYPE</label>
          <input
            value={targetType}
            disabled
            className="input-neon opacity-60"
            data-testid="dispute-type"
          />
        </div>
        {targetSlug && (
          <div>
            <label className="text-[10px] uppercase tracking-widest text-white/60 font-heading block mb-1">REPORT REFERENCE</label>
            <input
              value={targetSlug}
              disabled
              className="input-neon opacity-60 font-mono text-xs"
              data-testid="dispute-slug"
            />
          </div>
        )}

        <div>
          <label className="text-[10px] uppercase tracking-widest text-white/60 font-heading block mb-1">CASINO / OPERATOR NAME *</label>
          <input
            required
            value={casinoName}
            onChange={(e) => setCasinoName(e.target.value)}
            className="input-neon"
            placeholder="e.g. Lucky Spin Casino Ltd."
            data-testid="dispute-casino"
          />
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="text-[10px] uppercase tracking-widest text-white/60 font-heading block mb-1">YOUR NAME</label>
            <input
              value={contactName}
              onChange={(e) => setContactName(e.target.value)}
              className="input-neon"
              placeholder="Jane Doe"
              data-testid="dispute-name"
            />
          </div>
          <div>
            <label className="text-[10px] uppercase tracking-widest text-white/60 font-heading block mb-1">ROLE</label>
            <input
              value={role}
              onChange={(e) => setRole(e.target.value)}
              className="input-neon"
              placeholder="Compliance Officer / Legal counsel"
              data-testid="dispute-role"
            />
          </div>
        </div>

        <div>
          <label className="text-[10px] uppercase tracking-widest text-white/60 font-heading block mb-1">VERIFIABLE CONTACT EMAIL *</label>
          <input
            required
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="input-neon"
            placeholder="compliance@yourcasino.com"
            data-testid="dispute-email"
          />
          <p className="text-[10px] font-mono text-white/40 mt-1">Must be a domain email matching the operator. We may verify before publication.</p>
        </div>

        <div>
          <label className="text-[10px] uppercase tracking-widest text-white/60 font-heading block mb-1">YOUR RESPONSE * <span className="text-white/40">(20-4000 chars)</span></label>
          <textarea
            required
            rows={8}
            value={response}
            onChange={(e) => setResponse(e.target.value)}
            className="input-neon font-mono text-sm leading-relaxed"
            placeholder="State your position. Cite licenses, audits, or evidence that contradicts the analysis. Be specific."
            data-testid="dispute-response"
          />
          <p className="text-[10px] font-mono text-white/40 mt-1">{response.length} / 4000</p>
        </div>

        <button
          type="submit"
          disabled={busy}
          className="btn-neon w-full flex items-center justify-center gap-2"
          data-testid="dispute-submit"
        >
          {busy ? <Loader2 className="w-4 h-4 animate-spin" /> : <Scale className="w-4 h-4" />}
          {busy ? "SUBMITTING..." : "FILE DISPUTE >_"}
        </button>
        <p className="text-[10px] text-white/40 text-center font-mono">
          By submitting you agree your name, role, and response may be published publicly alongside the original report.
        </p>
      </form>
    </div>
  );
}
