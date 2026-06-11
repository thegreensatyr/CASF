import { Link } from "react-router-dom";
import { useEffect, useState } from "react";
import { api } from "../lib/api";
import { ShieldCheck, Eye, Brain, Cpu, AlertTriangle, ScanLine } from "lucide-react";
import HowItWorks from "../components/HowItWorks";
import ActivityFeed from "../components/ActivityFeed";
import CommunityQuote from "../components/CommunityQuote";
import AuthorityBar from "../components/AuthorityBar";
import { CountUp } from "../lib/ui";

const HERO_BG = "https://static.prod-images.emergentagent.com/jobs/8caf52cb-094a-4d65-a90d-80fcc35c450b/images/75b76f05881f4e4a221ee963f2c32def964326102990541391542ed1f042ba58.png";
const ROULETTE = "https://static.prod-images.emergentagent.com/jobs/8caf52cb-094a-4d65-a90d-80fcc35c450b/images/e86a09562d24b0d9d2a7744aa33200add6771aeacfd9183d5c81dbcba24590c3.png";
const LOCK = "https://static.prod-images.emergentagent.com/jobs/8caf52cb-094a-4d65-a90d-80fcc35c450b/images/7cb9af410815f2c5b8df7b7ecf5a1dda3da2bdbe5719cb35f35b9c678ba35a39.png";

