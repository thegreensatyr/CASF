import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../lib/api";
import {
  Users, DollarSign, Cpu, Scale, AlertTriangle, TrendingUp, Loader2,
  ChevronRight, Database, ShieldCheck
} from "lucide-react";

const fmtUSD = (n) => `$${Number(n || 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
const fmt = (n) => Number(n || 0).toLocaleString();

export default function AdminDashboard() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState("");

  useEffect(() => {
    document.title = "Admin Dashboard · Casino Spotter";
    api.get("/admin/dashboard")
      .then((r) => setData(r.data))
      .catch((e) => setErr(e?.response?.data?.detail || "Could not load dashboard"))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return (
    <div className="text-center py-20">
      <Loader2 className="w-6 h-6 animate-spin text-[var(--neon)] mx-auto" />
    </div>
  );

  if (err) return (
    <div className="max-w-3xl mx-auto px-6 py-20 text-center">
      <p className="text-sm font-mono text-[var(--danger)]">{err}</p>
    </div>
  );

  const dailyBudget = 25;  // USD/day soft alert threshold
  const burnRatio = data.llm_costs.estimated_today_usd / dailyBudget;
  const burnState = burnRatio >= 1 ? "danger" : burnRatio >= 0.6 ? "warn" : "ok";
  const burnColor = burnState === "danger" ? "text-[var(--danger)]"
    : burnState === "warn" ? "text-yellow-400" : "text-[var(--neon)]";

  return (
    <div className="max-w-7xl mx-auto px-6 py-12" data-testid="admin-dashboard">
      <p className="text-xs uppercase tracking-[0.3em] text-[var(--neon)] mb-2">// operator console</p>
      <h1 className="font-heading text-4xl tracking-tighter mb-2">MISSION CONTROL</h1>
      <p className="text-sm text-white/60 font-mono mb-8">
        &gt; All key metrics. Auto-refreshed on each visit. Drill into any section via the side links.
      </p>

      {/* Top-line KPIs */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-8">
        <Kpi
          icon={<Users className="w-4 h-4" />}
          label="Total users"
          value={fmt(data.users.total)}
          sub={`+${data.users.today} today · +${data.users.seven_days} this week`}
          testid="kpi-users"
        />
        <Kpi
          icon={<TrendingUp className="w-4 h-4" />}
          label="Premium MRR"
          value={fmtUSD(data.revenue.mrr_usd)}
          sub={`${data.revenue.premium_count} subscribers · ${fmtUSD(data.revenue.arr_usd)} ARR`}
          accent="neon"
          testid="kpi-mrr"
        />
        <Kpi
          icon={<Cpu className="w-4 h-4" />}
          label="LLM spend today"
          value={fmtUSD(data.llm_costs.estimated_today_usd)}
          sub={`Budget: ${fmtUSD(dailyBudget)} · 7d ${fmtUSD(data.llm_costs.estimated_7d_usd)}`}
          accent={burnState}
          testid="kpi-llm"
        />
        <Kpi
          icon={<Scale className="w-4 h-4" />}
          label="Moderation queue"
          value={fmt(data.moderation.pending_disputes + data.moderation.pending_verified_apps)}
          sub={`${data.moderation.pending_disputes} disputes · ${data.moderation.pending_verified_apps} verified apps`}
          accent={data.moderation.pending_disputes > 0 ? "warn" : "ok"}
          testid="kpi-moderation"
        />
      </div>

      {/* Burn-rate alert */}
      {burnState === "danger" && (
        <div className="panel p-4 mb-6 border border-[var(--danger)]/60 bg-[var(--danger)]/[0.05] flex gap-3" data-testid="burn-alert">
          <AlertTriangle className="w-4 h-4 text-[var(--danger)] mt-0.5 shrink-0" />
          <p className="text-xs font-mono text-white/85 leading-relaxed">
            <strong className="text-[var(--danger)]">LLM spend exceeded ${dailyBudget}/day budget.</strong>{" "}
            Investigate top callers or pause advertising until verified. Cache hit rate this week saved <span className="text-[var(--neon)]">{fmtUSD(data.llm_costs.cache_savings_7d_usd)}</span>.
          </p>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Acquisition / sources */}
        <div className="panel p-5" data-testid="dashboard-sources">
          <h2 className="font-heading text-sm uppercase tracking-widest mb-3 flex items-center gap-2">
            <Database className="w-3.5 h-3.5 text-[var(--neon)]" /> Top signup sources (30d)
          </h2>
          {data.top_sources_30d.length === 0 ? (
            <p className="text-xs font-mono text-white/40">No signups in the last 30 days.</p>
          ) : (
            <table className="w-full text-xs font-mono">
              <thead>
                <tr className="text-white/40 text-[10px] uppercase tracking-widest border-b border-white/10">
                  <th className="text-left py-1">Source</th>
                  <th className="text-right">Signups</th>
                  <th className="text-right">Premium</th>
                  <th className="text-right">Conv%</th>
                </tr>
              </thead>
              <tbody>
                {data.top_sources_30d.map((s) => {
                  const conv = s.signups_30d > 0 ? Math.round((s.premium_30d / s.signups_30d) * 100) : 0;
                  return (
                    <tr key={s.source} className="border-b border-white/5" data-testid={`source-row-${s.source}`}>
                      <td className="py-2 text-white/80">{s.source}</td>
                      <td className="text-right text-white/70">{fmt(s.signups_30d)}</td>
                      <td className="text-right text-[var(--neon)]">{fmt(s.premium_30d)}</td>
                      <td className={`text-right ${conv > 0 ? "text-[var(--neon)]" : "text-white/40"}`}>{conv}%</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          )}
        </div>

        {/* LLM breakdown */}
        <div className="panel p-5" data-testid="dashboard-llm">
          <h2 className="font-heading text-sm uppercase tracking-widest mb-3 flex items-center gap-2">
            <Cpu className={`w-3.5 h-3.5 ${burnColor}`} /> LLM call breakdown (today)
          </h2>
          <ul className="space-y-2 text-xs font-mono">
            <CostRow label="Video forensic scans" calls={data.llm_costs.breakdown_today.video_analysis_calls} unitCost={0.18} />
            <CostRow label="Legitimacy reports" calls={data.llm_costs.breakdown_today.legitimacy_report_calls} unitCost={0.06} />
            <CostRow label="Live frame analyses" calls={data.llm_costs.breakdown_today.live_frame_calls} unitCost={0.012} />
            <CostRow label="Live summaries" calls={data.llm_costs.breakdown_today.live_summary_calls} unitCost={0.02} />
          </ul>
          <div className="mt-4 pt-3 border-t border-white/10 text-[11px] font-mono text-white/60">
            7-day cache hits saved <span className="text-[var(--neon)]">{fmtUSD(data.llm_costs.cache_savings_7d_usd)}</span>
          </div>
        </div>

        {/* Recent signups */}
        <div className="panel p-5" data-testid="dashboard-signups">
          <h2 className="font-heading text-sm uppercase tracking-widest mb-3 flex items-center gap-2">
            <Users className="w-3.5 h-3.5 text-[var(--neon)]" /> Recent signups
          </h2>
          {data.recent_signups.length === 0 ? (
            <p className="text-xs font-mono text-white/40">No recent signups.</p>
          ) : (
            <ul className="space-y-2 text-xs font-mono">
              {data.recent_signups.map((u) => (
                <li key={u.id} className="flex items-start justify-between gap-2 border-b border-white/5 pb-2 last:border-0">
                  <div className="min-w-0 flex-1">
                    <p className="text-white/80 truncate">{u.email}</p>
                    <p className="text-[10px] text-white/40">
                      {new Date(u.created_at).toLocaleString()}
                      {u.signup_source && <> · <span className="text-[var(--neon)]">{u.signup_source}</span></>}
                    </p>
                  </div>
                  {u.is_premium && (
                    <span className="text-[10px] text-[var(--neon)] uppercase">PREMIUM</span>
                  )}
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>

      {/* Quick links */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mt-8">
        <QuickLink to="/admin/disputes" label="Moderate disputes" count={data.moderation.pending_disputes} />
        <QuickLink to="/admin/affiliates" label="Affiliates" />
        <QuickLink to="/admin/digest" label="Weekly digest" />
        <QuickLink to="/scams" label="Scam Wall" count={data.recent_scams.length} />
      </div>
    </div>
  );
}

function Kpi({ icon, label, value, sub, accent = "ok", testid }) {
  const colors = {
    ok: "border-white/15",
    neon: "border-[var(--neon)]/40",
    warn: "border-yellow-400/50",
    danger: "border-[var(--danger)]/60",
  };
  return (
    <div className={`panel p-4 ${colors[accent]}`} data-testid={testid}>
      <div className="flex items-center gap-2 text-[10px] uppercase tracking-widest text-white/50 mb-2">
        {icon} {label}
      </div>
      <p className="font-heading text-2xl text-white tracking-tight">{value}</p>
      <p className="text-[10px] font-mono text-white/40 mt-1">{sub}</p>
    </div>
  );
}

function CostRow({ label, calls, unitCost }) {
  const total = (calls * unitCost).toFixed(2);
  return (
    <li className="flex justify-between items-center">
      <span className="text-white/70">{label}</span>
      <span className="font-mono text-white/60">
        {calls} × ${unitCost.toFixed(3)} = <span className="text-[var(--neon)]">${total}</span>
      </span>
    </li>
  );
}

function QuickLink({ to, label, count }) {
  return (
    <Link to={to} className="panel p-4 hover:bg-white/[0.02] transition flex items-center justify-between group">
      <span className="text-xs font-mono uppercase tracking-widest text-white/70 group-hover:text-[var(--neon)]">{label}</span>
      <div className="flex items-center gap-2">
        {count !== undefined && count > 0 && (
          <span className="text-[10px] font-mono px-1.5 py-0.5 border border-[var(--neon)]/40 text-[var(--neon)]">{count}</span>
        )}
        <ChevronRight className="w-3 h-3 text-white/40" />
      </div>
    </Link>
  );
}
