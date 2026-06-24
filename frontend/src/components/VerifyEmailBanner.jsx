import { useState } from "react";
import { useLocation } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { api } from "../lib/api";
import { toast } from "sonner";
import { Mail } from "lucide-react";

export default function VerifyEmailBanner() {
  const { user } = useAuth();
  const location = useLocation();
  const [busy, setBusy] = useState(false);

  // Hide on auth pages and on the verify page itself.
  const hiddenRoutes = ["/login", "/signup", "/verify-email", "/forgot-password", "/reset-password"];
  if (!user) return null;
  if (user.email_verified) return null;
  if (hiddenRoutes.includes(location.pathname)) return null;

  const resend = async () => {
    setBusy(true);
    try {
      const { data } = await api.post("/auth/resend-verification", { origin_url: window.location.origin });
      if (data?.already_verified) {
        toast.success("Already verified — refresh the page.");
      } else {
        toast.success(data?.message || "Verification email sent.");
      }
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Couldn't send verification email.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div
      data-testid="verify-email-banner"
      className="bg-[var(--neon-glow)] border-b border-[var(--neon)]/40 px-4 py-2 text-xs font-mono flex items-center justify-center gap-3 flex-wrap"
    >
      <Mail className="w-4 h-4 text-[var(--neon)] shrink-0" />
      <span className="text-white/85">
        Verify your email to unlock trust checks, video scans &amp; live mode.
      </span>
      <button
        onClick={resend}
        disabled={busy}
        data-testid="resend-verification-btn"
        className="text-[var(--neon)] underline hover:text-white disabled:opacity-50"
      >
        {busy ? "sending..." : "resend email >_"}
      </button>
    </div>
  );
}
