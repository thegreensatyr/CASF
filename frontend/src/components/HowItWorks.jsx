import { useEffect, useState } from "react";
import { Upload, Cpu, ShieldCheck } from "lucide-react";

const DEMO_LINES = [
  "> connecting forensic feed...",
  "> ingesting evidence: roulette_session_4f2.mp4",
  "> routing to gemini-3-flash multimodal...",
  "> scrubbing 1,847 frames",
  "",
  "VERDICT: Casino is using engineered near-miss",
  "         outcomes and a delayed-reveal animation",
  "         to create false-hope euphoria.",
  "",
  "TECHNIQUES_DETECTED: near-miss, slow-reveal,",
  "                    losses-disguised-as-wins",
  "",
  "DETAILED_ANALYSIS: Across the captured spins,",
  "the wheel pauses for 1.4s on the slot adjacent",
  "to the player's bet 3 out of 5 times — a rate",
  "that is statistically impossible on a fair",
  "European roulette wheel (expected: 1 in 18).",
  "",
  "PROTECT_YOURSELF:",
  " • Stop playing this operator. Cash out now.",
  " • Verify the RNG audit certificate.",
  " • Switch to a UKGC or MGA-licensed casino.",
  "",
  "[ analysis complete · 4.2s · 1 credit used ]",
];

export default function HowItWorks() {
  return (
    <section className="border-t border-white/10 bg-black">
      <div className="max-w-7xl mx-auto px-6 md:px-12 py-24">
        <div className="flex items-end justify-between flex-wrap gap-4 mb-12">
          <div>
            <p className="text-xs uppercase tracking-[0.3em] text-[var(--neon)] mb-2">// how it works</p>
            <h2 className="font-heading text-3xl md:text-5xl tracking-tighter">
              THREE STEPS. <span className="neon-text">ZERO LIES.</span>
            </h2>
          </div>
          <span className="hidden md:inline text-xs text-white/40 font-mono">avg scan: 4 seconds</span>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 items-start">
          {/* Left: 3 steps */}
          <div className="space-y-4">
            <Step
              n="01"
              Icon={Upload}
              title="DROP YOUR EVIDENCE"
              body="Upload a short clip or screenshot of any casino game session. Roulette, slots, blackjack, crash games — anything visual we can analyze. Or paste a casino name for an instant trust report."
            />
            <Step
              n="02"
              Icon={Cpu}
              title="AI DECODES THE TRICK"
              body="Gemini 3 Flash multimodal scrubs every frame. Claude Sonnet 4.5 cross-references known operator patterns. The AI doesn't just label patterns — it explains exactly which technique is being used and why your brain is being targeted."
            />
            <Step
              n="03"
              Icon={ShieldCheck}
              title="GET THE TRUTH (& AN ALTERNATIVE)"
              body="Plain-English verdict, severity rating, and concrete protect-yourself steps. If the casino is rigged, you get 3 licensed alternatives audited by UKGC / MGA / state regulators."
            />
          </div>

          {/* Right: live demo terminal */}
          <div className="panel scanlines p-0 overflow-hidden">
            <TerminalHeader />
            <div className="p-5 md:p-6 font-mono text-[11px] leading-relaxed bg-[#050505] min-h-[420px] max-h-[520px] overflow-hidden">
              <Typewriter lines={DEMO_LINES} />
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

function Step({ n, Icon, title, body }) {
  return (
    <div className="panel p-6 group hover:border-[var(--neon)] transition">
      <div className="flex items-start gap-4">
        <div className="font-heading text-3xl text-[var(--neon)] min-w-[3rem]">{n}</div>
        <div className="flex-1">
          <div className="flex items-center gap-2 mb-2">
            <Icon className="w-4 h-4 text-[var(--neon)]" />
            <h3 className="font-heading text-lg tracking-tight">{title}</h3>
          </div>
          <p className="text-sm font-mono text-white/70 leading-relaxed">{body}</p>
        </div>
      </div>
    </div>
  );
}

function TerminalHeader() {
  return (
    <div className="flex items-center justify-between px-4 py-2 border-b border-[var(--border)] bg-[#0a0a0a]">
      <div className="flex items-center gap-1.5">
        <span className="w-2.5 h-2.5 rounded-full bg-[#ff5f57]" />
        <span className="w-2.5 h-2.5 rounded-full bg-[#ffbd2e]" />
        <span className="w-2.5 h-2.5 rounded-full bg-[#28c940]" />
      </div>
      <span className="text-[10px] uppercase tracking-widest text-white/50 font-mono">/forensic/live-demo</span>
      <span className="flex items-center gap-1 text-[10px] text-[var(--neon)] font-mono">
        <span className="dot-pulse w-1.5 h-1.5 rounded-full bg-[var(--neon)]" />
        LIVE
      </span>
    </div>
  );
}

function Typewriter({ lines }) {
  const [lineIdx, setLineIdx] = useState(0);
  const [charIdx, setCharIdx] = useState(0);
  const [done, setDone] = useState(false);

  useEffect(() => {
    if (lineIdx >= lines.length) {
      // restart loop after 4s
      const t = setTimeout(() => { setLineIdx(0); setCharIdx(0); setDone(false); }, 4000);
      return () => clearTimeout(t);
    }
    const currentLine = lines[lineIdx];
    if (charIdx < currentLine.length) {
      const speed = currentLine.startsWith(">") || currentLine === "" ? 8 : 14;
      const t = setTimeout(() => setCharIdx((c) => c + 1), speed);
      return () => clearTimeout(t);
    }
    // line complete — pause briefly then advance
    const pause = currentLine === "" ? 80 : currentLine.startsWith("[") ? 800 : 180;
    const t = setTimeout(() => {
      setLineIdx((i) => i + 1);
      setCharIdx(0);
      if (lineIdx === lines.length - 1) setDone(true);
    }, pause);
    return () => clearTimeout(t);
  }, [lineIdx, charIdx, lines]);

  return (
    <div className="whitespace-pre-wrap">
      {lines.slice(0, lineIdx).map((l, i) => (
        <div key={i} className={getLineColor(l)}>{l || "\u00A0"}</div>
      ))}
      {lineIdx < lines.length && (
        <div className={getLineColor(lines[lineIdx])}>
          {lines[lineIdx].slice(0, charIdx)}
          <span className="caret-inline">_</span>
        </div>
      )}
    </div>
  );
}

function getLineColor(line) {
  if (!line) return "";
  if (line.startsWith("VERDICT:")) return "text-[var(--neon)] font-bold";
  if (line.startsWith("TECHNIQUES_DETECTED:") || line.startsWith("PROTECT_YOURSELF:")) return "text-[var(--neon)]";
  if (line.startsWith("DETAILED_ANALYSIS:")) return "text-[var(--neon)]";
  if (line.startsWith(">")) return "text-white/50";
  if (line.startsWith("[")) return "text-white/40 italic";
  return "text-white/85";
}
