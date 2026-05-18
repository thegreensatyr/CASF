import { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
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
      <p className="text-xs mt-6 text-white/60 font-mono">
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
