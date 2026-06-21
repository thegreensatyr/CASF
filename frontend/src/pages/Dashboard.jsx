import { useEffect, useMemo, useState } from "react";
import { api } from "../lib/api";
import { Link } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { ScanLine, ShieldCheck, History, Mail, Radio, AlertTriangle, ChevronRight } from "lucide-react";
import { toast } from "sonner";

export default function Dashboard() {
  const { user } = useAuth();
  const [analyses, setAnalyses] = useState([]);
  const [legits, setLegits] = useState([]);
  const [liveSessions, setLiveSessions] = useState([]);
  const [subscribed, setSubscribed] = useState(true);
  const [liveSort, setLiveSort] = useState("recent");      // recent | flagged | clean
  const [liveTechFilter, setLiveTechFilter] = useState(""); // technique slug

  useEffect(() => {
    api.get("/analysis/history").then((r) => setAnalyses(r.data)).catch(()=>{});
    api.get("/legitimacy/history").then((r) => setLegits(r.data)).catch(()=>{});
    api.get("/live/sessions").then((r) => setLiveSessions(r.data)).catch(()=>{});
  }, []);

  useEffect(() => {
    if (user) setSubscribed(user.email_digest_subscribed !== false);
  }, [user]);

  const toggleDigest = async () => {
    const next = !subscribed;
    setSubscribed(next);
    try {
      await api.patch("/user/preferences", { subscribed: next });
      toast.success(next ? "Subscribed to weekly digest" : "Unsubscribed from digest");
    } catch (e) {
      setSubscribed(!next);
      toast.error("Failed to update");
    }
  };

  const allLiveTechniques = useMemo(() => {
    const s = new Set();
    liveSessions.forEach((sess) => sess.techniques_aggregated?.forEach((t) => s.add(t)));
    return [...s].sort();
  }, [liveSessions]);

  const visibleLiveSessions = useMemo(() => {
    let list = [...liveSessions];
    if (liveTechFilter) {
      list = list.filter((s) => (s.techniques_aggregated || []).includes(liveTechFilter));
    }
    if (liveSort === "flagged") {
      list.sort((a, b) => (b.techniques_aggregated?.length || 0) - (a.techniques_aggregated?.length || 0));
    } else if (liveSort === "clean") {
      list.sort((a, b) => (a.techniques_aggregated?.length || 0) - (b.techniques_aggregated?.length || 0));
    } else {
      list.sort((a, b) => new Date(b.started_at) - new Date(a.started_at));
    }
    return list;
  }, [liveSessions, liveSort, liveTechFilter]);

  return (
    <div className="max-w-7xl mx-auto px-6 md:px-12 py-12">
      <div className="flex items-end justify-between mb-10">
        <div>
          <p className="text-xs uppercase tracking-[0.3em] text-[var(--neon)] mb-2">// control room</p>
          <h1 className="font-heading text-4xl md:text-5xl tracking-tighter">WELCOME, {(user?.name||"").toUpperCase()}</h1>
        </div>
        <span className="hidden md:flex items-center gap-2 text-xs text-white/40 font-mono">
          <span className="dot-pulse w-2 h-2 rounded-full bg-[var(--neon)]" /> system online
        </span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-10">
        <Stat label="Scans run" value={analyses.length} />
        <Stat label="Casinos checked" value={legits.length} />
        <Stat label="Avg trust score" value={
          legits.length ? Math.round(legits.reduce((a,r)=>a+r.trust_score,0)/legits.length) : "—"
        }/>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-12">
        <Link to="/analyze" className="panel p-8 hover:bg-white/[0.02] transition" data-testid="quick-analyze">
          <ScanLine className="w-6 h-6 text-[var(--neon)] mb-3" />
          <h3 className="font-heading text-xl mb-1">New scan</h3>
          <p className="text-xs text-white/60 font-mono">Drop a clip or screenshot for forensic analysis.</p>
        </Link>
        <Link to="/live" className="panel p-8 hover:bg-white/[0.02] transition relative overflow-hidden" data-testid="quick-live">
          <div className="absolute top-3 right-3 flex items-center gap-1 text-[10px] uppercase tracking-widest font-mono text-[var(--neon)]">
            <span className="w-1.5 h-1.5 rounded-full bg-[var(--neon)] animate-pulse" /> new
          </div>
          <Radio className="w-6 h-6 text-[var(--neon)] mb-3" />
          <h3 className="font-heading text-xl mb-1">Live capture</h3>
          <p className="text-xs text-white/60 font-mono">Share your screen and get real-time technique alerts as you play.</p>
        </Link>
        <Link to="/legitimacy" className="panel p-8 hover:bg-white/[0.02] transition" data-testid="quick-legit">
          <ShieldCheck className="w-6 h-6 text-[var(--neon)] mb-3" />
          <h3 className="font-heading text-xl mb-1">Verify casino</h3>
          <p className="text-xs text-white/60 font-mono">Pull a trust report on any operator.</p>
        </Link>
      </div>


      <div className="panel p-6 mb-12 flex items-center justify-between flex-wrap gap-4" data-testid="digest-pref-panel">
        <div className="flex items-center gap-3">
          <Mail className="w-5 h-5 text-[var(--neon)]" />
          <div>
            <h3 className="font-heading text-base">Weekly digest email</h3>
            <p className="text-[11px] text-white/60 font-mono">Top 5 lowest-trust casinos + 1 safer alternative, every Monday.</p>
          </div>
        </div>
        <button
          onClick={toggleDigest}
          data-testid="digest-toggle"
          className={`px-4 py-2 text-xs uppercase tracking-widest font-heading border transition ${
            subscribed ? "border-[var(--neon)] text-[var(--neon)] bg-[var(--neon-glow)]" : "border-white/30 text-white/60"
          }`}
        >
          {subscribed ? "Subscribed ✓" : "Subscribe"}
        </button>
      </div>

      <div className="flex items-center justify-between mb-4 flex-wrap gap-3">
        <h2 className="font-heading text-xl flex items-center gap-2">
          <Radio className="w-4 h-4 text-[var(--neon)]" /> LIVE SESSIONS
          <span className="text-xs font-mono text-white/40 ml-2">({liveSessions.length})</span>
        </h2>
        <div className="flex items-center gap-2 flex-wrap">
          <select
            value={liveSort}
            onChange={(e) => setLiveSort(e.target.value)}
            className="bg-black/60 border border-white/15 text-[11px] font-mono uppercase tracking-widest text-white/70 px-2 py-1.5"
            data-testid="live-sessions-sort"
          >
            <option value="recent">sort: most recent</option>
            <option value="flagged">sort: most flagged</option>
            <option value="clean">sort: least flagged</option>
          </select>
          {allLiveTechniques.length > 0 && (
            <select
              value={liveTechFilter}
              onChange={(e) => setLiveTechFilter(e.target.value)}
              className="bg-black/60 border border-white/15 text-[11px] font-mono uppercase tracking-widest text-white/70 px-2 py-1.5"
              data-testid="live-sessions-filter"
            >
              <option value="">filter: all techniques</option>
              {allLiveTechniques.map((t) => <option key={t} value={t}>{t}</option>)}
            </select>
          )}
          <Link to="/live" className="btn-neon text-[11px]" data-testid="live-sessions-new-cta">
            <Radio className="w-3 h-3 inline mr-1" /> NEW SESSION &gt;_
          </Link>
        </div>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3 mb-12">
        {visibleLiveSessions.length === 0 && (
          <div className="text-xs text-white/40 font-mono col-span-full panel p-5" data-testid="live-sessions-empty">
            &gt; no live sessions yet. <Link to="/live" className="text-[var(--neon)] underline">Run your first one</Link>.
          </div>
        )}
        {visibleLiveSessions.slice(0, 9).map((s) => {
          const flagged = (s.techniques_aggregated || []).length;
          return (
            <Link
              key={s.id}
              to={`/live/sessions/${s.id}`}
              className="panel p-4 hover:bg-white/[0.02] transition group"
              data-testid={`live-session-card-${s.id}`}
            >
              <div className="flex items-center justify-between mb-2">
                <span className="tag flex items-center gap-1">
                  <Radio className="w-3 h-3" /> {s.game_type}
                </span>
                <span className="text-[10px] text-white/40">{new Date(s.started_at).toLocaleDateString()}</span>
              </div>
              <p className="font-heading text-sm mb-1 truncate">{s.casino_name || "unspecified casino"}</p>
              <div className="flex items-center justify-between text-[10px] font-mono text-white/50 mb-2">
                <span>{s.frame_count} frame{s.frame_count === 1 ? "" : "s"}</span>
                {flagged > 0 ? (
                  <span className="text-[var(--danger)] flex items-center gap-1">
                    <AlertTriangle className="w-3 h-3" /> {flagged} flagged
                  </span>
                ) : (
                  <span className="text-white/40">clean</span>
                )}
              </div>
              {flagged > 0 && (
                <div className="flex flex-wrap gap-1 mb-2">
                  {(s.techniques_aggregated || []).slice(0, 3).map((t, i) => (
                    <span key={i} className="text-[9px] font-mono px-1.5 py-0.5 border border-[var(--neon)]/30 text-[var(--neon)]">
                      {t}
                    </span>
                  ))}
                  {flagged > 3 && (
                    <span className="text-[9px] font-mono px-1.5 py-0.5 text-white/40">+{flagged - 3}</span>
                  )}
                </div>
              )}
              <div className="flex items-center justify-end text-[10px] uppercase tracking-widest text-[var(--neon)]/60 group-hover:text-[var(--neon)] transition">
                view detail <ChevronRight className="w-3 h-3" />
              </div>
            </Link>
          );
        })}
      </div>

      <h2 className="font-heading text-xl mb-4 flex items-center gap-2">
        <History className="w-4 h-4 text-[var(--neon)]" /> RECENT SCANS
      </h2>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3 mb-12">
        {analyses.length === 0 && <div className="text-xs text-white/40 font-mono">&gt; no scans yet</div>}
        {analyses.slice(0,9).map((a) => (
          <div key={a.id} className="panel p-4" data-testid={`history-analysis-${a.id}`}>
            <div className="flex items-center justify-between mb-2">
              <span className="tag">{a.media_type}</span>
              <span className="text-[10px] text-white/40">{new Date(a.created_at).toLocaleDateString()}</span>
            </div>
            <p className="font-heading text-sm mb-1">{a.game_type}</p>
            <p className="text-[10px] text-white/50 font-mono mb-2">{a.casino_name || "unspecified casino"}</p>
            <p className="text-xs text-white/75 font-mono line-clamp-3">{a.analysis.slice(0, 160)}...</p>
          </div>
        ))}
      </div>

      <h2 className="font-heading text-xl mb-4 flex items-center gap-2">
        <ShieldCheck className="w-4 h-4 text-[var(--neon)]" /> RECENT TRUST CHECKS
      </h2>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
        {legits.length === 0 && <div className="text-xs text-white/40 font-mono">&gt; no lookups yet</div>}
        {legits.slice(0,6).map((l) => (
          <div key={l.id} className="panel p-4">
            <div className="flex items-center justify-between mb-2">
              <span className="font-heading text-sm">{l.casino_name}</span>
              <span className="text-[var(--neon)] font-heading text-lg">{l.trust_score}</span>
            </div>
            <p className="text-[10px] uppercase tracking-widest text-white/50">{l.verdict}</p>
          </div>
        ))}
      </div>
    </div>
  );
}

function Stat({ label, value }) {
  return (
    <div className="panel p-6">
      <div className="font-heading text-4xl text-[var(--neon)]">{value}</div>
      <div className="text-xs uppercase tracking-widest text-white/60">{label}</div>
    </div>
  );
}
