import { useEffect, useState, useMemo } from "react";
import { Link } from "react-router-dom";
import { api } from "../lib/api";
import { X, GitCompare, ShieldCheck, ShieldAlert, ShieldX } from "lucide-react";

export default function Compare() {
  const [allReports, setAllReports] = useState([]);
  const [picked, setPicked] = useState([]);
  const [query, setQuery] = useState("");

  useEffect(() => {
    document.title = "Compare Casinos · Casino Spotter";
    api.get("/legitimacy/public?limit=100").then((r) => setAllReports(r.data)).catch(() => {});
  }, []);

  const filtered = useMemo(() => {
    if (!query.trim()) return allReports.slice(0, 12);
    const q = query.toLowerCase();
    return allReports.filter((r) => r.casino_name.toLowerCase().includes(q)).slice(0, 12);
  }, [query, allReports]);

  const toggle = (r) => {
    setPicked((prev) => {
      if (prev.find((p) => p.slug === r.slug)) return prev.filter((p) => p.slug !== r.slug);
      if (prev.length >= 3) return [...prev.slice(1), r];
      return [...prev, r];
    });
  };

  return (
    <div className="max-w-7xl mx-auto px-6 md:px-12 py-12">
      <p className="text-xs uppercase tracking-[0.3em] text-[var(--neon)] mb-2">// side-by-side</p>
      <h1 className="font-heading text-4xl md:text-5xl tracking-tighter mb-2 flex items-center gap-3">
        <GitCompare className="w-8 h-8 text-[var(--neon)]" /> COMPARE CASINOS
      </h1>
      <p className="text-sm text-white/60 font-mono mb-8">
        &gt; Pick up to 3 casinos from our public archive to see them head-to-head.
      </p>

      <div className="mb-6">
        <input
          data-testid="compare-search"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search the archive..."
          className="input-neon max-w-md"
        />
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-2 mb-10">
        {filtered.map((r) => {
          const active = picked.find((p) => p.slug === r.slug);
          return (
            <button
              key={r.slug}
              data-testid={`compare-pick-${r.slug}`}
              onClick={() => toggle(r)}
              className={`panel p-3 text-left transition ${active ? "border-[var(--neon)] bg-[var(--neon-glow)]" : "hover:border-[var(--neon-dim)]"}`}
            >
              <div className="text-xs font-heading truncate">{r.casino_name}</div>
              <div className={`text-base font-heading ${scoreColor(r.trust_score)}`}>{r.trust_score}</div>
            </button>
          );
        })}
      </div>

      {picked.length === 0 ? (
        <div className="panel p-10 text-center">
          <p className="text-xs font-mono text-white/50">Pick 2-3 casinos above to compare them.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4" data-testid="compare-grid">
          {picked.map((r) => <CompareCard key={r.slug} r={r} onRemove={() => toggle(r)} />)}
        </div>
      )}
    </div>
  );
}

function CompareCard({ r, onRemove }) {
  const { Icon, color, label } = badge(r.trust_score);
  return (
    <div className={`panel p-6 border-2 ${color}`}>
      <div className="flex items-start justify-between mb-3">
        <Icon className="w-7 h-7" />
        <button onClick={onRemove} className="text-white/40 hover:text-white" data-testid={`compare-remove-${r.slug}`}>
          <X className="w-4 h-4" />
        </button>
      </div>
      <h3 className="font-heading text-xl mb-1">{r.casino_name}</h3>
      <div className="font-heading text-5xl mb-1">{r.trust_score}<span className="text-white/40 text-lg">/100</span></div>
      <div className={`tag mb-4 ${color}`}>{label}</div>
      <p className="text-xs font-mono text-white/70 mb-4">{r.verdict}</p>

      <div className="text-[10px] uppercase tracking-widest text-[var(--danger)] mb-1">Red flags ({r.red_flags?.length || 0})</div>
      <ul className="text-[11px] font-mono text-white/70 mb-3 space-y-0.5">
        {(r.red_flags || []).slice(0, 4).map((f, i) => (<li key={i} className="truncate">&gt; {f}</li>))}
      </ul>

      <div className="text-[10px] uppercase tracking-widest text-[var(--neon)] mb-1">Green flags ({r.green_flags?.length || 0})</div>
      <ul className="text-[11px] font-mono text-white/70 mb-4 space-y-0.5">
        {(r.green_flags || []).slice(0, 4).map((f, i) => (<li key={i} className="truncate">&gt; {f}</li>))}
      </ul>

      <Link to={`/report/${r.slug}`} className="btn-ghost w-full text-xs text-center block">Full report &gt;_</Link>
    </div>
  );
}

function scoreColor(s) {
  if (s >= 75) return "text-[var(--neon)]";
  if (s >= 45) return "text-[var(--warn)]";
  return "text-[var(--danger)]";
}

function badge(s) {
  if (s >= 75) return { Icon: ShieldCheck, color: "border-[var(--neon)] text-[var(--neon)]", label: "TRUSTED" };
  if (s >= 45) return { Icon: ShieldAlert, color: "border-[var(--warn)] text-[var(--warn)]", label: "CAUTIOUS" };
  return { Icon: ShieldX, color: "border-[var(--danger)] text-[var(--danger)]", label: "AVOID" };
}
