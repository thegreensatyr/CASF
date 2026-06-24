import { Link, useNavigate, useLocation } from "react-router-dom";
import { useEffect, useState } from "react";
import { useAuth } from "../context/AuthContext";
import { api } from "../lib/api";
import { Terminal, LogOut, AlertTriangle, Menu, X } from "lucide-react";

function NavLink({ to, label, large = false, active }) {
  return (
    <Link
      to={to}
      data-testid={`nav-${label.toLowerCase().replace(/\s+/g, "-")}-link`}
      className={`${large ? "block py-3 px-4 text-base" : "px-3 py-2 text-xs"} uppercase tracking-widest font-heading transition ${
        active ? "text-[var(--neon)]" : "text-white/70 hover:text-[var(--neon)]"
      }`}
    >
      {label}
    </Link>
  );
}

export default function Navbar() {
  const { user, logout } = useAuth();
  const nav = useNavigate();
  const loc = useLocation();
  const [scamsToday, setScamsToday] = useState(0);
  const [mobileOpen, setMobileOpen] = useState(false);

  useEffect(() => {
    const load = () => api.get("/stats/public").then((r) => setScamsToday(r.data.scams_today || 0)).catch(() => {});
    load();
    const t = setInterval(load, 30000);
    return () => clearInterval(t);
  }, []);

  // Close mobile menu when route changes
  useEffect(() => { setMobileOpen(false); }, [loc.pathname]);

  // Lock body scroll while drawer is open
  useEffect(() => {
    document.body.style.overflow = mobileOpen ? "hidden" : "";
    return () => { document.body.style.overflow = ""; };
  }, [mobileOpen]);

  const navItems = [
    { to: "/", label: "Home", show: true },
    { to: "/techniques", label: "Tricks", show: true },
    { to: "/reports", label: "Reports", show: true },
    { to: "/compare", label: "Compare", show: true },
    { to: "/scams", label: "Wall", show: true },
    { to: "/pricing", label: "Pricing", show: true },
    { to: "/audit", label: "Deep Audit", show: !!user },
    { to: "/dashboard", label: "Dashboard", show: !!user },
    { to: "/analyze", label: "Analyze", show: !!user },
    { to: "/live", label: "Live", show: !!user },
    { to: "/legitimacy", label: "Verify", show: !!user },
    { to: "/admin", label: "Console", show: !!user?.is_admin },
    { to: "/admin/affiliates", label: "Affiliates", show: !!user?.is_admin },
    { to: "/admin/disputes", label: "Disputes", show: !!user?.is_admin },
  ];
  const visibleItems = navItems.filter((i) => i.show);

  return (
    <>
      <header className="sticky top-0 z-50 bg-black/80 backdrop-blur-xl border-b border-white/10">
        <div className="max-w-7xl mx-auto flex items-center justify-between px-4 md:px-6 py-3">
          <Link to="/" className="flex items-center gap-2 min-w-0" data-testid="brand-link">
            <Terminal className="w-5 h-5 text-[var(--neon)] shrink-0" />
            <span className="font-heading font-black text-sm md:text-base tracking-tight truncate">
              CASINO<span className="text-[var(--neon)]">.SPOTTER</span>
            </span>
            {scamsToday > 0 && (
              <Link
                to="/scams"
                data-testid="scams-today-badge"
                className="hidden md:flex items-center gap-1 ml-3 px-2 py-0.5 border border-[var(--danger)]/60 text-[var(--danger)] text-[10px] uppercase tracking-widest font-mono hover:bg-[var(--danger)]/10"
              >
                <AlertTriangle className="w-3 h-3" />
                {scamsToday} new today
              </Link>
            )}
          </Link>

          {/* Desktop nav */}
          <nav className="hidden md:flex items-center gap-1">
            {visibleItems.map((i) => <NavLink key={i.to} to={i.to} label={i.label} active={loc.pathname === i.to} />)}
          </nav>

          {/* Right side: auth + mobile burger */}
          <div className="flex items-center gap-2">
            {user ? (
              <>
                <span className="text-xs text-white/60 hidden lg:inline" data-testid="user-email">{user.email}</span>
                <button
                  data-testid="logout-btn"
                  onClick={() => { logout(); nav("/"); }}
                  className="btn-ghost text-xs items-center gap-1 hidden md:flex"
                >
                  <LogOut className="w-3 h-3" /> Exit
                </button>
              </>
            ) : (
              <>
                <Link to="/login" className="btn-ghost text-xs hidden md:inline-block" data-testid="login-link">Login</Link>
                <Link to="/signup" className="btn-neon text-xs hidden md:inline-block" data-testid="signup-link">Sign up</Link>
              </>
            )}
            {/* Hamburger — only on mobile */}
            <button
              type="button"
              onClick={() => setMobileOpen((v) => !v)}
              className="md:hidden p-2 text-white hover:text-[var(--neon)] transition"
              aria-label={mobileOpen ? "Close menu" : "Open menu"}
              data-testid="mobile-menu-toggle"
            >
              {mobileOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
            </button>
          </div>
        </div>
      </header>

      {/* Mobile drawer */}
      {mobileOpen && (
        <div
          className="fixed inset-0 z-40 md:hidden bg-black/95 backdrop-blur-xl pt-16 overflow-y-auto"
          data-testid="mobile-menu-drawer"
        >
          {scamsToday > 0 && (
            <Link
              to="/scams"
              className="mx-4 mt-4 flex items-center gap-1 px-2 py-1 border border-[var(--danger)]/60 text-[var(--danger)] text-[11px] uppercase tracking-widest font-mono w-fit"
            >
              <AlertTriangle className="w-3 h-3" />
              {scamsToday} scam{scamsToday === 1 ? "" : "s"} flagged today
            </Link>
          )}
          <nav className="flex flex-col py-4 px-2">
            {visibleItems.map((i) => <NavLink key={i.to} to={i.to} label={i.label} large active={loc.pathname === i.to} />)}
          </nav>
          <div className="px-4 pt-4 border-t border-white/10 flex flex-col gap-3">
            {user ? (
              <>
                <div className="text-xs text-white/60 font-mono break-all">{user.email}</div>
                <button
                  onClick={() => { logout(); nav("/"); setMobileOpen(false); }}
                  className="btn-ghost text-xs flex items-center gap-1 w-fit"
                  data-testid="mobile-logout-btn"
                >
                  <LogOut className="w-3 h-3" /> Exit session
                </button>
              </>
            ) : (
              <div className="flex gap-3">
                <Link to="/login" className="btn-ghost text-xs flex-1 text-center" data-testid="mobile-login-link">Login</Link>
                <Link to="/signup" className="btn-neon text-xs flex-1 text-center" data-testid="mobile-signup-link">Sign up</Link>
              </div>
            )}
          </div>
        </div>
      )}
    </>
  );
}