export default function Landing() {
  const [stats, setStats] = useState(null);
  useEffect(() => { api.get("/stats/public").then((r) => setStats(r.data)).catch(()=>{}); }, []);
  return (
    <div className="relative">
      {/* Hero */}
      <section className="relative overflow-hidden border-b border-white/10">
        <div
          className="absolute inset-0 opacity-40"
          style={{ backgroundImage: `url(${HERO_BG})`, backgroundSize: "cover", backgroundPosition: "center" }}
        />
        <div className="absolute inset-0 grid-bg opacity-30" />
        <div className="absolute inset-0 bg-gradient-to-b from-transparent via-black/40 to-black" />

        <div className="relative max-w-7xl mx-auto px-6 md:px-12 py-24 md:py-36">
          <div className="flex items-center gap-2 mb-6">
            <span className="dot-pulse w-2 h-2 rounded-full bg-[var(--neon)]" />
            <span className="text-xs uppercase tracking-[0.3em] text-[var(--neon)]">live forensic feed</span>
          </div>
          <h1 className="font-heading font-black text-4xl sm:text-5xl lg:text-7xl leading-[0.95] tracking-tighter max-w-4xl">
            EXPOSE THE <span className="neon-text">RIGGED</span><br/>
            MACHINE BEHIND<br/>
            ONLINE CASINOS<span className="text-[var(--neon)]">.</span>
          </h1>
          <p className="mt-8 max-w-2xl text-base text-white/70 font-mono">
            &gt; Upload a clip of any online casino game. Our AI investigates the math,
            the animations, and the psychology, and tells you exactly how the house
            is bending the truth in real time<span className="caret"/>
          </p>

          <div className="mt-10 flex flex-wrap gap-3">
            <Link to="/signup" className="btn-neon" data-testid="hero-cta-signup">Start scanning &gt;_</Link>
            <Link to="/audit" className="btn-ghost" data-testid="hero-cta-audit">Order deep audit · $24.99</Link>
            <Link to="/techniques" className="btn-ghost" data-testid="hero-cta-tricks">See known tricks</Link>
          </div>

          <div className="mt-16 grid grid-cols-2 md:grid-cols-4 gap-4 max-w-3xl">
            {[
              { k: stats?.casinos_analyzed ?? 0, v: "casinos analyzed" },
              { k: stats?.games_scanned ?? 0, v: "games scanned" },
              { k: stats?.scam_reports ?? 0, v: "scam reports filed" },
              { k: stats?.techniques_documented ?? 0, v: "tricks decoded" },
            ].map((s) => (
              <div key={s.v} className="panel p-4" data-testid={`landing-stat-${s.v.replace(/\s+/g,'-')}`}>
                <div className="font-heading text-2xl text-[var(--neon)]">
                  {stats ? <CountUp to={s.k} /> : "—"}
                </div>
                <div className="text-xs uppercase tracking-widest text-white/60">{s.v}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Features bento */}
      <AuthorityBar />
      <HowItWorks />
      <ActivityFeed />
      <CommunityQuote />

      <section className="max-w-7xl mx-auto px-6 md:px-12 py-24">
        <div className="flex items-end justify-between mb-10">
          <h2 className="font-heading text-3xl md:text-4xl tracking-tighter">
            <span className="text-[var(--neon)]">//</span> THE TOOLKIT
          </h2>
          <span className="hidden md:inline text-xs text-white/40 font-mono">v.1.0 / feb 2026</span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-12 gap-4">
          <div className="md:col-span-7 panel p-8 scanlines relative overflow-hidden">
            <Eye className="w-6 h-6 text-[var(--neon)] mb-4" />
            <h3 className="font-heading text-2xl mb-3">VIDEO / SCREENSHOT FORENSICS</h3>
            <p className="text-sm text-white/70 font-mono leading-relaxed">
              Drop a short clip of a slot spin, roulette round, or any bonus animation.
              Gemini 3 Flash multimodal scrubs every frame, flags near-miss patterns,
              losses-disguised-as-wins, and timing irregularities.
            </p>
            <div className="mt-6 inline-block tag">multimodal &gt;_</div>
          </div>

          <div className="md:col-span-5 panel p-0 overflow-hidden relative">
            <img src={ROULETTE} alt="roulette noir" className="w-full h-56 md:h-full object-cover opacity-90" />
            <div className="absolute inset-0 bg-gradient-to-t from-black via-black/40 to-transparent" />
            <div className="absolute bottom-0 left-0 right-0 p-6">
              <ScanLine className="w-5 h-5 text-[var(--neon)] mb-2" />
              <h3 className="font-heading text-xl">PSYCHOLOGY DECODER</h3>
              <p className="text-xs text-white/70 font-mono mt-1">
                Every dark pattern translated to plain English.
              </p>
            </div>
          </div>

          <div className="md:col-span-4 panel p-8">
            <ShieldCheck className="w-6 h-6 text-[var(--neon)] mb-4" />
            <h3 className="font-heading text-xl mb-2">CASINO TRUST CHECK</h3>
            <p className="text-sm text-white/70 font-mono">
              Type a casino name or URL. Claude Sonnet 4.5 + our curated blacklist
              return a 0-100 trust score with red flags and green flags.
            </p>
          </div>

          <div className="md:col-span-4 panel p-8">
            <Brain className="w-6 h-6 text-[var(--neon)] mb-4" />
            <h3 className="font-heading text-xl mb-2">KNOWLEDGE LIBRARY</h3>
            <p className="text-sm text-white/70 font-mono">
              8+ documented manipulation techniques: near-miss, false RTP, LDW,
              bonus traps, rigged RNG. Read them. Recognize them.
            </p>
          </div>

          <div className="md:col-span-4 panel p-0 overflow-hidden relative">
            <img src={LOCK} alt="trust" className="w-full h-44 object-cover opacity-90" />
            <div className="absolute inset-0 bg-gradient-to-t from-black via-black/30 to-transparent" />
            <div className="absolute bottom-0 left-0 right-0 p-6">
              <Cpu className="w-5 h-5 text-[var(--neon)] mb-2" />
              <h3 className="font-heading text-lg">YOUR PRIVATE LOG</h3>
              <p className="text-xs text-white/70 font-mono mt-1">All analyses saved to your encrypted dashboard.</p>
            </div>
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="border-t border-white/10 bg-black">
        <div className="max-w-7xl mx-auto px-6 md:px-12 py-20 flex flex-col md:flex-row gap-10 items-start md:items-center justify-between">
          <div>
            <AlertTriangle className="w-8 h-8 text-[var(--warn)] mb-4" />
            <h2 className="font-heading text-3xl md:text-5xl tracking-tighter max-w-2xl">
              The house wrote the rules.<br/>
              <span className="neon-text">Now read the source code.</span>
            </h2>
          </div>
          <Link to="/signup" className="btn-neon text-base" data-testid="cta-bottom-signup">
            Run my first scan &gt;_
          </Link>
        </div>
      </section>

      <footer className="border-t border-white/10 py-10 text-center">
        <p className="text-xs text-[var(--neon)] font-mono">
          <CountUp to={(stats?.casinos_analyzed ?? 0) + (stats?.games_scanned ?? 0) + (stats?.scam_reports ?? 0)} duration={1800} /> forensic operations run by the community
        </p>
        <p className="text-[10px] text-white/40 font-mono mt-2">
          casino.spotter / educational use only / play responsibly / 18+
        </p>
      </footer>
    </div>
  );
}
