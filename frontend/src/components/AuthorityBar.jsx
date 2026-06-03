import { Cpu } from "lucide-react";

const TECH = [
  { name: "Claude Sonnet 4.5", note: "trust analysis" },
  { name: "Gemini 3 Flash", note: "video forensics" },
  { name: "FastAPI", note: "backend" },
  { name: "MongoDB", note: "encrypted log" },
  { name: "eCOGRA refs", note: "audit standard" },
  { name: "BeGambleAware", note: "responsible play" },
];

export default function AuthorityBar() {
  return (
    <section className="border-t border-white/10 bg-[#0a0a0a]">
      <div className="max-w-7xl mx-auto px-6 md:px-12 py-10">
        <div className="flex items-center gap-3 mb-6">
          <Cpu className="w-4 h-4 text-[var(--neon)]" />
          <span className="text-xs uppercase tracking-[0.3em] text-white/60">// powered by · referenced by</span>
        </div>
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
          {TECH.map((t) => (
            <div key={t.name} className="panel p-3 px-4 hover:border-[var(--neon-dim)] transition">
              <div className="font-heading text-sm text-white truncate">{t.name}</div>
              <div className="text-[10px] uppercase tracking-widest text-white/40 font-mono mt-0.5">{t.note}</div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
