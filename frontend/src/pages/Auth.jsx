import { useState, useEffect } from "react";
import { useNavigate, useSearchParams, Link } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { api } from "../lib/api";
import { toast } from "sonner";

export function Login() {
  const { login } = useAuth();
  const nav = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    try {
      await login(email, password);
      toast.success("Welcome back, operator.");
      nav("/dashboard");
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Login failed");
    } finally { setBusy(false); }
  };

  return (
    <AuthShell title="LOGIN" subtitle="Authenticate to access forensic tools">
      <form onSubmit={submit} className="space-y-4" data-testid="login-form">
        <Field label="EMAIL" type="email" value={email} onChange={setEmail} testid="login-email" />
        <Field label="PASSWORD" type="password" value={password} onChange={setPassword} testid="login-password" />
        <button className="btn-neon w-full mt-4" disabled={busy} data-testid="login-submit">
          {busy ? "Verifying..." : "ENTER >_"}
        </button>
      </form>
      <div className="mt-4 text-right">
        <Link to="/forgot-password" className="text-xs text-[var(--neon)] hover:underline font-mono" data-testid="goto-forgot-password">
          Forgot password?
        </Link>
      </div>
      <p className="text-xs mt-4 text-white/60 font-mono">
        New here? <Link to="/signup" className="text-[var(--neon)]" data-testid="goto-signup">Create account</Link>
      </p>
    </AuthShell>
  );
}

export function Signup() {
  const { signup } = useAuth();
  const nav = useNavigate();
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    if (password.length < 6) return toast.error("Password must be 6+ characters");
    setBusy(true);
    try {
      await signup(email, password, name);
      toast.success("Account created. Forensic tools unlocked.");
      nav("/dashboard");
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Signup failed");
    } finally { setBusy(false); }
  };

  return (
    <AuthShell title="SIGN UP" subtitle="Spin up your private investigative log">
      <form onSubmit={submit} className="space-y-4" data-testid="signup-form">
        <Field label="HANDLE" value={name} onChange={setName} testid="signup-name" />
        <Field label="EMAIL" type="email" value={email} onChange={setEmail} testid="signup-email" />
        <Field label="PASSWORD" type="password" value={password} onChange={setPassword} testid="signup-password" />
        <button className="btn-neon w-full mt-4" disabled={busy} data-testid="signup-submit">
          {busy ? "Provisioning..." : "CREATE ACCOUNT >_"}
        </button>
      </form>
      <p className="text-xs mt-6 text-white/60 font-mono">
        Already have an account? <Link to="/login" className="text-[var(--neon)]" data-testid="goto-login">Login</Link>
      </p>
    </AuthShell>
  );
}

function Field({ label, type = "text", value, onChange, testid }) {
  return (
    <label className="block">
      <span className="block text-xs uppercase tracking-widest text-white/60 mb-1 font-heading">{label}</span>
      <input
        data-testid={testid}
        type={type}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        required
        className="input-neon"
      />
    </label>
  );
}

function AuthShell({ title, subtitle, children }) {
  return (
    <div className="min-h-[calc(100vh-64px)] flex items-center justify-center p-6">
      <div className="w-full max-w-md panel p-8 scanlines">
        <div className="flex items-center gap-2 mb-1">
          <span className="dot-pulse w-2 h-2 rounded-full bg-[var(--neon)]" />
          <span className="text-xs uppercase tracking-[0.3em] text-[var(--neon)]">secure terminal</span>
        </div>
        <h1 className="font-heading text-3xl mb-1">{title}</h1>
        <p className="text-xs text-white/60 font-mono mb-6">&gt; {subtitle}</p>
        {children}
      </div>
    </div>
  );
}

