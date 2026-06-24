import { useEffect } from "react";

export default function Terms() {
  useEffect(() => { document.title = "Terms of Service · Casino Spotter"; }, []);
  return (
    <div className="max-w-3xl mx-auto px-6 py-12" data-testid="terms-page">
      <p className="text-xs uppercase tracking-[0.3em] text-[var(--neon)] mb-2">// legal</p>
      <h1 className="font-heading text-4xl tracking-tighter mb-2">Terms of Service</h1>
      <p className="text-xs text-white/50 font-mono mb-8">Last updated: February 2026</p>

      <Section title="1. Acceptance">
        By using Casino Spotter (casforensics.org) you agree to these terms. If you don&apos;t agree,
        don&apos;t use the service. You must be at least 18 years old (21+ in some jurisdictions)
        to use this service.
      </Section>

      <Section title="2. Nature of the service">
        Casino Spotter provides AI-powered forensic analysis of online casino games and operators
        for educational and consumer-protection purposes. Our reports are AI-generated opinions
        based on publicly available information and forensic frame analysis. They are{" "}
        <strong className="text-white">not legal advice</strong>, not financial advice, and not
        statements of fact in the sense of a legal finding. We do not facilitate, broker, or
        process gambling transactions.
      </Section>

      <Section title="3. No guarantee">
        We do not warrant the accuracy, completeness, or current applicability of any analysis.
        Operators&apos; practices change. Regulators change rules. AI models make errors. You are
        solely responsible for any decision you make based on our reports.
      </Section>

      <Section title="4. Right of response">
        Casinos named in any of our reports have a right of response. They may submit a formal
        rebuttal via <a href="/dispute" className="text-[var(--neon)] underline">/dispute</a>{" "}
        which, if accepted, will be published alongside the original report. We do not remove
        reports on demand but we always publish operator responses.
      </Section>

      <Section title="5. User submissions">
        Content you submit to the Scam Wall, disputes, or any user-facing surface is your own.
        You warrant that submissions are truthful and not defamatory. We may remove submissions
        that violate these terms. We do not pre-moderate Scam Wall posts; please report inaccurate
        content via the report button or to corrections@casforensics.org.
      </Section>

      <Section title="6. Premium subscription">
        Premium is a recurring monthly subscription processed via Stripe at the prices shown on{" "}
        <a href="/pricing" className="text-[var(--neon)] underline">/pricing</a>. You can cancel
        at any time from your account; cancellation takes effect at the end of the current billing
        cycle. We do not issue partial refunds for unused time in a billing cycle but we will
        refund the most recent month on request within 14 days.
      </Section>

      <Section title="7. Acceptable use">
        Don&apos;t: (a) attempt to scrape or extract our entire database; (b) use the service to
        harass any operator or individual; (c) submit content you don&apos;t own the rights to; (d)
        attempt to bypass quotas, rate limits, or the free-trial system; (e) resell or rebrand
        our reports without prior written permission. We reserve the right to terminate accounts
        for violations.
      </Section>

      <Section title="8. Responsible gambling">
        This service exists to help inform players. If you or someone you know has a gambling
        problem, please contact a helpline: 1-800-GAMBLER (US), 0808 8020 133 (GamCare UK), or
        visit <a href="https://www.begambleaware.org" className="text-[var(--neon)] underline">BeGambleAware.org</a>.
      </Section>

      <Section title="9. Liability">
        Casino Spotter is provided &quot;as-is&quot; without warranty. To the maximum extent
        permitted by law, our total liability to you for any claim arising from your use of
        the service is limited to the amount you paid us in the 12 months preceding the claim
        (or $50 if you are a free user).
      </Section>

      <Section title="10. Changes &amp; jurisdiction">
        We may update these terms. Material changes will be announced via email to registered
        users. These terms are governed by the laws applicable to the service&apos;s operator. Disputes
        will be resolved via good-faith negotiation first, then via the appropriate jurisdiction.
      </Section>

      <Section title="11. Contact">
        Legal:{" "}
        <a href="mailto:legal@casforensics.org" className="text-[var(--neon)] underline">legal@casforensics.org</a>
        . Editorial corrections: <a href="mailto:corrections@casforensics.org" className="text-[var(--neon)] underline">corrections@casforensics.org</a>.
      </Section>
    </div>
  );
}

function Section({ title, children }) {
  return (
    <section className="mb-8" data-testid={`terms-section-${title.split(".")[0]}`}>
      <h2 className="font-heading text-xl mb-3 text-white">{title}</h2>
      <p className="text-sm font-mono text-white/75 leading-relaxed">{children}</p>
    </section>
  );
}
