import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { api } from "../lib/api";
import { Radio, ArrowLeft, AlertTriangle, Clock, Loader2 } from "lucide-react";

export default function LiveSessionDetail() {
  const { id } = useParams();
  const [session, setSession] = useState(null);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState("");

  useEffect(() => {
    api.get(`/live/session/${id}`)
      .then((r) => setSession(r.data))
      .catch((e) => setErr(e?.response?.data?.detail || "Session not found"))
      .finally(() => setLoading(false));
  }, [id]);

  if (loading) {
    return (
      <div className="max-w-5xl mx-auto px-6 py-20 text-center">
        <Loader2 className="w-6 h-6 animate-spin text-[var(--neon)] mx-auto" />
        <p className="text-xs font-mono text-white/50 mt-3">Loading session…</p>
      </div>
    );
  }

  if (err || !session) {
    return (
      <div className="max-w-3xl mx-auto px-6 py-20">
        <p className="text-sm font-mono text-[var(--danger)]">{err || "Session not found"}</p>
        <Link to="/dashboard" className="btn-ghost text-xs mt-6 inline-flex items-center gap-2">
          <ArrowLeft className="w-3 h-3" /> Back to dashboard
        </Link>
      </div>
    );
  }

  const startedAt = new Date(session.started_at);
  const endedAt = session.ended_at ? new Date(session.ended_at) : null;
  const durationSec = endedAt
    ? Math.max(0, Math.round((endedAt - startedAt) / 1000))
    : null;

  return (
    <div className="max-w-5xl mx-auto px-6 md:px-12 py-12" data-testid="live-session-detail">
      <Link
        to="/dashboard"
        className="text-xs font-mono text-white/50 hover:text-[var(--neon)] inline-flex items-center gap-1 mb-6"
        data-testid="live-detail-back"
      >
        <ArrowLeft className="w-3 h-3" /> back to dashboard
      </Link>

      <p className="text-xs uppercase tracking-[0.3em] text-[var(--neon)] mb-2">// live session</p>
      <h1 className="font-heading text-3xl md:text-4xl tracking-tighter mb-2">
        {session.game_type}{session.casino_name ? ` — ${session.casino_name}` : ""}
      </h1>
      <div className="flex flex-wrap gap-4 text-xs font-mono text-white/60 mb-8">
        <span><Clock className="w-3 h-3 inline mr-1" />{startedAt.toLocaleString()}</span>
        <span>frames: <span className="text-white">{session.frame_count}</span></span>
        {durationSec !== null && (
          <span>duration: <span className="text-white">{durationSec}s</span> / cap {session.max_seconds}s</span>
        )}
        {session.is_trial && (
          <span className="px-1.5 py-0.5 border border-[var(--neon)]/40 text-[var(--neon)] text-[10px] uppercase tracking-widest">trial</span>
        )}
      </div>

      {/* Techniques summary */}
      <div className="panel p-5 mb-6" data-testid="live-detail-techniques">
        <h2 className="text-xs uppercase tracking-widest font-heading mb-3 text-white/70">Techniques flagged</h2>
        {session.techniques_aggregated.length === 0 ? (
          <p className="text-xs font-mono text-white/40">No manipulation techniques detected during this session.</p>
        ) : (
          <div className="flex flex-wrap gap-2">
            {session.techniques_aggregated.map((t, i) => (
              <span key={i} className="text-xs font-mono px-2 py-1 border border-[var(--danger)]/50 text-[var(--danger)]">
                {t}
              </span>
            ))}
          </div>
        )}
      </div>

      {/* AI summary */}
      {session.summary && (
        <div className="panel p-6 mb-6" data-testid="live-detail-summary">
          <h2 className="text-xs uppercase tracking-widest font-heading mb-3 text-white/70">AI editorial summary</h2>
          {session.summary.split("\n").filter(Boolean).map((p, i) => (
            <p key={i} className="text-sm text-white/80 font-mono leading-relaxed mb-3 last:mb-0">{p}</p>
          ))}
        </div>
      )}

      {/* Frame-by-frame timeline */}
      <h2 className="text-xs uppercase tracking-widest font-heading mb-3 text-white/70">Frame timeline</h2>
      {session.frames.length === 0 ? (
        <div className="panel p-4 text-xs font-mono text-white/40">No frames were analyzed before the session ended.</div>
      ) : (
        <ol className="relative border-l border-white/10 ml-2 space-y-4" data-testid="live-detail-timeline">
          {session.frames.map((f) => (
            <li key={f.idx} className="ml-4 panel p-4" data-testid={`live-detail-frame-${f.idx}`}>
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
      )}

      <div className="mt-10 flex gap-3">
        <Link to="/live" className="btn-neon text-xs inline-flex items-center gap-2" data-testid="live-detail-new-session">
          <Radio className="w-3 h-3" /> RUN A NEW SESSION &gt;_
        </Link>
        <Link to="/dashboard" className="btn-ghost text-xs">Back to dashboard</Link>
      </div>
    </div>
  );
}
