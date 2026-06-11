import { useEffect, useState } from "react";
import { api } from "../lib/api";
import { toast } from "sonner";
import { ShieldCheck, Check, ArrowRight } from "lucide-react";

const BENEFITS = [
  "Display the 'Verified by Scam Spotter' badge on your casino site",
  "Quarterly forensic audit by our analysts (Claude Sonnet 4.5 + manual review)",
  "Featured placement in our public archive at /reports",
  "Direct response-of-record on player complaints filed via our Scam Wall",
  "Co-branded annual transparency report (yours to publish)",
  "Removal of any inaccurate historical claims via documented evidence",
  "Priority listing in 'Safer Alternatives' CTA across the platform",
];

const CRITERIA = [
  "Valid UKGC, MGA, NJ DGE, PA, or other Tier-1 jurisdiction license",
  "Independently audited RNG (eCOGRA, iTech Labs, GLI)",
  "Published RTP figures on every game",
  "Public ownership / parent company disclosure",
  "Average withdrawal time under 72 hours over last 6 months",
  "Active and visible responsible-gambling tools",
];

export default function Verified() {
  const [form, setForm] = useState({
    casino_name: "", contact_name: "", contact_email: "",
    casino_url: "", license: "", notes: "",
  });
  const [submitted, setSubmitted] = useState(false);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    document.title = "Verified Badge Program — $299/yr · Casino Spotter";
    const m = document.querySelector('meta[name="description"]');
    const desc = "Apply for the Verified by Scam Spotter badge — quarterly forensic audits and a trust signal players can verify in real-time.";
    if (m) m.setAttribute("content", desc);
    else {
      const tag = document.createElement("meta");
      tag.name = "description"; tag.content = desc; document.head.appendChild(tag);
    }
  }, []);

  const upd = (k) => (e) => setForm({ ...form, [k]: e.target.value });

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    try {
      await api.post("/verified/apply", form);
      setSubmitted(true);
      toast.success("Application received. We'll review and respond within 5 business days.");
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Submission failed");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="max-w-5xl mx-auto px-6 md:px-12 py-12">
      <div className="flex items-center gap-3 mb-3">
        <ShieldCheck className="w-7 h-7 text-[var(--neon)]" />
        <p className="text-xs uppercase tracking-[0.3em] text-[var(--neon)]">// for casino operators</p>
      </div>
      <h1 className="font-heading text-4xl md:text-6xl tracking-tighter mb-3">
        VERIFIED BY <span className="neon-text">SCAM SPOTTER</span>
      </h1>
      <p className="text-base text-white/70 font-mono max-w-2xl mb-8 leading-relaxed">
        A trust signal that means something. We audit, you display the badge.
        Players see a name they recognize as on-their-side.
      </p>
      <div className="font-heading text-5xl text-[var(--neon)] mb-2">$299<span className="text-base text-white/40 font-mono"> /year</span></div>
      <p className="text-[11px] text-white/40 font-mono mb-12">Renewable annually. Pulled instantly if audit findings change.</p>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-8 mb-14">
        <div>
          <h2 className="font-heading text-xl mb-4 text-[var(--neon)]">// what you get</h2>
          <ul className="space-y-3">
            {BENEFITS.map((b, i) => (
              <li key={i} className="flex items-start gap-2 text-xs font-mono text-white/85 leading-relaxed">
                <Check className="w-3 h-3 text-[var(--neon)] mt-1 shrink-0" />
                <span>{b}</span>
              </li>
            ))}
          </ul>
        </div>
        <div>
          <h2 className="font-heading text-xl mb-4 text-[var(--neon)]">// eligibility criteria</h2>
          <ul className="space-y-3">
            {CRITERIA.map((c, i) => (
              <li key={i} className="flex items-start gap-2 text-xs font-mono text-white/85 leading-relaxed">
                <ArrowRight className="w-3 h-3 text-[var(--neon)] mt-1 shrink-0" />
                <span>{c}</span>
              </li>
            ))}
          </ul>
          <p className="text-[10px] text-white/40 font-mono mt-4">
            Operators failing any criterion may apply but will be reviewed case-by-case.
          </p>
        </div>
      </div>

      {submitted ? (
        <div className="panel p-8 text-center border-[var(--neon)]" data-testid="verified-success">
          <Check className="w-10 h-10 text-[var(--neon)] mx-auto mb-3" />
          <h2 className="font-heading text-2xl mb-2">APPLICATION RECEIVED</h2>
          <p className="text-sm font-mono text-white/70">
            Our compliance team will review within 5 business days. We respond to every application,
            approved or not, with specific feedback.
          </p>
        </div>
      ) : (
        <form onSubmit={submit} className="panel p-6 space-y-5" data-testid="verified-application-form">
          <h2 className="font-heading text-xl mb-2">// apply now</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <Field label="CASINO BRAND NAME *" value={form.casino_name} onChange={upd("casino_name")} testid="verified-name" />
            <Field label="CASINO URL *" value={form.casino_url} onChange={upd("casino_url")} testid="verified-url" placeholder="https://" />
            <Field label="YOUR FULL NAME *" value={form.contact_name} onChange={upd("contact_name")} testid="verified-contact-name" />
            <Field label="WORK EMAIL *" type="email" value={form.contact_email} onChange={upd("contact_email")} testid="verified-contact-email" />
            <div className="md:col-span-2">
              <Field label="LICENSE NUMBER(S) & JURISDICTION" value={form.license} onChange={upd("license")} testid="verified-license" placeholder="e.g. MGA/CRP/118/2004 (Malta)" />
            </div>
          </div>
          <label className="block">
            <span className="block text-xs uppercase tracking-widest text-white/60 mb-1 font-heading">ANYTHING ELSE WE SHOULD KNOW?</span>
            <textarea
              data-testid="verified-notes"
              value={form.notes}
              onChange={upd("notes")}
              rows={4}
              maxLength={2000}
              className="input-neon resize-y"
              placeholder="Recent audits, ownership changes, response to past complaints, anything that helps our review."
            />
          </label>
          <button className="btn-neon w-full" disabled={busy} data-testid="verified-submit">
            {busy ? "Submitting..." : "SUBMIT APPLICATION >_"}
          </button>
          <p className="text-[10px] text-white/40 font-mono text-center">
            No payment until approved. We review first, then send a Stripe invoice on acceptance.
          </p>
        </form>
      )}
    </div>
  );
}

function Field({ label, value, onChange, testid, placeholder, type = "text" }) {
  return (
    <label className="block">
      <span className="block text-xs uppercase tracking-widest text-white/60 mb-1 font-heading">{label}</span>
      <input
        data-testid={testid}
        type={type}
        value={value}
        onChange={onChange}
        placeholder={placeholder}
        required={label.includes("*")}
        className="input-neon"
      />
    </label>
  );
}
