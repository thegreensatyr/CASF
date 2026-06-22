import { Link } from "react-router-dom";
import { Scale } from "lucide-react";

/**
 * Editorial / legal disclaimer surfaced on every public-facing report page.
 * Critical for affiliate-network approval AND defamation-defense posture.
 */
export default function LegalDisclaimer({ slug, type = "trust" }) {
  return (
    <div
      className="mt-12 border-t border-white/10 pt-6 text-[11px] font-mono text-white/50 leading-relaxed"
      data-testid="legal-disclaimer"
    >
      <div className="flex items-start gap-2 mb-3">
        <Scale className="w-3 h-3 mt-0.5 shrink-0 text-white/40" />
        <div>
          <p className="text-white/60 mb-2">
            <strong className="text-white/80">Editorial standards.</strong>{" "}
            This report is an AI-generated analysis based on publicly available information, user
            submissions, and forensic frame analysis. It reflects observed patterns and educational
            opinion, <strong>not</strong> legal findings of fact. Casino Spotter does not allege
            criminal conduct by any named operator.
          </p>
          <p className="text-white/50 mb-2">
            <strong className="text-white/70">Right of response.</strong>{" "}
            If you represent the operator named in this report and dispute any finding, you may
            submit a formal response that will be attached to this page after review.{" "}
            <Link
              to={`/dispute?type=${type}${slug ? `&slug=${encodeURIComponent(slug)}` : ""}`}
              className="text-[var(--neon)] underline"
              data-testid="legal-dispute-link"
            >
              File a dispute &gt;_
            </Link>
          </p>
          <p className="text-white/40">
            For DMCA, takedown, or correction requests:{" "}
            <a
              href="mailto:corrections@casforensics.org"
              className="text-[var(--neon)] underline"
            >
              corrections@casforensics.org
            </a>
            . Educational purposes only · 18+/21+ · Gambling problem? Call 1-800-GAMBLER or visit{" "}
            <a
              href="https://www.begambleaware.org"
              target="_blank"
              rel="noopener noreferrer"
              className="text-[var(--neon)] underline"
            >
              BeGambleAware.org
            </a>
            .
          </p>
        </div>
      </div>
    </div>
  );
}
