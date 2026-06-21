import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../lib/api";
import { useAuth } from "../context/AuthContext";
import { toast } from "sonner";
import {
  Radio, Square, Sparkles, Lock, Info, AlertTriangle, Loader2, ScanLine, Clock
} from "lucide-react";

const GAME_TYPES = ["Slots", "Roulette", "Blackjack", "Poker", "Live Dealer", "Crash/Aviator", "Other"];

export default function Live() {
  const { user } = useAuth();
  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const streamRef = useRef(null);
  const captureTimerRef = useRef(null);
  const countdownRef = useRef(null);

  const [gameType, setGameType] = useState("Slots");
  const [casinoName, setCasinoName] = useState("");
  const [session, setSession] = useState(null);     // {session_id, cadence_seconds, max_seconds, is_trial}
  const [streaming, setStreaming] = useState(false);
  const [elapsed, setElapsed] = useState(0);
  const [busy, setBusy] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [feed, setFeed] = useState([]);             // [{idx, elapsed, techniques, note}]
  const [finalReport, setFinalReport] = useState(null);

  const isPremium = !!user?.is_premium;
  const isAdmin = !!user?.is_admin;
  const isUnlimited = isPremium || isAdmin;
  const trialUsed = !!user?.live_trial_used;
  const blockedNoTrial = !isUnlimited && trialUsed;

  // Cleanup on unmount
  useEffect(() => {
    return () => stopEverything();
  }, []);

  function stopEverything() {
    if (captureTimerRef.current) { clearTimeout(captureTimerRef.current); captureTimerRef.current = null; }
    if (countdownRef.current) { clearInterval(countdownRef.current); countdownRef.current = null; }
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((t) => t.stop());
      streamRef.current = null;
    }
    if (videoRef.current) videoRef.current.srcObject = null;
  }

  async function startCapture() {
    if (blockedNoTrial) {
      toast.error("Your free 60s trial is used. Upgrade to Premium for unlimited 3-min sessions.");
      return;
    }
    if (!navigator.mediaDevices?.getDisplayMedia) {
      toast.error("Your browser doesn't support screen capture. Try Chrome, Edge, or Firefox on desktop.");
      return;
    }
    setBusy(true);
    setFinalReport(null);
    setFeed([]);
    setElapsed(0);
    try {
      const stream = await navigator.mediaDevices.getDisplayMedia({
        video: { frameRate: 5 },
        audio: false,
      });
      streamRef.current = stream;
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        await videoRef.current.play().catch(() => {});
      }

      // Stop session when the user revokes the share via browser UI
      stream.getVideoTracks()[0].addEventListener("ended", () => {
        endSession("Screen share ended.");
      });

      const { data } = await api.post("/live/session/start", {
        game_type: gameType,
        casino_name: casinoName.trim(),
      });
      setSession(data);
      setStreaming(true);

      // Kick off elapsed counter
      const startedAt = Date.now();
      countdownRef.current = setInterval(() => {
        const e = Math.floor((Date.now() - startedAt) / 1000);
        setElapsed(e);
        if (e >= data.max_seconds) {
          endSession("Time limit reached.");
        }
      }, 1000);

      // First analysis after a tiny warm-up, then on cadence
      captureTimerRef.current = setTimeout(
        () => analyzeFrame(data.session_id, Math.floor((Date.now() - startedAt) / 1000), startedAt, data),
        1500
      );

    } catch (err) {
      if (err?.response?.status === 402) {
        toast.error(err.response.data.detail || "Upgrade required");
      } else if (err?.name === "NotAllowedError") {
        toast.error("Screen share permission denied.");
      } else {
        toast.error(err?.response?.data?.detail || err?.message || "Could not start capture");
      }
      stopEverything();
      setStreaming(false);
    } finally {
      setBusy(false);
    }
  }

  async function analyzeFrame(sessionId, elapsedSec, startedAt, sessConfig) {
    if (!streamRef.current || !videoRef.current || !canvasRef.current) return;
    const video = videoRef.current;
    const canvas = canvasRef.current;
    if (!video.videoWidth) {
      // Video not ready yet, retry quickly
      captureTimerRef.current = setTimeout(
        () => analyzeFrame(sessionId, Math.floor((Date.now() - startedAt) / 1000), startedAt, sessConfig),
        1000
      );
      return;
    }
    // Downscale to 1280px max width for upload efficiency
    const maxW = 1280;
    const scale = Math.min(1, maxW / video.videoWidth);
    canvas.width = Math.round(video.videoWidth * scale);
    canvas.height = Math.round(video.videoHeight * scale);
    const ctx = canvas.getContext("2d");
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
    const dataUrl = canvas.toDataURL("image/jpeg", 0.7);

    setAnalyzing(true);
    try {
      const { data } = await api.post("/live/frame", {
        session_id: sessionId,
        frame_data_url: dataUrl,
        elapsed_seconds: elapsedSec,
      }, { timeout: 60000 });

      setFeed((prev) => [
        ...prev,
        {
          idx: data.frame_idx,
          elapsed: elapsedSec,
          techniques: data.techniques_detected || [],
          note: data.note || "",
          ts: new Date().toISOString(),
        },
      ]);

      if (data.should_continue && streamRef.current) {
        captureTimerRef.current = setTimeout(
          () => analyzeFrame(sessionId, Math.floor((Date.now() - startedAt) / 1000), startedAt, sessConfig),
          (sessConfig?.cadence_seconds || 15) * 1000
        );
      } else if (!data.should_continue) {
        endSession("Time limit reached.");
      }
    } catch (err) {
      console.error("Frame analyze failed", err);
      // Don't abort the whole session for one failed frame — schedule the next
      if (streamRef.current) {
        captureTimerRef.current = setTimeout(
          () => analyzeFrame(sessionId, Math.floor((Date.now() - startedAt) / 1000), startedAt, sessConfig),
          (sessConfig?.cadence_seconds || 15) * 1000
        );
      }
    } finally {
      setAnalyzing(false);
    }
  }

  async function endSession(reason) {
    if (!session) return;
    const sid = session.session_id;
    if (countdownRef.current) { clearInterval(countdownRef.current); countdownRef.current = null; }
    if (captureTimerRef.current) { clearTimeout(captureTimerRef.current); captureTimerRef.current = null; }
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((t) => t.stop());
      streamRef.current = null;
    }
    if (videoRef.current) videoRef.current.srcObject = null;

    setStreaming(false);
    if (reason) toast.info(reason);

    try {
      const { data } = await api.post("/live/session/end", { session_id: sid }, { timeout: 60000 });
      setFinalReport(data);
      toast.success("Session report ready.");
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Could not finalize session");
    } finally {
      setSession(null);
    }
  }

  const maxSec = session?.max_seconds || (isUnlimited ? 180 : 60);
  const progressPct = Math.min(100, Math.round((elapsed / maxSec) * 100));
  const remaining = Math.max(0, maxSec - elapsed);

  return (
    <div className="max-w-6xl mx-auto px-6 md:px-12 py-12">
      <p className="text-xs uppercase tracking-[0.3em] text-[var(--neon)] mb-2">// real-time forensic mode</p>
      <h1 className="font-heading text-4xl md:text-5xl tracking-tighter mb-2">LIVE CAPTURE</h1>
      <p className="text-sm text-white/60 font-mono mb-8">
        &gt; Share your screen or game tab. Gemini 3 Flash analyzes a frame every 15 seconds.
      </p>

      {/* Cost / scope notice */}
      <div className="panel p-4 mb-6 border border-[var(--neon)]/30 bg-black/60 flex gap-3" data-testid="live-cost-notice">
        <Info className="w-4 h-4 text-[var(--neon)] mt-0.5 shrink-0" />
        <div className="text-xs font-mono text-white/70 leading-relaxed">
          To keep forensic scans free for the community, each live session is capped at <span className="text-[var(--neon)]">3 minutes</span> (60s on the free trial).
          <br />
          <span className="text-white/50">Tip: cue up the slot spin, bonus round, or withdrawal flow you&apos;re suspicious of — then start capture.</span>
        </div>
      </div>

      {/* Trial / Premium gating banner */}
      {!isUnlimited && (
        <div className="panel p-4 mb-6 flex items-start justify-between gap-4" data-testid="live-trial-banner">
          <div className="flex items-start gap-3">
            <Sparkles className="w-4 h-4 text-[var(--neon)] mt-0.5 shrink-0" />
            <div className="text-xs font-mono text-white/70 leading-relaxed">
              {trialUsed ? (
                <>
                  Your free <span className="text-[var(--neon)]">60-second live trial</span> has been used.
                  Upgrade to Premium for unlimited 3-min sessions.
                </>
              ) : (
                <>
                  You have <span className="text-[var(--neon)]">one free 60-second live trial</span> on this account. Premium ($9.99/mo) unlocks unlimited 3-min sessions.
                </>
              )}
            </div>
          </div>
          <Link to="/pricing" className="btn-neon text-xs whitespace-nowrap" data-testid="live-upsell-btn">
            Go Premium &gt;_
          </Link>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
        {/* Left: capture area */}
        <div className="lg:col-span-3 panel p-5 space-y-4">
          <div className="flex items-center gap-2">
            <span className={`w-2 h-2 rounded-full ${streaming ? "bg-[var(--neon)] animate-pulse" : "bg-white/30"}`} />
            <span className="text-xs uppercase tracking-widest font-heading">
              {streaming ? "CAPTURING" : "IDLE"}
            </span>
            {streaming && (
              <span className="ml-auto text-xs font-mono text-white/60 flex items-center gap-1" data-testid="live-elapsed">
                <Clock className="w-3 h-3" />
                {String(Math.floor(elapsed / 60)).padStart(1, "0")}:{String(elapsed % 60).padStart(2, "0")} / {String(Math.floor(maxSec / 60)).padStart(1, "0")}:{String(maxSec % 60).padStart(2, "0")}
              </span>
            )}
          </div>

          <div className="relative rounded border border-white/10 overflow-hidden bg-black/80 aspect-video">
            <video
              ref={videoRef}
              autoPlay
              playsInline
              muted
              className="w-full h-full object-contain"
              data-testid="live-video"
            />
            {!streaming && (
              <div className="absolute inset-0 flex flex-col items-center justify-center text-center p-6">
                <ScanLine className="w-10 h-10 text-[var(--neon)] mb-3" />
                <p className="text-sm text-white/70 font-mono">Screen share inactive</p>
                <p className="text-xs text-white/40 font-mono mt-1">Choose a game window or browser tab when prompted.</p>
              </div>
            )}
            {analyzing && (
              <div className="absolute top-2 right-2 bg-black/70 border border-[var(--neon)]/40 px-2 py-1 text-[10px] font-mono text-[var(--neon)] flex items-center gap-1" data-testid="live-analyzing-pill">
                <Loader2 className="w-3 h-3 animate-spin" /> analyzing frame...
              </div>
            )}
            <canvas ref={canvasRef} className="hidden" />
          </div>

          {streaming && (
            <div>
              <div className="h-1 bg-white/10 rounded overflow-hidden">
                <div
                  className="h-full bg-[var(--neon)] transition-all"
                  style={{ width: `${progressPct}%` }}
                  data-testid="live-progress"
                />
              </div>
              <p className="text-[10px] font-mono text-white/40 mt-1">{remaining}s remaining</p>
            </div>
          )}

          {!streaming && !finalReport && (
            <div className="space-y-3" data-testid="live-setup">
              <label className="block">
                <span className="block text-xs uppercase tracking-widest text-white/60 mb-1 font-heading">GAME TYPE</span>
                <select
                  data-testid="live-game-type"
                  value={gameType}
                  onChange={(e) => setGameType(e.target.value)}
                  className="input-neon"
                >
                  {GAME_TYPES.map((g) => <option key={g} value={g}>{g}</option>)}
                </select>
              </label>
              <label className="block">
                <span className="block text-xs uppercase tracking-widest text-white/60 mb-1 font-heading">CASINO NAME (OPTIONAL)</span>
                <input
                  data-testid="live-casino-name"
                  value={casinoName}
                  onChange={(e) => setCasinoName(e.target.value)}
                  placeholder="e.g. Lucky Spin Casino"
                  className="input-neon"
                />
              </label>
              <button
                onClick={startCapture}
                disabled={busy || blockedNoTrial}
                className="btn-neon w-full flex items-center justify-center gap-2"
                data-testid="live-start-btn"
              >
                {busy ? <Loader2 className="w-4 h-4 animate-spin" /> : <Radio className="w-4 h-4" />}
                {blockedNoTrial ? "TRIAL USED — UPGRADE TO RESUME" : busy ? "REQUESTING SHARE..." : "START LIVE CAPTURE >_"}
              </button>
              {blockedNoTrial && (
                <div className="flex items-center gap-1 text-[10px] font-mono text-white/40">
                  <Lock className="w-3 h-3" /> Premium required for additional sessions.
                </div>
              )}
            </div>
          )}

          {streaming && (
            <button
              onClick={() => endSession("Stopped by user.")}
              className="btn-ghost w-full flex items-center justify-center gap-2 text-xs"
              data-testid="live-stop-btn"
            >
              <Square className="w-3 h-3" /> STOP & GENERATE REPORT
            </button>
          )}
        </div>

        {/* Right: live feed */}
        <div className="lg:col-span-2 panel p-5">
          <div className="flex items-center justify-between mb-3">
            <h2 className="font-heading text-sm uppercase tracking-widest">Live Findings</h2>
            <span className="text-[10px] font-mono text-white/40">{feed.length} frame{feed.length === 1 ? "" : "s"}</span>
          </div>

          {feed.length === 0 && !streaming && (
            <p className="text-xs font-mono text-white/40">No frames analyzed yet. Start a capture to populate this feed.</p>
          )}

          {feed.length === 0 && streaming && (
            <p className="text-xs font-mono text-white/50 flex items-center gap-2">
              <Loader2 className="w-3 h-3 animate-spin text-[var(--neon)]" /> Waiting for first frame analysis…
            </p>
          )}

          <ul className="space-y-3 max-h-[500px] overflow-y-auto pr-1" data-testid="live-feed">
            {[...feed].reverse().map((f) => (
              <li key={f.idx} className="border border-white/10 rounded p-3 bg-black/40" data-testid={`live-feed-item-${f.idx}`}>
                <div className="flex items-center justify-between mb-1">
                  <span className="text-[10px] uppercase tracking-widest font-mono text-white/40">t = {f.elapsed}s</span>
                  {f.techniques.length > 0 ? (
                    <span className="text-[10px] font-mono text-[var(--danger)] flex items-center gap-1">
                      <AlertTriangle className="w-3 h-3" /> flagged
                    </span>
                  ) : (
                    <span className="text-[10px] font-mono text-white/40">clean</span>
                  )}
                </div>
                {f.techniques.length > 0 && (
                  <div className="flex flex-wrap gap-1 mb-1">
                    {f.techniques.map((t, i) => (
                      <span key={i} className="text-[10px] font-mono px-1.5 py-0.5 border border-[var(--neon)]/40 text-[var(--neon)]">
                        {t}
                      </span>
                    ))}
                  </div>
                )}
                <p className="text-xs font-mono text-white/70 leading-relaxed">{f.note}</p>
              </li>
            ))}
          </ul>
        </div>
      </div>

      {/* Final report */}
      {finalReport && (
        <div className="panel p-6 mt-8" data-testid="live-report">
          <p className="text-xs uppercase tracking-[0.3em] text-[var(--neon)] mb-1">// session report</p>
          <h2 className="font-heading text-2xl mb-3">
            {finalReport.game_type} session{finalReport.casino_name ? ` — ${finalReport.casino_name}` : ""}
          </h2>
          <div className="flex flex-wrap gap-4 text-xs font-mono text-white/60 mb-4">
            <span>frames: <span className="text-white">{finalReport.frame_count}</span></span>
            <span>duration: <span className="text-white">{finalReport.max_seconds}s cap</span></span>
            <span>techniques flagged: <span className="text-[var(--danger)]">{finalReport.techniques_aggregated.length}</span></span>
          </div>

          {finalReport.techniques_aggregated.length > 0 && (
            <div className="flex flex-wrap gap-2 mb-4" data-testid="live-report-techniques">
              {finalReport.techniques_aggregated.map((t, i) => (
                <span key={i} className="text-xs font-mono px-2 py-1 border border-[var(--danger)]/50 text-[var(--danger)]">
                  {t}
                </span>
              ))}
            </div>
          )}

          {finalReport.summary && (
            <div className="prose-neon" data-testid="live-report-summary">
              {finalReport.summary.split("\n").filter(Boolean).map((p, i) => (
                <p key={i} className="text-sm text-white/80 font-mono leading-relaxed mb-3">{p}</p>
              ))}
            </div>
          )}

          <div className="flex gap-3 mt-6 flex-wrap">
            <Link to="/dashboard" className="btn-ghost text-xs" data-testid="live-report-dashboard">&lt; Back to dashboard</Link>
            <Link
              to={`/live/sessions/${finalReport.id}`}
              className="btn-ghost text-xs"
              data-testid="live-report-detail"
            >
              View full timeline
            </Link>
            <button onClick={() => { setFinalReport(null); setFeed([]); }} className="btn-neon text-xs" data-testid="live-report-new">
              RUN ANOTHER &gt;_
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
