import { useEffect, useState } from "react";
import { api } from "../lib/api";
import { Link, useParams } from "react-router-dom";
import { AlertTriangle, ArrowLeft } from "lucide-react";
import TrustedCasinoCTA from "../components/TrustedCasinoCTA";

const SEVERITY_COLOR = {
  low: "text-white/70 border-white/30",
  medium: "text-[var(--warn)] border-[var(--warn)]/60",
  high: "text-orange-400 border-orange-500/60",
  critical: "text-[var(--danger)] border-[var(--danger)]/60",
};

export function Techniques() {
  const [items, setItems] = useState([]);
  useEffect(() => { api.get("/techniques").then((r) => setItems(r.data)); }, []);
  return (
    <div className="max-w-7xl mx-auto px-6 md:px-12 py-16">
      <div className="flex items-end justify-between mb-10">
        <div>
          <p className="text-xs uppercase tracking-[0.3em] text-[var(--neon)] mb-2">// library</p>
          <h1 className="font-heading text-4xl md:text-5xl tracking-tighter">KNOWN TRICKS</h1>
        </div>
        <span className="text-xs font-mono text-white/40 hidden md:inline">{items.length} dossiers</span>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {items.map((t) => (
          <Link key={t.slug} to={`/techniques/${t.slug}`} data-testid={`technique-card-${t.slug}`}
            className="panel p-6 hover:bg-white/[0.02] transition">
            <div className="flex items-center justify-between mb-3">
              <span className={`tag ${SEVERITY_COLOR[t.severity]}`}>{t.severity}</span>
              <span className="text-[10px] uppercase tracking-widest text-white/40">{t.category}</span>
            </div>
            <h3 className="font-heading text-xl mb-2">{t.name}</h3>
            <p className="text-xs text-white/70 font-mono leading-relaxed">{t.short}</p>
            <div className="mt-4 text-[10px] text-[var(--neon)] uppercase tracking-widest">read dossier &gt;_</div>
          </Link>
        ))}
      </div>
    </div>
  );
}

export function TechniqueDetail() {
  const { slug } = useParams();
  const [t, setT] = useState(null);
  useEffect(() => { api.get(`/techniques/${slug}`).then((r) => setT(r.data)); }, [slug]);
  if (!t) return <div className="p-10 text-[var(--neon)] font-mono">Loading dossier...</div>;
  return (
    <div className="max-w-4xl mx-auto px-6 md:px-12 py-16">
      <Link to="/techniques" className="inline-flex items-center gap-2 text-xs uppercase tracking-widest mb-8" data-testid="back-to-techniques">
        <ArrowLeft className="w-3 h-3" /> All tricks
      </Link>
      <span className={`tag ${SEVERITY_COLOR[t.severity]}`}>{t.severity} severity</span>
      <h1 className="font-heading text-4xl md:text-5xl tracking-tighter mt-4 mb-2">{t.name}</h1>
      <p className="text-xs uppercase tracking-widest text-white/60 mb-8">{t.category}</p>
      <Section title="Overview" body={t.description} />
      <Section title="How it works" body={t.how_it_works} />
      <Section title="How to spot it" body={t.how_to_spot} />
      <div className="panel p-6 mt-10 border-[var(--warn)]/40">
        <AlertTriangle className="w-5 h-5 text-[var(--warn)] mb-2" />
        <p className="text-xs font-mono text-white/80">
          If you suspect a casino is using this on you, run a video clip through our analyzer.
        </p>
        <Link to="/analyze" className="btn-neon inline-block mt-4 text-xs">Open analyzer &gt;_</Link>
      </div>
      <TrustedCasinoCTA source={`technique:${t.slug}`} headline={`CASINOS THAT DON'T DO ${t.name.toUpperCase()}`} />
    </div>
  );
}

function Section({ title, body }) {
  return (
    <div className="mb-8">
      <h2 className="font-heading text-lg mb-2 text-[var(--neon)]">// {title}</h2>
      <p className="text-sm font-mono text-white/80 leading-relaxed whitespace-pre-line">{body}</p>
    </div>
  );
}
