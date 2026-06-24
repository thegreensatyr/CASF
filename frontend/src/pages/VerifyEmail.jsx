import { useEffect, useRef, useState } from "react";
import { useSearchParams, Link, useNavigate } from "react-router-dom";
import { api } from "../lib/api";
import { useAuth } from "../context/AuthContext";
import { toast } from "sonner";
import { CheckCircle2, XCircle, Mail } from "lucide-react";

export default function VerifyEmail() {
  const [params] = useSearchParams();
  const token = params.get("token");
  const { setSession } = useAuth();
  const nav = useNavigate();
  const [status, setStatus] = useState("verifying"); // verifying | success | error
  const [error, setError] = useState("");
  const ranRef = useRef(false);

  useEffect(() => {
    if (ranRef.current) return; // Guard against React 18 StrictMode double-invoke.
    ranRef.current = true;
    if (!token) {
      setStatus("error");
      setError("Missing verification token in URL.");
      return;
    }
    api
      .post("/auth/verify-email", { token })
      .then((r) => {
        setSession(r.data.token, r.data.user);
        setStatus("success");
        toast.success("Email verified. Forensic tools unlocked.");
        setTimeout(() => nav("/dashboard"), 1600);
      })
      .catch((err) => {
        setStatus("error");
        setError(err?.response?.data?.detail || "Verification failed.");
      });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token]);

  return (
    <div className="max-w-md mx-auto px-6 py-20">
      <div className="panel p-8 text-center" data-testid="verify-email-page">
        <p className="text-xs uppercase tracking-[0.3em] text-[var(--neon)] mb-2">// secure terminal</p>
        <h1 className="font-heading text-3xl tracking-tighter mb-4">EMAIL VERIFICATION</h1>

        {status === "verifying" && (
          <div className="py-8" data-testid="verify-status-verifying">
            <Mail className="w-10 h-10 text-[var(--neon)] mx-auto mb-4 animate-pulse" />
            <p className="text-sm font-mono text-white/70">&gt; verifying token...</p>
          </div>
        )}

        {status === "success" && (
          <div className="py-8" data-testid="verify-status-success">
            <CheckCircle2 className="w-12 h-12 text-[var(--neon)] mx-auto mb-4" />
            <p className="text-sm font-mono text-white/85">&gt; verified. redirecting to dashboard...</p>
          </div>
        )}

        {status === "error" && (
          <div className="py-8" data-testid="verify-status-error">
            <XCircle className="w-12 h-12 text-[var(--danger)] mx-auto mb-4" />
            <p className="text-sm font-mono text-white/85 mb-2">{error}</p>
            <p className="text-xs text-white/50 font-mono mb-6">Login and request a new verification email from the banner.</p>
            <Link to="/login" className="btn-neon">LOGIN &gt;_</Link>
          </div>
        )}
      </div>
    </div>
  );
}
