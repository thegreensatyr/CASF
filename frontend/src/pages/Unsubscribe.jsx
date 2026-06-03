import { useEffect, useState } from "react";
import { useSearchParams, Link } from "react-router-dom";
import { api } from "../lib/api";
import { Check, X } from "lucide-react";

export default function Unsubscribe() {
  const [params] = useSearchParams();
  const [status, setStatus] = useState("loading");

  useEffect(() => {
    document.title = "Unsubscribe · Casino Spotter";
    const token = params.get("token");
    if (!token) { setStatus("invalid"); return; }
    api.get(`/unsubscribe?token=${encodeURIComponent(token)}`)
      .then(() => setStatus("done"))
      .catch(() => setStatus("invalid"));
  }, [params]);

  return (
    <div className="max-w-md mx-auto px-6 py-24 text-center">
      {status === "loading" && <p className="text-xs font-mono text-[var(--neon)]">&gt; processing...</p>}
      {status === "done" && (
        <>
          <Check className="w-10 h-10 text-[var(--neon)] mx-auto mb-4" />
          <h1 className="font-heading text-3xl mb-3">YOU'RE OUT</h1>
          <p className="text-sm font-mono text-white/70 mb-6">
            You won't receive any more digest emails. You can opt back in anytime from your dashboard.
          </p>
          <Link to="/" className="btn-ghost">Back to home &gt;_</Link>
        </>
      )}
      {status === "invalid" && (
        <>
          <X className="w-10 h-10 text-[var(--danger)] mx-auto mb-4" />
          <h1 className="font-heading text-3xl mb-3">INVALID LINK</h1>
          <p className="text-sm font-mono text-white/70 mb-6">
            This unsubscribe link is invalid or expired. If you keep receiving emails,
            log in to your dashboard and turn off the digest manually.
          </p>
          <Link to="/login" className="btn-ghost">Login &gt;_</Link>
        </>
      )}
    </div>
  );
}
