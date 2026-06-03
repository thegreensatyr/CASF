import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../lib/api";
import { timeAgo } from "../lib/ui";
import { Activity, ScanLine, ShieldCheck, AlertTriangle } from "lucide-react";

const ICONS = {
  ai_scan: ScanLine,
  trust_check: ShieldCheck,
  scam_report: AlertTriangle,
};

const COLORS = {
  ai_scan: "text-[var(--neon)]",
  trust_check: "text-[var(--neon)]",
  scam_report: "text-[var(--danger)]",
};

export default function ActivityFeed() {
  const [events, setEvents] = useState([]);
  const [tick, setTick] = useState(0);

  useEffect(() => {
    const load = () => api.get("/activity/recent?limit=8").then((r) => setEvents(r.data)).catch(() => {});
    load();
    const poll = setInterval(load, 20000);
    const tk = setInterval(() => setTick((t) => t + 1), 15000);
    return () => { clearInterval(poll); clearInterval(tk); };
  }, []);

  if (events.length === 0) return null;

  return (
    <section className="border-t border-white/10 bg-black">
      <div className="max-w-7xl mx-auto px-6 md:px-12 py-16">
        <div className="flex items-center justify-between flex-wrap gap-4 mb-8">
          <div className="flex items-center gap-3">
            <Activity className="w-5 h-5 text-[var(--neon)]" />
            <h2 className="font-heading text-2xl md:text-3xl tracking-tighter">LIVE ACTIVITY</h2>
            <span className="flex items-center gap-1 text-[10px] uppercase tracking-widest text-[var(--neon)] font-mono">
              <span className="dot-pulse w-1.5 h-1.5 rounded-full bg-[var(--neon)]" /> streaming
            </span>
          </div>
          <span className="text-xs font-mono text-white/40">auto-refresh · 20s</span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-2" data-testid="activity-feed">
          {events.map((e, i) => {
            const Icon = ICONS[e.type] || Activity;
            const color = COLORS[e.type] || "text-white/70";
            const inner = (
              <>
                <Icon className={`w-4 h-4 ${color} shrink-0`} />
                <div className="flex-1 min-w-0">
                  <div className="text-xs font-mono text-white/90 truncate" key={tick}>
                    <span className={color}>&gt;</span> {e.label}
                    {e.detail && <span className="text-white/50"> · {e.detail}</span>}
                  </div>
                </div>
                <span className="text-[10px] uppercase tracking-widest text-white/40 font-mono shrink-0">
                  {timeAgo(e.created_at)}
                </span>
              </>
            );
            const cls = "panel p-3 px-4 flex items-center gap-3 hover:border-[var(--neon-dim)] transition";
            return e.slug ? (
              <Link key={`${e.type}-${i}`} to={`/report/${e.slug}`} className={cls}>{inner}</Link>
            ) : (
              <div key={`${e.type}-${i}`} className={cls}>{inner}</div>
            );
          })}
        </div>
      </div>
    </section>
  );
}
