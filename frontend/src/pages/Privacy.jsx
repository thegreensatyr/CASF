import { useEffect } from "react";

export default function Privacy() {
  useEffect(() => { document.title = "Privacy Policy · Casino Spotter"; }, []);
  return (
    <div className="max-w-3xl mx-auto px-6 py-12 prose-neon" data-testid="privacy-page">
      <p className="text-xs uppercase tracking-[0.3em] text-[var(--neon)] mb-2">// legal</p>
      <h1 className="font-heading text-4xl tracking-tighter mb-2">Privacy Policy</h1>
      <p className="text-xs text-white/50 font-mono mb-8">Last updated: February 2026</p>

      <Section title="1. Who we are">
        Casino Spotter (&quot;we&quot;, &quot;us&quot;) operates the website at casforensics.org. We are an
        independent editorial and forensic-analysis service. We are not a casino operator and
        we do not facilitate gambling transactions.
      </Section>

      <Section title="2. What we collect">
        We collect: (a) your email address and a name when you create an account; (b) usage data
        such as scans you run and reports you generate; (c) IP address and basic request metadata
        for security and rate-limiting; (d) payment metadata (transaction IDs, not card numbers)
        if you subscribe to Premium via Stripe; (e) optional content you submit to the Scam Wall
        or dispute system. We do not sell, rent, or share your email with third parties.
      </Section>

      <Section title="3. How we use it">
        Email is used to authenticate your account, deliver service notifications (password reset,
        weekly digest if you opted in), and to attribute traffic sources for our own analytics.
        Scan data is used to provide the service to you and (in anonymized aggregate) to improve
        our forensic models. You can request deletion at any time via
        <a href="mailto:corrections@casforensics.org" className="text-[var(--neon)] underline"> corrections@casforensics.org</a>.
      </Section>

      <Section title="4. AI processing">
        Casino names, video clips, and screen-capture frames you submit are sent to third-party AI
        providers (Google Gemini, Anthropic Claude) for analysis under standard B2B terms. These
        providers process the content transiently and do not retain it for model training. We
        store the analysis output (text and structured findings) on your account.
      </Section>

      <Section title="5. Payments">
        Subscription payments are processed by Stripe. We never see or store your full card
        number; we only retain Stripe&apos;s transaction IDs and subscription status.
      </Section>

      <Section title="6. Cookies">
        We use a single first-party token in localStorage to keep you signed in. We do not use
        third-party advertising cookies or cross-site trackers.
      </Section>

      <Section title="7. Your rights">
        You can: (a) view and download your data via your dashboard; (b) request deletion of your
        account and all associated reports; (c) export your data as JSON on request; (d) opt out
        of the weekly digest at any time. EU/UK residents have additional rights under GDPR/UK
        GDPR; we honor all such requests.
      </Section>

      <Section title="8. Contact">
        Privacy questions, deletion requests, or data exports:{" "}
        <a href="mailto:corrections@casforensics.org" className="text-[var(--neon)] underline">corrections@casforensics.org</a>.
      </Section>
    </div>
  );
}

function Section({ title, children }) {
  return (
    <section className="mb-8" data-testid={`privacy-section-${title.split(".")[0]}`}>
      <h2 className="font-heading text-xl mb-3 text-white">{title}</h2>
      <p className="text-sm font-mono text-white/75 leading-relaxed">{children}</p>
    </section>
  );
}
