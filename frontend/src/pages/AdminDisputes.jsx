import { useEffect, useState } from "react";
import { api } from "../lib/api";
import { toast } from "sonner";
import { Scale, Check, X, Loader2 } from "lucide-react";

export default function AdminDisputes() {
  const [tab, setTab] = useState("pending");
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [acting, setActing] = useState(null);
  const [notes, setNotes] = useState({}); // id -> review_notes

  const load = (status) => {
    setLoading(true);
    api.get(`/admin/disputes?status_filter=${status}`)
      .then((r) => setItems(r.data))
      .catch((e) => toast.error(e?.response?.data?.detail || "Could not load disputes"))
      .finally(() => setLoading(false));
  };

  useEffect(() => { load(tab); }, [tab]);

  const moderate = async (id, status) => {
    setActing(id);
    try {
      await api.post(`/admin/disputes/${id}/moderate`, {
        status,
        review_notes: notes[id] || "",
      });
      toast.success(`Dispute ${status}`);
      load(tab);
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Moderation failed");
    } finally { setActing(null); }
  };

  return (
    <div className="max-w-5xl mx-auto px-6 py-12" data-testid="admin-disputes-page">
      <p className="text-xs uppercase tracking-[0.3em] text-[var(--neon)] mb-2">// admin · moderation</p>
      <h1 className="font-heading text-3xl md:text-4xl tracking-tighter mb-2 flex items-center gap-3">
        <Scale className="w-7 h-7 text-[var(--neon)]" /> DISPUTES QUEUE
      </h1>
      <p className="text-sm text-white/60 font-mono mb-6">
        &gt; Operator right-of-response submissions. Approve to publish on the public report.
      </p>

      <div className="flex gap-2 mb-6">
        {["pending", "approved", "rejected"].map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-3 py-1.5 text-[11px] uppercase tracking-widest font-mono border ${tab === t ? "border-[var(--neon)] text-[var(--neon)]" : "border-white/15 text-white/50 hover:text-white/80"}`}
            data-testid={`admin-disputes-tab-${t}`}
          >
            {t}
          </button>
        ))}
      </div>

      {loading && (
        <div className="text-center py-12">
          <Loader2 className="w-5 h-5 animate-spin text-[var(--neon)] mx-auto" />
        </div>
      )}

      {!loading && items.length === 0 && (
        <p className="text-xs font-mono text-white/40" data-testid="admin-disputes-empty">
          No <strong>{tab}</strong> disputes.
        </p>
      )}

      <div className="space-y-4">
        {items.map((d) => (
          <div key={d.id} className="panel p-5" data-testid={`admin-dispute-${d.id}`}>
            <div className="flex flex-wrap items-start justify-between gap-3 mb-3">
              <div>
                <p className="text-xs font-mono text-white/40">{d.target_type} · {d.target_slug || d.target_id}</p>
                <h3 className="font-heading text-lg">{d.casino_name}</h3>
                <p className="text-[10px] font-mono text-white/50">
                  {d.contact_name || "—"} {d.role ? `(${d.role})` : ""} · {d.contact_email}
                </p>
                <p className="text-[10px] font-mono text-white/40">
                  submitted {new Date(d.submitted_at).toLocaleString()}
                  {d.reviewed_at && <> · reviewed {new Date(d.reviewed_at).toLocaleString()}</>}
                </p>
              </div>
              <span className={`text-[10px] font-mono uppercase tracking-widest px-2 py-1 border ${
                d.status === "approved" ? "border-[var(--neon)] text-[var(--neon)]" :
                d.status === "rejected" ? "border-[var(--danger)] text-[var(--danger)]" :
                "border-yellow-400/40 text-yellow-400"
              }`}>{d.status}</span>
            </div>

            <p className="text-sm font-mono text-white/80 leading-relaxed whitespace-pre-line border-l-2 border-[var(--neon)]/30 pl-3 mb-3">
              {d.response_text}
            </p>

            {d.review_notes && (
              <p className="text-[11px] font-mono text-white/50 italic mb-3">
                Review note: {d.review_notes}
              </p>
            )}

            {d.status === "pending" && (
              <div className="space-y-2">
                <textarea
                  rows={2}
                  value={notes[d.id] || ""}
                  onChange={(e) => setNotes((p) => ({ ...p, [d.id]: e.target.value }))}
                  placeholder="Internal review note (optional)"
                  className="input-neon text-xs"
                  data-testid={`admin-dispute-notes-${d.id}`}
                />
                <div className="flex gap-2">
                  <button
                    onClick={() => moderate(d.id, "approved")}
                    disabled={acting === d.id}
                    className="btn-neon text-xs flex items-center gap-1"
                    data-testid={`admin-dispute-approve-${d.id}`}
                  >
                    <Check className="w-3 h-3" /> APPROVE & PUBLISH
                  </button>
                  <button
                    onClick={() => moderate(d.id, "rejected")}
                    disabled={acting === d.id}
                    className="btn-ghost text-xs flex items-center gap-1 hover:text-[var(--danger)]"
                    data-testid={`admin-dispute-reject-${d.id}`}
                  >
                    <X className="w-3 h-3" /> REJECT
                  </button>
                </div>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
