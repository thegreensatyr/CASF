import { Link, useNavigate, useLocation } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { Terminal, LogOut } from "lucide-react";

export default function Navbar() {
  const { user, logout } = useAuth();
  const nav = useNavigate();
  const loc = useLocation();

  const NavLink = ({ to, label }) => (
    <Link
      to={to}
      data-testid={`nav-${label.toLowerCase()}-link`}
      className={`px-3 py-2 text-xs uppercase tracking-widest font-heading transition ${
        loc.pathname === to ? "text-[var(--neon)]" : "text-white/70 hover:text-[var(--neon)]"
      }`}
    >
      {label}
    </Link>
  );

  return (
    <header className="sticky top-0 z-50 bg-black/80 backdrop-blur-xl border-b border-white/10">
      <div className="max-w-7xl mx-auto flex items-center justify-between px-6 py-3">
        <Link to="/" className="flex items-center gap-2" data-testid="brand-link">
          <Terminal className="w-5 h-5 text-[var(--neon)]" />
          <span className="font-heading font-black text-base tracking-tight">
            CASINO<span className="text-[var(--neon)]">.SPOTTER</span>
          </span>
        </Link>

        <nav className="hidden md:flex items-center gap-1">
          <NavLink to="/" label="Home" />
          <NavLink to="/techniques" label="Tricks" />
          {user && <NavLink to="/dashboard" label="Dashboard" />}
          {user && <NavLink to="/analyze" label="Analyze" />}
          {user && <NavLink to="/legitimacy" label="Verify" />}
        </nav>

        <div className="flex items-center gap-2">
          {user ? (
            <>
              <span className="text-xs text-white/60 hidden sm:inline" data-testid="user-email">{user.email}</span>
              <button
                data-testid="logout-btn"
                onClick={() => { logout(); nav("/"); }}
                className="btn-ghost text-xs flex items-center gap-1"
              >
                <LogOut className="w-3 h-3" /> Exit
              </button>
            </>
          ) : (
            <>
              <Link to="/login" className="btn-ghost text-xs" data-testid="login-link">Login</Link>
              <Link to="/signup" className="btn-neon text-xs" data-testid="signup-link">Sign up</Link>
            </>
          )}
        </div>
      </div>
    </header>
  );
}
