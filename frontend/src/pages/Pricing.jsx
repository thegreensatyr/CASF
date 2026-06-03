import { useEffect, useState } from "react";
import { useNavigate, useLocation, Link } from "react-router-dom";
import { api } from "../lib/api";
import { useAuth } from "../context/AuthContext";
import { toast } from "sonner";
import { Check, Loader2, Crown, X } from "lucide-react";

const FEATURES = {
  free: [
    "1 casino trust check (lifetime)",
    "1 video/screenshot AI scan (lifetime)",
    "Full Tricks library",
    "Scam Wall voting",
    "Public report archive",
  ],
  premium: [
    "Unlimited trust checks",
    "Unlimited video/screenshot scans",
    "Priority AI processing",
    "Re-analyze reports anytime",
    "Export PDF reports (coming soon)",
    "Email digest of new scams (coming soon)",
    "Bookmark + alert on flagged casinos (coming soon)",
  ],
};

export default function Pricing() {
  const { user } = useAuth();
  const nav = useNavigate();
  const [busy, setBusy] = useState(false);

  useEffect(() => { document.title = "Pricing · Casino Spotter Premium"; }, []);

  const subscribe = async () => {
    if (!user) {
      toast.error("Sign in first");
      nav("/login");
      return;
    }
    setBusy(true);
    try {
      const { data } = await api.post("/stripe/checkout", { origin_url: window.location.origin });
      window.location.href = data.url;
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Checkout failed");
      setBusy(false);
    }
  };

  return (
    <div className="max-w-5xl mx-auto px-6 md:px-12 py-16">
      <p className="text-xs uppercase tracking-[0.3em] text-[var(--neon)] mb-2">// upgrade</p>
      <h1 className="font-heading text-4xl md:text-6xl tracking-tighter mb-3">UNLOCK PREMIUM</h1>
      <p className="text-sm text-white/60 font-mono mb-12 max-w-2xl">
        &gt; Free covers casual users. If you're researching multiple casinos or analyzing real game footage,
        upgrade to unlimited.
      </p>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <Plan
          title="FREE"
          price="$0"
          subtitle="Start here"
          features={FEATURES.free}
          cta={user ? "Current plan" : "Sign up free"}
          onClick={() => user ? null : nav("/signup")}
          disabled={!!user && !user.is_premium}
          accent={false}
        />
        <Plan
          title="PREMIUM"
          price="$9.99"
          subtitle="/ month · cancel anytime"
          features={FEATURES.premium}
          cta={user?.is_premium ? "Active ✓" : (busy ? "Loading..." : "Upgrade now >_")}
          onClick={subscribe}
          disabled={user?.is_premium || busy}
          accent
        />
      </div>

      <p className="text-[10px] text-white/40 font-mono mt-8 text-center">
        Secure payment by Stripe · 18+ · Educational service only · cancel anytime from your Stripe receipt
      </p>
    </div>
  );
}

function Plan({ title, price, subtitle, features, cta, onClick, disabled, accent }) {
  return (
    <div className={`panel p-8 ${accent ? "border-[var(--neon)] border-2 neon-glow" : ""}`}>
      <div className="flex items-center gap-2 mb-2">
        {accent && <Crown className="w-4 h-4 text-[var(--neon)]" />}
        <h2 className="font-heading text-2xl">{title}</h2>
      </div>
      <div className="font-heading text-5xl mb-1">{price}</div>
      <p className="text-xs text-white/60 font-mono mb-6">{subtitle}</p>
      <ul className="space-y-2 mb-8">
        {features.map((f, i) => (
          <li key={i} className="text-xs font-mono text-white/80 flex items-start gap-2">
            <Check className="w-3 h-3 text-[var(--neon)] mt-0.5 shrink-0" />
            <span>{f}</span>
          </li>
        ))}
      </ul>
      <button
        onClick={onClick}
        disabled={disabled}
        className={accent ? "btn-neon w-full" : "btn-ghost w-full"}
        data-testid={`pricing-${title.toLowerCase()}-cta`}
      >
        {cta}
      </button>
    </div>
  );
}

export function PricingSuccess() {
  const loc = useLocation();
  const nav = useNavigate();
  const { user } = useAuth();
  const [status, setStatus] = useState("checking");
  const [attempts, setAttempts] = useState(0);

  useEffect(() => {
    document.title = "Payment Processing · Casino Spotter";
    const params = new URLSearchParams(loc.search);
    const sid = params.get("session_id");
    if (!sid) { setStatus("missing"); return; }

    let cancelled = false;
    const poll = async (n) => {
      if (cancelled) return;
      if (n >= 6) { setStatus("timeout"); return; }
      try {
        const { data } = await api.get(`/stripe/checkout/status/${sid}`);
        if (data.payment_status === "paid") { setStatus("paid"); return; }
        if (data.status === "expired") { setStatus("expired"); return; }
      } catch (e) { /* keep polling */ }
      setAttempts(n + 1);
      setTimeout(() => poll(n + 1), 2000);
    };
    poll(0);
    return () => { cancelled = true; };
  }, [loc.search]);

  return (
    <div className="max-w-xl mx-auto px-6 py-20 text-center">
      {status === "checking" && (
        <>
          <Loader2 className="w-10 h-10 text-[var(--neon)] mx-auto mb-4 animate-spin" />
          <h1 className="font-heading text-3xl mb-2">Confirming payment...</h1>
          <p className="text-xs font-mono text-white/60">Polling Stripe ({attempts}/6)</p>
        </>
      )}
      {status === "paid" && (
        <>
          <Crown className="w-12 h-12 text-[var(--neon)] mx-auto mb-4" />
          <h1 className="font-heading text-4xl mb-3 neon-text">YOU'RE PREMIUM</h1>
          <p className="text-sm font-mono text-white/70 mb-6">
            Unlimited trust checks + video scans unlocked. Refresh to see your new powers.
          </p>
          <button onClick={() => { window.location.href = "/dashboard"; }} className="btn-neon">Go to dashboard &gt;_</button>
        </>
      )}
      {(status === "expired" || status === "timeout" || status === "missing") && (
        <>
          <X className="w-10 h-10 text-[var(--danger)] mx-auto mb-4" />
          <h1 className="font-heading text-3xl mb-2">Payment incomplete</h1>
          <p className="text-sm font-mono text-white/70 mb-6">
            {status === "missing" ? "No session reference found." : "We couldn't confirm your payment. If you were charged, contact support."}
          </p>
          <Link to="/pricing" className="btn-ghost">Try again &gt;_</Link>
        </>
      )}
    </div>
  );
}
