import { useEffect } from "react";
import { Link } from "react-router-dom";
import { ShieldCheck, Scale, FileCheck, Sparkles } from "lucide-react";

export default function EditorialStandards() {
  useEffect(() => { document.title = "Editorial Standards · Casino Spotter"; }, []);
  return (
    <div className="max-w-3xl mx-auto px-6 py-12" data-testid="editorial-page">
      <p className="text-xs uppercase tracking-[0.3em] text-[var(--neon)] mb-2">// editorial process</p>
      <h1 className="font-heading text-4xl md:text-5xl tracking-tighter mb-3 leading-tight">
        Editorial Standards
      </h1>
      <p className="text-base text-white/80 font-mono leading-relaxed mb-10 border-l-2 border-[var(--neon)]/60 pl-4">
        Casino Spotter publishes forensic analyses of online casino games and operators. These
        analyses inform real player decisions, so we hold ourselves to standards designed for
        evidence, fairness, and accountability. This page explains how we work.
      </p>

      <Block icon={<ShieldCheck className="w-5 h-5" />} title="1. What our reports are — and aren't">
        Our reports are <strong className="text-white">AI-generated forensic opinions</strong> based
        on (a) publicly available information about the operator (licensing data, regulator
        publications, AskGamblers/Casino Guru/Trustpilot complaints), (b) frame-by-frame analysis
        of user-submitted clips, and (c) our curated database of known operator histories. They are{" "}
        <strong className="text-white">not legal findings</strong>, not court verdicts, and not
        statements of fact in the legal sense. We do not allege criminal conduct against any
        named operator. We describe observed patterns and let players decide.
      </Block>

      <Block icon={<FileCheck className="w-5 h-5" />} title="2. How analyses are produced">
        Video analyses are processed by Google Gemini 3 Flash with a frame-by-frame visual
        forensics prompt focused on identifying documented manipulation techniques (near-miss
        programming, losses disguised as wins, false RTP, etc.). Trust reports are produced by
        Anthropic Claude Sonnet 4.5 using a system prompt that explicitly forbids accusations of
        criminal conduct and requires measured, observation-based language. Both models are
        instructed to flag uncertainty when relevant data is unavailable.
      </Block>

      <Block icon={<Scale className="w-5 h-5" />} title="3. Source weighting">
        We weight evidence as follows: (a) primary regulator publications (UKGC, MGA, SGA, US
        state regulators) — strongest weight; (b) audit certifications from eCOGRA, iTech Labs,
        GLI — strong weight; (c) AskGamblers complaint database and Casino Guru complaint system
        with verified resolution status — moderate weight; (d) Trustpilot reviews — light weight,
        adjusted for known review-bombing patterns; (e) Reddit and forum reports — context only,
        never sole basis for a finding.
      </Block>

      <Block icon={<Scale className="w-5 h-5" />} title="4. Right of response">
        Every operator named in our reports may submit a formal response via{" "}
        <Link to="/dispute" className="text-[var(--neon)] underline">/dispute</Link>. Submissions
        are reviewed within <strong className="text-white">5 business days</strong>. If accepted,
        the response is published prominently alongside the original report. We do not remove
        reports on demand — public-record analyses stay public — but we always publish operator
        responses. Approved responses include the operator name, the responder&apos;s name and role,
        and the full response text. Email addresses are never published.
      </Block>

      <Block icon={<FileCheck className="w-5 h-5" />} title="5. Corrections policy">
        Factual errors will be corrected within 48 hours of verification. Material corrections
        (those that change the trust score by more than 10 points or the verdict band) are noted
        publicly on the report with a timestamp. Send correction requests to{" "}
        <a href="mailto:corrections@casforensics.org" className="text-[var(--neon)] underline">
          corrections@casforensics.org
        </a>.
      </Block>

      <Block icon={<Sparkles className="w-5 h-5" />} title="6. Editorial independence from affiliates">
        Casino Spotter operates an affiliate program for{" "}
        <strong className="text-white">licensed, audited, well-regulated operators only</strong>.
        Affiliate revenue funds the free-tier service. We maintain editorial independence: (a)
        affiliate operators do not receive favorable treatment in trust reports; (b) the same
        forensic analysis is applied to affiliates as to non-affiliates; (c) affiliate
        disclosures appear prominently on any page that contains a referral link.
      </Block>

      <Block icon={<ShieldCheck className="w-5 h-5" />} title="7. Conflicts of interest">
        Casino Spotter is independently owned. Neither Casino Spotter nor its operators receive
        equity, board positions, or undisclosed payments from any online casino. All revenue
        comes from (a) Premium subscriptions from individual players, (b) transparent affiliate
        commissions from licensed operators, and (c) B2B Verified Operator badges (a fee-for-
        audit service for operators that want to display proof of our independent review).
      </Block>

      <Block icon={<Scale className="w-5 h-5" />} title="8. Responsible gambling commitment">
        Every public report includes a Gamble Aware notice. We do not promote gambling. Premium
        features include built-in deposit-limit reminders. We support, financially and
        editorially, BeGambleAware.org and GamCare. We will never publish content designed to
        encourage problem-gambling behavior.
      </Block>

      <Block icon={<FileCheck className="w-5 h-5" />} title="9. Editorial team">
        Casino Spotter is operated by an independent editorial team using AI tools. All AI-
        generated reports are pre-prompted with our editorial standards above. Human review is
        applied to (a) all approved disputes before publication, (b) all content surfaced on
        the homepage or in the weekly digest, and (c) any report flagged by the corrections
        inbox. Direct contact:{" "}
        <a href="mailto:editorial@casforensics.org" className="text-[var(--neon)] underline">
          editorial@casforensics.org
        </a>.
      </Block>

      <div className="panel p-6 mt-10 bg-black/60">
        <p className="text-xs font-mono text-white/60 leading-relaxed">
          Questions about these standards or our process?{" "}
          <a href="mailto:editorial@casforensics.org" className="text-[var(--neon)] underline">Email the editorial team</a>.
          We respond to all good-faith inquiries within 2 business days.
        </p>
      </div>
    </div>
  );
}

function Block({ icon, title, children }) {
  return (
    <div className="mb-8 flex gap-4" data-testid={`editorial-section-${title.split(".")[0]}`}>
      <div className="text-[var(--neon)] shrink-0 mt-1">{icon}</div>
      <div>
        <h2 className="font-heading text-xl text-white mb-2">{title}</h2>
        <p className="text-sm font-mono text-white/75 leading-relaxed">{children}</p>
      </div>
    </div>
  );
}
