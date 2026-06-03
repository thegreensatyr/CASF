import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { api } from "../lib/api";
import { ShieldCheck, ShieldAlert, ShieldX, Copy, Check, Twitter, ArrowLeft, ExternalLink } from "lucide-react";
import { toast } from "sonner";
import TrustedCasinoCTA from "../components/TrustedCasinoCTA";

export default function PublicReport() {
  const { slug } = useParams();
  const [report, setReport] = useState(null);
  const [notFound, setNotFound] = useState(false);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    api.get(`/legitimacy/public/${slug}`)
      .then((r) => setReport(r.data))
      .catch(() => setNotFound(true));
  }, [slug]);

  useEffect(() => {
    if (report) {
      document.title = `${report.casino_name} — Trust Report ${report.trust_score}/100 · Casino Spotter`;
      // Inject Schema.org Review JSON-LD for SEO
      const existing = document.getElementById("report-schema");
      if (existing) existing.remove();
      const schema = {
        "@context": "https://schema.org",
        "@type": "Review",
        "itemReviewed": {
          "@type": "Organization",
          "name": report.casino_name,
          ...(report.casino_url ? { "url": report.casino_url } : {}),
        },
        "reviewRating": {
          "@type": "Rating",
          "ratingValue": report.trust_score,
          "bestRating": 100,
          "worstRating": 0,
        },
        "author": { "@type": "Organization", "name": "Casino Spotter" },
        "datePublished": report.created_at,
        "reviewBody": report.report,
        "name": `${report.casino_name} Trust Report`,
      };
      const s = document.createElement("script");
      s.type = "application/ld+json";
      s.id = "report-schema";
      s.text = JSON.stringify(schema);
      document.head.appendChild(s);
    }
    return () => {
      const existing = document.getElementById("report-schema");
      if (existing) existing.remove();
    };
  }, [report]);

  const shareUrl = typeof window !== "undefined" ? window.location.href : "";
  const shareText = report
    ? `${report.casino_name} got a ${report.trust_score}/100 trust score on Casino Spotter — ${report.verdict}`
    : "";

  const copyLink = () => {
    navigator.clipboard.writeText(shareUrl);
    setCopied(true);
    toast.success("Link copied — paste it anywhere");
    setTimeout(() => setCopied(false), 2000);
  };

  const shareTwitter = () => {
    const u = `https://twitter.com/intent/tweet?text=${encodeURIComponent(shareText)}&url=${encodeURIComponent(shareUrl)}`;
    window.open(u, "_blank", "noopener");
  };

  const shareReddit = () => {
    const u = `https://www.reddit.com/submit?url=${encodeURIComponent(shareUrl)}&title=${encodeURIComponent(shareText)}`;
    window.open(u, "_blank", "noopener");
  };

  if (notFound) {
    return (
      <div className="max-w-md mx-auto p-10 text-center">
        <p className="font-mono text-sm text-white/70 mb-4">Report not found or has been removed.</p>
        <Link to="/legitimacy" className="btn-neon">Verify a casino &gt;_</Link>
      </div>
    );
  }
  if (!report) return <div className="p-10 text-[var(--neon)] font-mono">Loading report...</div>;

  const scoreBadge = (() => {
    const s = report.trust_score;
    if (s >= 75) return { Icon: ShieldCheck, color: "text-[var(--neon)] border-[var(--neon)]", label: "TRUSTED" };
    if (s >= 45) return { Icon: ShieldAlert, color: "text-[var(--warn)] border-[var(--warn)]", label: "CAUTIOUS" };
    return { Icon: ShieldX, color: "text-[var(--danger)] border-[var(--danger)]", label: "AVOID" };
  })();
  const { Icon } = scoreBadge;

  return (
    <div className="max-w-5xl mx-auto px-6 md:px-12 py-12">
      <div className="flex items-center justify-between flex-wrap gap-4 mb-8">
        <Link to="/reports" className="inline-flex items-center gap-2 text-xs uppercase tracking-widest" data-testid="back-to-reports">
          <ArrowLeft className="w-3 h-3" /> All public reports
        </Link>
        <div className="flex items-center gap-2">
          <button onClick={copyLink} className="btn-ghost text-xs flex items-center gap-1" data-testid="share-copy">
            {copied ? <><Check className="w-3 h-3"/> Copied</> : <><Copy className="w-3 h-3"/> Copy link</>}
          </button>
          <button onClick={shareTwitter} className="btn-ghost text-xs flex items-center gap-1" data-testid="share-twitter">
            <Twitter className="w-3 h-3"/> X
          </button>
          <button onClick={shareReddit} className="btn-ghost text-xs" data-testid="share-reddit">Reddit</button>
        </div>
      </div>

      <p className="text-xs uppercase tracking-[0.3em] text-[var(--neon)] mb-2">// public trust report</p>
      <h1 className="font-heading text-4xl md:text-6xl tracking-tighter mb-4">{report.casino_name}</h1>
      {report.casino_url && (
        <a href={report.casino_url} target="_blank" rel="noopener noreferrer nofollow"
           className="text-xs text-white/50 font-mono inline-flex items-center gap-1 mb-6">
          <ExternalLink className="w-3 h-3" /> {report.casino_url}
        </a>
      )}

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6" data-testid="public-report">
        <div className={`panel p-6 ${scoreBadge.color} border-2`}>
          <Icon className="w-8 h-8 mb-3" />
          <div className="text-[10px] uppercase tracking-[0.3em] text-white/60">trust score</div>
          <div className="font-heading text-6xl mt-1">{report.trust_score}<span className="text-white/40 text-2xl">/100</span></div>
          <div className={`mt-3 tag ${scoreBadge.color}`}>{scoreBadge.label}</div>
          <p className="text-xs font-mono text-white/70 mt-4">{report.verdict}</p>
          <p className="text-[10px] text-white/40 mt-4 font-mono">
            Issued {new Date(report.created_at).toLocaleDateString()}
          </p>
        </div>

        <div className="panel p-6 md:col-span-2">
          <h3 className="font-heading text-lg mb-3 text-[var(--neon)]">// Investigative report</h3>
          <p className="text-sm font-mono text-white/85 whitespace-pre-line leading-relaxed">{report.report}</p>
        </div>

        <div className="panel p-6 border-[var(--danger)]/40">
          <h3 className="font-heading text-sm mb-3 text-[var(--danger)] uppercase tracking-widest">Red flags</h3>
          {report.red_flags.length ? (
            <ul className="text-xs font-mono space-y-1 text-white/80">
              {report.red_flags.map((f,i)=>(<li key={i}>&gt; {f}</li>))}
            </ul>
          ) : (<p className="text-xs text-white/40 font-mono">none detected</p>)}
        </div>

        <div className="panel p-6 border-[var(--neon)]/30 md:col-span-2">
          <h3 className="font-heading text-sm mb-3 text-[var(--neon)] uppercase tracking-widest">Green flags</h3>
          {report.green_flags.length ? (
            <ul className="text-xs font-mono space-y-1 text-white/80">
              {report.green_flags.map((f,i)=>(<li key={i}>&gt; {f}</li>))}
            </ul>
          ) : (<p className="text-xs text-white/40 font-mono">none detected</p>)}
        </div>
      </div>

      {report.trust_score < 60 && (
        <TrustedCasinoCTA source={`public-report:${report.slug}`} headline="SAFER ALTERNATIVES" />
      )}

      <div className="panel p-6 mt-10 text-center">
        <p className="text-xs font-mono text-white/70">
          Want a forensic AI scan of your own casino sessions?
        </p>
        <Link to="/signup" className="btn-neon inline-block mt-3 text-xs" data-testid="public-report-cta-signup">
          Sign up free &gt;_
        </Link>
      </div>

      <footer className="border-t border-white/10 mt-12 py-6 text-center text-[10px] text-white/40 font-mono">
        Report generated by Claude Sonnet 4.5 + Casino Spotter's curated database.
        Educational purposes only · 18+ · BeGambleAware.org
      </footer>
    </div>
  );
}

