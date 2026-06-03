import { useEffect, useState } from "react";
import { useAuth } from "../context/AuthContext";
import { api } from "../lib/api";
import { toast } from "sonner";
import { Mail, Send, Loader2, Eye } from "lucide-react";

export default function AdminDigest() {
  const { user } = useAuth();
  const [preview, setPreview] = useState(null);
  const [busy, setBusy] = useState(false);
  const [sending, setSending] = useState(false);
  const [lastResult, setLastResult] = useState(null);

  const load = async () => {
    setBusy(true);
    try {
      const { data } = await api.get("/digest/preview");
      setPreview(data);
    } catch (e) { toast.error("Preview failed. Admin only."); }
    finally { setBusy(false); }
  };

  useEffect(() => { if (user?.is_admin) load(); }, [user]);

  const send = async (testOnly) => {
    if (!window.confirm(testOnly
      ? "Send a test digest to your admin email only?"
      : "Send the digest to ALL subscribed users? This action is final.")) return;
    setSending(true);
    try {
      const { data } = await api.post("/digest/send", { test_only: testOnly });
      setLastResult(data);
      toast.success(`Sent ${data.sent} of ${data.total}. ${data.failures} failures.`);
    } catch (e) { toast.error(e?.response?.data?.detail || "Send failed"); }
    finally { setSending(false); }
  };

  if (!user) return <div className="p-10 text-center text-white/60 font-mono">Login required.</div>;
  if (!user.is_admin) return <div className="p-10 text-center text-white/60 font-mono">Admin only.</div>;

  return (
    <div className="max-w-6xl mx-auto px-6 md:px-12 py-12">
      <p className="text-xs uppercase tracking-[0.3em] text-[var(--neon)] mb-2">// admin</p>
      <h1 className="font-heading text-4xl md:text-5xl tracking-tighter mb-2 flex items-center gap-3">
        <Mail className="w-8 h-8 text-[var(--neon)]" /> EMAIL DIGEST
      </h1>
      <p className="text-sm text-white/60 font-mono mb-8">
        &gt; Send the weekly "worst casinos" roundup to subscribers via Resend.
      </p>

      <div className="flex flex-wrap gap-3 mb-8">
        <button onClick={load} disabled={busy} className="btn-ghost text-xs flex items-center gap-2" data-testid="digest-preview-btn">
          {busy ? <Loader2 className="w-3 h-3 animate-spin" /> : <Eye className="w-3 h-3" />} Refresh preview
        </button>
        <button onClick={() => send(true)} disabled={sending} className="btn-ghost text-xs flex items-center gap-2" data-testid="digest-test-btn">
          <Send className="w-3 h-3" /> Send TEST to me
        </button>
        <button onClick={() => send(false)} disabled={sending} className="btn-neon text-xs flex items-center gap-2" data-testid="digest-send-all-btn">
          {sending ? <><Loader2 className="w-3 h-3 animate-spin" /> Sending...</> : <><Send className="w-3 h-3" /> SEND TO ALL &gt;_</>}
        </button>
      </div>

      {lastResult && (
        <div className="panel p-4 mb-6 text-xs font-mono" data-testid="digest-last-result">
          &gt; Last run: {lastResult.sent} sent · {lastResult.failures} failed · {lastResult.total} total
        </div>
      )}

      {preview && (
        <div>
          <div className="panel p-4 mb-4">
            <p className="text-xs uppercase tracking-widest text-white/60">Subject line</p>
            <p className="font-heading text-base text-[var(--neon)]" data-testid="digest-subject">{preview.subject}</p>
            <p className="text-[10px] text-white/40 font-mono mt-2">Featured {preview.casino_count} casinos in this digest.</p>
          </div>
          <div className="panel p-2">
            <iframe
              title="digest-preview"
              srcDoc={preview.html}
              className="w-full h-[700px] border-0"
              data-testid="digest-iframe"
            />
          </div>
        </div>
      )}
    </div>
  );
}
