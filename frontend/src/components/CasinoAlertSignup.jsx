import { useState } from "react";
import { api } from "../lib/api";
import { toast } from "sonner";
import { Bell, Check } from "lucide-react";

export default function CasinoAlertSignup({ slug, casinoName }) {
  const [email, setEmail] = useState("");
  const [done, setDone] = useState(false);
  const [busy, setBusy] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    try {
      await api.post("/alerts/subscribe-casino", {
        email,
        casino_slug: slug,
        casino_name: casinoName,
      });
      setDone(true);
      toast.success("You'll be notified when this score changes");
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Subscription failed");
    } finally {
      setBusy(false);
    }
  };

  if (done) {
    return (
      <div className="panel p-5 mt-6 border-[var(--neon)]/40 flex items-center gap-3" data-testid="alert-success">
        <Check className="w-4 h-4 text-[var(--neon)]" />
        <p className="text-xs font-mono text-white/80">
          You're on the list. We'll email you the moment this casino's trust score moves.
        </p>
      </div>
    );
  }

  return (
    <form onSubmit={submit} className="panel p-5 mt-6 border-[var(--neon)]/30" data-testid="alert-form">
      <div className="flex items-center gap-2 mb-3">
        <Bell className="w-4 h-4 text-[var(--neon)]" />
        <h3 className="font-heading text-sm uppercase tracking-widest">Get alerted on score changes</h3>
      </div>
      <p className="text-[11px] font-mono text-white/60 mb-3">
        Casinos change. New complaints surface, licenses lapse, ownership shifts. We'll email you if {casinoName}'s score moves.
      </p>
      <div className="flex flex-col sm:flex-row gap-2">
        <input
          data-testid="alert-email-input"
          type="email"
          required
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          placeholder="you@example.com"
          className="input-neon flex-1"
        />
        <button data-testid="alert-submit" className="btn-neon text-xs whitespace-nowrap" disabled={busy}>
          {busy ? "..." : "ALERT ME >_"}
        </button>
      </div>
      <p className="text-[10px] text-white/40 font-mono mt-2">No spam. Just score changes. Unsub anytime.</p>
    </form>
  );
}
