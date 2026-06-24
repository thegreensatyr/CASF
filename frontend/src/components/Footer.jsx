import { Link } from "react-router-dom";

export default function Footer() {
  return (
    <footer className="border-t border-white/10 mt-20 py-10 px-6" data-testid="site-footer">
      <div className="max-w-7xl mx-auto grid grid-cols-2 md:grid-cols-4 gap-6 text-xs font-mono">
        <div>
          <p className="uppercase tracking-widest text-[var(--neon)] mb-3 font-heading">Casino Spotter</p>
          <p className="text-white/50 leading-relaxed">
            Forensic AI for online casino games and operators. Independent. Editorial.
          </p>
        </div>

        <div>
          <p className="uppercase tracking-widest text-white/60 mb-3 font-heading">Explore</p>
          <ul className="space-y-1.5 text-white/55">
            <li><Link to="/techniques" className="hover:text-[var(--neon)]">All techniques</Link></li>
            <li><Link to="/reports" className="hover:text-[var(--neon)]">Public reports</Link></li>
            <li><Link to="/scams" className="hover:text-[var(--neon)]">Scam Wall</Link></li>
            <li><Link to="/compare" className="hover:text-[var(--neon)]">Casino compare</Link></li>
            <li><Link to="/pricing" className="hover:text-[var(--neon)]">Premium</Link></li>
          </ul>
        </div>

        <div>
          <p className="uppercase tracking-widest text-white/60 mb-3 font-heading">Editorial</p>
          <ul className="space-y-1.5 text-white/55">
            <li><Link to="/editorial-standards" className="hover:text-[var(--neon)]" data-testid="footer-editorial-link">Editorial standards</Link></li>
            <li><Link to="/dispute" className="hover:text-[var(--neon)]">Right of response</Link></li>
            <li><a href="mailto:corrections@casforensics.org" className="hover:text-[var(--neon)]">Corrections</a></li>
            <li><Link to="/verified" className="hover:text-[var(--neon)]">For operators</Link></li>
          </ul>
        </div>

        <div>
          <p className="uppercase tracking-widest text-white/60 mb-3 font-heading">Legal</p>
          <ul className="space-y-1.5 text-white/55">
            <li><Link to="/privacy" className="hover:text-[var(--neon)]" data-testid="footer-privacy-link">Privacy policy</Link></li>
            <li><Link to="/terms" className="hover:text-[var(--neon)]" data-testid="footer-terms-link">Terms of service</Link></li>
            <li><a href="mailto:legal@casforensics.org" className="hover:text-[var(--neon)]">Legal contact</a></li>
          </ul>
        </div>
      </div>

      <div className="max-w-7xl mx-auto mt-8 pt-6 border-t border-white/5 flex flex-col md:flex-row gap-2 justify-between text-[10px] text-white/35 font-mono">
        <p>© 2026 Casino Spotter. Educational forensic analysis. 18+/21+ depending on jurisdiction.</p>
        <p>
          Gambling problem? <a href="https://www.begambleaware.org" target="_blank" rel="noopener noreferrer" className="text-[var(--neon)] underline">BeGambleAware.org</a> · 1-800-GAMBLER · 0808 8020 133
        </p>
      </div>
    </footer>
  );
}
