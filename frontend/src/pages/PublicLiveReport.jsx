import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import axios from "axios";
import { Radio, AlertTriangle, Clock, Loader2, Share2, ShieldCheck, MessageSquare } from "lucide-react";
import LegalDisclaimer from "../components/LegalDisclaimer";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

export default function PublicLiveReport() {
  const { slug } = useParams();
  const [data, setData] = useState(null);
  const [disputes, setDisputes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState("");

  useEffect(() => {
    axios.get(`${BACKEND_URL}/api/live/public/${slug}`)
      .then((r) => setData(r.data))
      .catch((e) => setErr(e?.response?.data?.detail || "Report not found"))
      .finally(() => setLoading(false));
    axios.get(`${BACKEND_URL}/api/disputes/public/live/${slug}`)
      .then((r) => setDisputes(r.data))
      .catch(() => {});
  }, [slug]);

  useEffect(() => {
    if (!data) return;
    document.title = `${data.headline} · Casino Spotter`;
    // Inject JSON-LD for SEO
    const ld = {
      "@context": "https://schema.org",
      "@type": "Report",
      "headline": data.headline,
      "datePublished": data.published_at,
      "about": data.casino_name || "online casino",
      "keywords": data.techniques_aggregated.join(", "),
      "author": { "@type": "Organization", "name": "Casino Spotter" },
    };
    let tag = document.getElementById("live-report-ld");
    if (!tag) {
      tag = document.createElement("script");
      tag.type = "application/ld+json";
      tag.id = "live-report-ld";
      document.head.appendChild(tag);
    }
    tag.textContent = JSON.stringify(ld);
    return () => { tag?.remove(); };
  }, [data]);

  if (loading) {
    return (
      <div className="max-w-5xl mx-auto px-6 py-20 text-center">
        <Loader2 className="w-6 h-6 animate-spin text-[var(--neon)] mx-auto" />
      </div>
    );
  }

  if (err || !data) {
    return (
      <div className="max-w-3xl mx-auto px-6 py-20">
        <p className="text-sm font-mono text-[var(--danger)]">{err || "Report not found"}</p>
        <Link to="/reports" className="btn-ghost text-xs mt-6 inline-block">Browse all reports</Link>
      </div>
    );
  }

  const startedAt = new Date(data.started_at);
  const publishedAt = new Date(data.published_at);

  return (
    <div className="max-w-5xl mx-auto px-6 md:px-12 py-12" data-testid="public-live-report">
      <Link to="/reports" className="text-xs font-mono text-white/50 hover:text-[var(--neon)] mb-6 inline-block">&lt; all reports</Link>

      <div className="flex items-center gap-2 mb-3">
        <span className="px-2 py-1 border border-[var(--neon)]/40 text-[var(--neon)] text-[10px] uppercase tracking-widest font-mono flex items-center gap-1">
          <Radio className="w-3 h-3" /> live capture
        </span>
        <span className="text-[10px] uppercase tracking-widest text-white/40 font-mono">
          published {publishedAt.toLocaleDateString()}
        </span>
      </div>

      <h1 className="font-heading text-3xl md:text-5xl tracking-tighter mb-3 leading-tight" data-testid="public-live-headline">
        {data.headline}
      </h1>
      <p className="text-sm text-white/60 font-mono mb-8">
        <Clock className="w-3 h-3 inline mr-1" />
        Recorded {startedAt.toLocaleString()} · {data.frame_count} forensic frame{data.frame_count === 1 ? "" : "s"} analyzed by Gemini 3 Flash.
      </p>

      {/* Techniques summary */}
      <div className="panel p-5 mb-6" data-testid="public-live-techniques">
        <h2 className="text-xs uppercase tracking-widest font-heading mb-3 text-white/70 flex items-center gap-2">
          <AlertTriangle className="w-3 h-3 text-[var(--danger)]" /> Manipulation patterns observed
        </h2>
        <div className="flex flex-wrap gap-2">
          {data.techniques_aggregated.map((t, i) => (
            <span key={i} className="text-xs font-mono px-2 py-1 border border-[var(--danger)]/50 text-[var(--danger)]">
              {t}
            </span>
          ))}
        </div>
      </div>

      {/* AI summary */}
      {data.summary && (
        <div className="panel p-6 mb-6" data-testid="public-live-summary">
          <h2 className="text-xs uppercase tracking-widest font-heading mb-3 text-white/70">Editorial summary</h2>
          {data.summary.split("\n").filter(Boolean).map((p, i) => (
            <p key={i} className="text-sm text-white/80 font-mono leading-relaxed mb-3 last:mb-0">{p}</p>
          ))}
        </div>
      )}

      {/* Frame timeline */}
      <h2 className="text-xs uppercase tracking-widest font-heading mb-3 text-white/70">Frame-by-frame evidence</h2>
      <ol className="relative border-l border-white/10 ml-2 space-y-4 mb-12" data-testid="public-live-timeline">
        {data.frames.map((f) => (
          <li key={f.idx} className="ml-4 panel p-4">
            <span className="absolute -left-[5px] mt-1 w-2 h-2 rounded-full bg-[var(--neon)] shadow-[0_0_8px_var(--neon)]" />
            <div className="flex items-center justify-between mb-1">
              <span className="text-[10px] uppercase tracking-widest font-mono text-white/40">
                frame #{f.idx + 1} · t = {f.elapsed_seconds}s
              </span>
              {f.techniques_detected.length > 0 ? (
                <span className="text-[10px] font-mono text-[var(--danger)] flex items-center gap-1">
                  <AlertTriangle className="w-3 h-3" /> flagged
                </span>
              ) : (
                <span className="text-[10px] font-mono text-white/40">clean</span>
              )}
            </div>
            {f.techniques_detected.length > 0 && (
              <div className="flex flex-wrap gap-1 mb-2">
                {f.techniques_detected.map((t, i) => (
                  <span key={i} className="text-[10px] font-mono px-1.5 py-0.5 border border-[var(--neon)]/40 text-[var(--neon)]">
                    {t}
                  </span>
                ))}
              </div>
            )}
            <p className="text-xs font-mono text-white/70 leading-relaxed">{f.note}</p>
          </li>
        ))}
      </ol>

      {/* Operator response (right-of-response approved) */}
      {disputes.length > 0 && (
        <div className="panel p-6 mb-6 border border-yellow-400/30 bg-yellow-400/[0.02]" data-testid="public-live-disputes">
          <h2 className="text-xs uppercase tracking-widest font-heading mb-3 text-yellow-400 flex items-center gap-2">
            <MessageSquare className="w-3 h-3" /> Operator response{disputes.length > 1 ? "s" : ""}
          </h2>
          {disputes.map((d, i) => (
            <div key={i} className="mb-4 last:mb-0">
              <p className="text-xs font-mono text-white/50 mb-2">
                <strong className="text-white/80">{d.casino_name}</strong>
                {d.contact_name && <> · {d.contact_name}</>}
                {d.role && <> ({d.role})</>}
                <span className="text-white/30"> · published {new Date(d.approved_at).toLocaleDateString()}</span>
              </p>
              <p className="text-sm font-mono text-white/80 leading-relaxed whitespace-pre-line border-l-2 border-yellow-400/50 pl-3">
                {d.response_text}
              </p>
            </div>
          ))}
        </div>
      )}

      {/* Share + CTA */}
      <div className="panel p-6 text-center">
        <ShieldCheck className="w-8 h-8 text-[var(--neon)] mx-auto mb-3" />
        <p className="text-sm text-white/80 font-mono mb-1">Seen these patterns before?</p>
        <p className="text-xs text-white/50 font-mono mb-4">
          Casino Spotter helps you spot manipulation as it happens. Scan your own clips or run live captures.
        </p>
        <div className="flex flex-wrap gap-3 justify-center">
          <Link to="/signup" className="btn-neon text-xs">START YOUR FIRST SCAN &gt;_</Link>
          <Link to="/techniques" className="btn-ghost text-xs">Learn the techniques</Link>
          <button
            onClick={() => {
              navigator.clipboard.writeText(window.location.href);
            }}
            className="btn-ghost text-xs flex items-center gap-1"
            data-testid="public-live-copy-url"
          >
            <Share2 className="w-3 h-3" /> Copy link
          </button>
        </div>
      </div>

      <LegalDisclaimer slug={slug} type="live" />
    </div>
  );
}
