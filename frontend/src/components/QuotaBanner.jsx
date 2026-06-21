import { Link } from "react-router-dom";
import { Crown, Zap } from "lucide-react";
import { useAuth } from "../context/AuthContext";

export default function QuotaBanner({ type }) {
  const { user } = useAuth();
  if (!user || user.is_premium || user.is_admin) return null;

  const used = type === "video"
    ? (user.free_video_scans_used ?? 0)
    : (user.free_trust_checks_used ?? 0);
  const limit = type === "video"
    ? (user.free_video_scans_limit ?? 1)
    : (user.free_trust_checks_limit ?? 1);

  const remaining = Math.max(0, limit - used);
  const exhausted = remaining === 0;

  return (
    <div
      className={`panel p-4 mb-6 flex flex-wrap items-center justify-between gap-3 ${exhausted ? "border-[var(--danger)]/60" : "border-[var(--warn)]/40"}`}
      data-testid={`quota-banner-${type}`}
    >
      <div className="flex items-center gap-3">
        <Zap className={`w-4 h-4 ${exhausted ? "text-[var(--danger)]" : "text-[var(--warn)]"}`} />
        <div>
          <p className="text-xs font-mono text-white/80">
            {exhausted
              ? <>You've used your free {type === "video" ? "video scan" : "trust check"}. Upgrade for unlimited.</>
              : <>Free tier: <span className="text-[var(--neon)]">{remaining}</span> {type === "video" ? "video scan" : "trust check"} remaining.</>
            }
          </p>
        </div>
      </div>
      <Link to="/pricing" className="btn-neon text-xs flex items-center gap-1" data-testid={`quota-upgrade-${type}`}>
        <Crown className="w-3 h-3" /> Upgrade $9.99/mo
      </Link>
    </div>
  );
}
