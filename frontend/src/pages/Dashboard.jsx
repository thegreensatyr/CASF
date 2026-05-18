import { useEffect, useState } from "react";
import { api } from "../lib/api";
import { Link } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { ScanLine, ShieldCheck, History } from "lucide-react";

export default function Dashboard() {
  const { user } = useAuth();
  const [analyses, setAnalyses] = useState([]);
  const [legits, setLegits] = useState([]);

  useEffect(() => {
    api.get("/analysis/history").then((r) => setAnalyses(r.data)).catch(()=>{});
    api.get("/legitimacy/history").then((r) => setLegits(r.data)).catch(()=>{});
  }, []);

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

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-12">
        <Link to="/analyze" className="panel p-8 hover:bg-white/[0.02] transition" data-testid="quick-analyze">
          <ScanLine className="w-6 h-6 text-[var(--neon)] mb-3" />
          <h3 className="font-heading text-xl mb-1">New scan</h3>
          <p className="text-xs text-white/60 font-mono">Drop a clip or screenshot for forensic analysis.</p>
        </Link>
        <Link to="/legitimacy" className="panel p-8 hover:bg-white/[0.02] transition" data-testid="quick-legit">
          <ShieldCheck className="w-6 h-6 text-[var(--neon)] mb-3" />
          <h3 className="font-heading text-xl mb-1">Verify casino</h3>
          <p className="text-xs text-white/60 font-mono">Pull a trust report on any operator.</p>
        </Link>
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