export function PublicReportsList() {
  const [reports, setReports] = useState([]);
  const [query, setQuery] = useState("");
  const [sortBy, setSortBy] = useState("recent");
  const [filter, setFilter] = useState("all");

  useEffect(() => { api.get("/legitimacy/public?limit=100").then((r) => setReports(r.data)).catch(()=>{}); }, []);
  useEffect(() => { document.title = "Public Casino Trust Reports · Casino Spotter"; }, []);

  const filtered = (() => {
    let out = [...reports];
    if (query.trim()) {
      const q = query.toLowerCase();
      out = out.filter((r) => r.casino_name.toLowerCase().includes(q));
    }
    if (filter === "avoid") out = out.filter((r) => r.trust_score < 45);
    else if (filter === "cautious") out = out.filter((r) => r.trust_score >= 45 && r.trust_score < 75);
    else if (filter === "trusted") out = out.filter((r) => r.trust_score >= 75);

    if (sortBy === "score-asc") out.sort((a,b) => a.trust_score - b.trust_score);
    else if (sortBy === "score-desc") out.sort((a,b) => b.trust_score - a.trust_score);
    else out.sort((a,b) => new Date(b.created_at) - new Date(a.created_at));
    return out;
  })();

  return (
    <div className="max-w-6xl mx-auto px-6 md:px-12 py-12">
      <p className="text-xs uppercase tracking-[0.3em] text-[var(--neon)] mb-2">// public archive</p>
      <h1 className="font-heading text-4xl md:text-5xl tracking-tighter mb-2">PUBLIC TRUST REPORTS</h1>
      <p className="text-sm text-white/60 font-mono mb-8">
        &gt; Every report ever generated by our community. <span className="text-[var(--neon)]">{reports.length}</span> casinos analyzed and counting.
      </p>

      <div className="flex flex-wrap items-center gap-3 mb-6">
        <input
          data-testid="reports-search"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search casino name..."
          className="input-neon max-w-sm"
        />
        <div className="flex gap-1">
          {[["all","All"],["trusted","Trusted"],["cautious","Cautious"],["avoid","Avoid"]].map(([k,l]) => (
            <button
              key={k}
              data-testid={`reports-filter-${k}`}
              onClick={() => setFilter(k)}
              className={`px-3 py-1.5 text-[10px] uppercase tracking-widest font-heading border transition ${
                filter === k ? "border-[var(--neon)] text-[var(--neon)] bg-[var(--neon-glow)]" : "border-white/20 text-white/60 hover:border-[var(--neon)]"
              }`}
            >{l}</button>
          ))}
        </div>
        <select
          data-testid="reports-sort"
          value={sortBy}
          onChange={(e) => setSortBy(e.target.value)}
          className="input-neon max-w-[200px]"
        >
          <option value="recent" className="bg-black">Most recent</option>
          <option value="score-asc" className="bg-black">Lowest score first</option>
          <option value="score-desc" className="bg-black">Highest score first</option>
        </select>
      </div>

      {filtered.length === 0 && (
        <p className="text-xs font-mono text-white/40">No reports match. <Link to="/legitimacy" className="text-[var(--neon)]">Generate one &gt;_</Link></p>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
        {filtered.map((r) => {
          const color = r.trust_score >= 75 ? "border-[var(--neon)]/40 text-[var(--neon)]"
                       : r.trust_score >= 45 ? "border-[var(--warn)]/40 text-[var(--warn)]"
                       : "border-[var(--danger)]/40 text-[var(--danger)]";
          return (
            <Link key={r.slug} to={`/report/${r.slug}`} data-testid={`public-card-${r.slug}`}
              className={`panel p-5 hover:bg-white/[0.02] transition ${color}`}>
              <div className="flex items-center justify-between mb-2">
                <span className="font-heading text-base text-white truncate">{r.casino_name}</span>
                <span className="font-heading text-2xl">{r.trust_score}</span>
              </div>
              <p className="text-[10px] uppercase tracking-widest opacity-80">{r.verdict}</p>
              <p className="text-[10px] text-white/40 mt-2 font-mono">{new Date(r.created_at).toLocaleDateString()}</p>
            </Link>
          );
        })}
      </div>
    </div>
  );
}
