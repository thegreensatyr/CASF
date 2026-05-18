import { useState } from "react";
import { api } from "../lib/api";
import { toast } from "sonner";
import { Upload, FileVideo, FileImage, Loader2 } from "lucide-react";

export default function Analyze() {
  const [file, setFile] = useState(null);
  const [gameType, setGameType] = useState("Slots");
  const [casinoName, setCasinoName] = useState("");
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState(null);

  const onSubmit = async (e) => {
    e.preventDefault();
    if (!file) return toast.error("Upload a video or screenshot first");
    setBusy(true); setResult(null);
    const fd = new FormData();
    fd.append("file", file);
    fd.append("game_type", gameType);
    fd.append("casino_name", casinoName);
    try {
      const { data } = await api.post("/analysis/upload", fd, {
        headers: { "Content-Type": "multipart/form-data" },
        timeout: 180000,
      });
      setResult(data);
      toast.success("Analysis complete");
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Analysis failed");
    } finally { setBusy(false); }
  };

  return (
    <div className="max-w-6xl mx-auto px-6 md:px-12 py-12">
      <p className="text-xs uppercase tracking-[0.3em] text-[var(--neon)] mb-2">// forensic upload</p>
      <h1 className="font-heading text-4xl md:text-5xl tracking-tighter mb-2">RUN A SCAN</h1>
      <p className="text-sm text-white/60 font-mono mb-10">&gt; Submit a clip or screenshot. Gemini 3 Flash will deconstruct every frame.</p>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <form onSubmit={onSubmit} className="panel p-6 space-y-5" data-testid="analyze-form">
          <label className="block">
            <span className="block text-xs uppercase tracking-widest text-white/60 mb-1 font-heading">GAME TYPE</span>
            <select
              data-testid="game-type-select"
              value={gameType}
              onChange={(e) => setGameType(e.target.value)}
              className="input-neon"
            >
              {["Slots","Roulette","Blackjack","Baccarat","Live Dealer","Crash / Aviator","Plinko","Sports Bet","Other"].map(g => (
                <option key={g} value={g} className="bg-black">{g}</option>
              ))}
            </select>
          </label>

          <label className="block">
            <span className="block text-xs uppercase tracking-widest text-white/60 mb-1 font-heading">CASINO (optional)</span>
            <input
              data-testid="casino-name-input"
              value={casinoName}
              onChange={(e) => setCasinoName(e.target.value)}
              placeholder="e.g. SuperStarz Casino"
              className="input-neon"
            />
          </label>

          <label className="block">
            <span className="block text-xs uppercase tracking-widest text-white/60 mb-1 font-heading">EVIDENCE FILE</span>
            <div className="border border-dashed border-[var(--neon-dim)] p-6 text-center rounded-sm hover:bg-[var(--neon-glow)] transition cursor-pointer">
              <input
                data-testid="file-input"
                type="file"
                accept="video/*,image/*"
                onChange={(e) => setFile(e.target.files?.[0])}
                className="hidden"
                id="file-up"
              />
              <label htmlFor="file-up" className="cursor-pointer block">
                <Upload className="w-6 h-6 mx-auto text-[var(--neon)] mb-2" />
                <span className="text-xs uppercase tracking-widest text-white/70">
                  {file ? file.name : "Drop video or screenshot here"}
                </span>
              </label>
            </div>
            {file && (
              <div className="mt-2 text-[10px] text-white/50 font-mono flex items-center gap-2">
                {file.type.startsWith("video") ? <FileVideo className="w-3 h-3" /> : <FileImage className="w-3 h-3" />}
                {(file.size / (1024*1024)).toFixed(2)} MB
              </div>
            )}
          </label>

          <button className="btn-neon w-full" disabled={busy} data-testid="analyze-submit">
            {busy ? (<span className="flex items-center justify-center gap-2"><Loader2 className="w-4 h-4 animate-spin"/>SCANNING...</span>) : "INITIATE SCAN >_"}
          </button>
        </form>

        <div className="panel p-6 scanlines min-h-[420px]" data-testid="analyze-output">
          {busy && (
            <div className="text-[var(--neon)] font-mono text-xs space-y-1">
              <div>&gt; uploading evidence...</div>
              <div>&gt; routing to gemini-3-flash multimodal...</div>
              <div>&gt; scrubbing frames for near-miss patterns</div>
              <div>&gt; cross-checking psychology heuristics</div>
              <div className="caret">&gt; awaiting verdict</div>
            </div>
          )}
          {!busy && !result && (
            <div className="text-xs text-white/40 font-mono">&gt; output will appear here</div>
          )}
          {result && (
            <div>
              <div className="flex items-center gap-2 mb-3">
                <span className="dot-pulse w-2 h-2 rounded-full bg-[var(--neon)]" />
                <span className="text-xs uppercase tracking-[0.3em] text-[var(--neon)]">analysis complete</span>
              </div>
              {result.techniques_detected?.length > 0 && (
                <div className="flex flex-wrap gap-2 mb-4">
                  {result.techniques_detected.map((t, i) => (
                    <span key={i} className="tag">{t}</span>
                  ))}
                </div>
              )}
              <pre className="whitespace-pre-wrap text-xs font-mono text-white/85 leading-relaxed" data-testid="analysis-text">
                {result.analysis}
              </pre>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