export function ForgotPassword() {
  const [email, setEmail] = useState("");
  const [busy, setBusy] = useState(false);
  const [sent, setSent] = useState(false);
  const [debugLink, setDebugLink] = useState("");

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    try {
      const { data } = await api.post("/auth/forgot-password", { email, origin_url: window.location.origin });
      setSent(true);
      if (data?.debug_link) {
        setDebugLink(data.debug_link);
        toast.success("Admin reset link generated below.");
      } else {
        toast.success("If that email exists, a reset link was sent.");
      }
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Could not request reset");
    } finally { setBusy(false); }
  };

  return (
    <AuthShell title="FORGOT PASSWORD" subtitle="Request a one-time reset link">
      {sent ? (
        <div className="space-y-4" data-testid="forgot-sent">
          <p className="text-sm text-white/80 font-mono">
            If an account exists for <span className="text-[var(--neon)]">{email}</span>, a reset link has been dispatched. It expires in 1 hour.
          </p>
          {debugLink && (
            <div className="panel p-3 border border-[var(--neon)]/40 bg-black/40">
              <div className="text-[10px] uppercase tracking-widest text-[var(--neon)] mb-1">admin debug link</div>
              <a
                href={debugLink}
                className="text-xs text-[var(--neon)] break-all underline font-mono"
                data-testid="forgot-debug-link"
              >
                {debugLink}
              </a>
              <p className="text-[10px] text-white/40 mt-2 font-mono">Shown only because Resend DNS isn&apos;t verified yet. Click to set a new password.</p>
            </div>
          )}
          <Link to="/login" className="block text-xs text-[var(--neon)] font-mono" data-testid="forgot-back-login">&lt; Back to login</Link>
        </div>
      ) : (
        <form onSubmit={submit} className="space-y-4" data-testid="forgot-form">
          <Field label="EMAIL" type="email" value={email} onChange={setEmail} testid="forgot-email" />
          <button className="btn-neon w-full mt-4" disabled={busy} data-testid="forgot-submit">
            {busy ? "Dispatching..." : "SEND RESET LINK >_"}
          </button>
          <p className="text-xs text-white/60 font-mono">
            Remembered it? <Link to="/login" className="text-[var(--neon)]" data-testid="forgot-goto-login">Back to login</Link>
          </p>
        </form>
      )}
    </AuthShell>
  );
}

export function ResetPassword() {
  const [params] = useSearchParams();
  const nav = useNavigate();
  const token = params.get("token") || "";
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!token) toast.error("Missing reset token");
  }, [token]);

  const submit = async (e) => {
    e.preventDefault();
    if (password.length < 6) return toast.error("Password must be 6+ characters");
    if (password !== confirm) return toast.error("Passwords do not match");
    setBusy(true);
    try {
      const { data } = await api.post("/auth/reset-password", { token, password });
      localStorage.setItem("cs_token", data.token);
      toast.success("Password updated. You're signed in.");
      // Hard reload so AuthContext picks up the new token
      window.location.href = "/dashboard";
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Reset failed");
    } finally { setBusy(false); }
  };

  return (
    <AuthShell title="RESET PASSWORD" subtitle="Choose a new password for your account">
      <form onSubmit={submit} className="space-y-4" data-testid="reset-form">
        <Field label="NEW PASSWORD" type="password" value={password} onChange={setPassword} testid="reset-password" />
        <Field label="CONFIRM PASSWORD" type="password" value={confirm} onChange={setConfirm} testid="reset-confirm" />
        <button className="btn-neon w-full mt-4" disabled={busy || !token} data-testid="reset-submit">
          {busy ? "Updating..." : "SET PASSWORD >_"}
        </button>
        {!token && (
          <p className="text-xs text-red-400 font-mono" data-testid="reset-no-token">
            No reset token in URL. Request a new <Link to="/forgot-password" className="text-[var(--neon)] underline">reset link</Link>.
          </p>
        )}
        <p className="text-xs text-white/60 font-mono">
          <Link to="/login" className="text-[var(--neon)]" data-testid="reset-goto-login">Back to login</Link>
        </p>
      </form>
    </AuthShell>
  );
}
