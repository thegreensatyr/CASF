import { useEffect, useState } from "react";
import { api } from "../lib/api";
import { ExternalLink, ShieldCheck } from "lucide-react";

export default function TrustedCasinoCTA({ source = "unknown", limit = 3, headline = "TRUSTED ALTERNATIVES" }) {
  const [casinos, setCasinos] = useState([]);

  useEffect(() => {
    api.get("/affiliates/casinos").then((r) => setCasinos(r.data)).catch(() => {});
  }, []);

  const onClick = (c) => {
    api.post("/affiliates/click", { affiliate_id: c.id, source }).catch(() => {});
  };

  if (!casinos.length) return null;

  return (
    <div className="panel p-6 mt-8 border-[var(--neon-dim)]" data-testid="trusted-casino-cta">
      <div className="flex items-center gap-2 mb-4">
        <ShieldCheck className="w-4 h-4 text-[var(--neon)]" />
        <span className="text-xs uppercase tracking-[0.3em] text-[var(--neon)]">// {headline}</span>
      </div>
      <p className="text-xs text-white/60 font-mono mb-5">
        &gt; Independently licensed operators with public audit trails. Sponsored placements.
      </p>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
        {casinos.slice(0, limit).map((c) => (
          <a
            key={c.id}
            href={c.url}
            target="_blank"
            rel="noopener nofollow sponsored"
            onClick={() => onClick(c)}
            data-testid={`cta-casino-${c.id}`}
            className="panel p-4 hover:border-[var(--neon)] hover:bg-white/[0.02] transition group"
          >
            <div className="flex items-center justify-between mb-2">
              <span className="font-heading text-base">{c.name}</span>
              <ExternalLink className="w-3 h-3 text-white/40 group-hover:text-[var(--neon)]" />
            </div>
            {c.badge && <span className="tag mb-2 inline-block">{c.badge}</span>}
            {c.description && <p className="text-xs text-white/70 font-mono mt-2 leading-relaxed">{c.description}</p>}
            <div className="flex items-center justify-between mt-3 text-[10px] uppercase tracking-widest text-white/40">
              <span>{c.license || "licensed"}</span>
              {c.payout_note && <span className="text-[var(--neon)]">{c.payout_note}</span>}
            </div>
          </a>
        ))}
      </div>
      <p className="text-[10px] text-white/30 font-mono mt-4">
        18+ · Play responsibly · Affiliate links · Begambleaware.org
      </p>
    </div>
  );
}
