import { useEffect, useState } from "react";
import { api } from "../lib/api";
import { toast } from "sonner";
import { Check, X, RefreshCw, MessageSquareWarning, User, Clock, ArrowRight } from "lucide-react";

const FILTERS = ["pending", "approved", "rejected", "all"];

export default function AdminDisagreements() {
  const [status, setStatus] = useState("pending");
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState({});

  const load = async () => {
    setLoading(true);
    try {
      const q = status === "all" ? "" : `?status=${status}`;
      const { data } = await api.get(`/admin/score-disagreements${q}`);
      setItems(data.items || []);
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Load failed");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); /* eslint-disable-next-line */ }, [status]);

  const act = async (id, action) => {
    setBusy((b) => ({ ...b, [id]: action }));
    try {
      const { data } = await api.post(`/admin/score-disagreements/${id}/${action}`);
      if (action === "approve") {
        if (data.rescan_ok && data.new_score != null) {
          toast.success(`Approved. AI rescanned → new score: ${data.new_score}/100. Live now.`);
        } else {
          toast.success(`Approved. Cache cleared (${data.cache_cleared} report(s)) — rescan will run on next visit.`);
        }
      } else {
        toast.success("Rejected.");
      }
      await load();
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Action failed");
    } finally {
      setBusy((b) => ({ ...b, [id]: null }));
    }
  };

  return (
    <div className="max-w-5xl mx-auto px-6 py-10" data-testid="admin-disagreements-page">
      <div className="flex items-center gap-2 mb-2">
        <MessageSquareWarning className="w-4 h-4 text-[var(--neon)]" />
        <span className="text-xs uppercase tracking-[0.3em] text-[var(--neon)]">// admin review queue</span>
      </div>
      <h1 className="font-heading text-4xl md:text-5xl tracking-tighter mb-2">SCORE DISAGREEMENTS</h1>
      <p className="text-sm text-white/60 font-mono mb-8">
        &gt; Community-submitted score corrections. <span className="text-[var(--neon)]">Approve</span> to clear the AI cache
        and inject the disagreement into the next scan. <span className="text-[var(--warn)]">Reject</span> if noise.
      </p>

      <div className="flex items-center gap-2 mb-8 flex-wrap">
        {FILTERS.map((f) => (
          <button
            key={f}
            onClick={() => setStatus(f)}
            data-testid={`filter-${f}`}
            className={`text-xs uppercase tracking-widest px-3 py-1.5 border rounded transition ${
              status === f
                ? "bg-[var(--neon)] text-black border-[var(--neon)]"
                : "border-white/15 text-white/60 hover:border-[var(--neon)]/50 hover:text-white"
            }`}
          >
            {f}
          </button>
        ))}
        <button
          onClick={load}
          className="text-xs text-white/50 hover:text-[var(--neon)] transition ml-auto flex items-center gap-1"
          data-testid="refresh-list"
        >
          <RefreshCw className="w-3 h-3" /> refresh
        </button>
      </div>

      {loading ? (
        <div className="panel p-8 text-center text-white/60 font-mono text-sm">Loading...</div>
      ) : items.length === 0 ? (
        <div className="panel p-8 text-center text-white/60 font-mono text-sm">
          Nothing in the <span className="text-[var(--neon)]">{status}</span> queue.
        </div>
      ) : (
        <div className="space-y-4">
          {items.map((d) => (
            <DisagreementCard key={d.id} d={d} act={act} busy={busy[d.id]} />
          ))}
        </div>
      )}
    </div>
  );
}

function DisagreementCard({ d, act, busy }) {
  const delta = d.proposed_score - d.current_score;
  const isPending = d.status === "pending";
  return (
    <div className="panel p-5 md:p-6 border border-white/10" data-testid={`disagreement-${d.id}`}>
      <div className="flex flex-col md:flex-row md:items-start md:justify-between gap-4 mb-3">
        <div>
          <div className="flex items-center gap-3 flex-wrap">
            <h3 className="font-heading text-xl tracking-tight">{d.casino_name}</h3>
            {d.firsthand && (
              <span className="tag border-[var(--neon)] text-[var(--neon)] text-[10px]">FIRSTHAND</span>
            )}
            <span className={`tag text-[10px] ${
              d.status === "pending" ? "border-[var(--warn)] text-[var(--warn)]" :
              d.status === "approved" ? "border-[var(--neon)] text-[var(--neon)]" :
              "border-white/20 text-white/40"
            }`}>
              {d.status}
            </span>
          </div>
          <div className="flex items-center gap-2 mt-2 text-[10px] text-white/50 font-mono flex-wrap">
            <User className="w-3 h-3" /> <span>{d.user_email || "anon"}</span>
            <span>·</span>
            <Clock className="w-3 h-3" /> <span>{new Date(d.created_at).toLocaleString()}</span>
            {d.slug && (<><span>·</span><span>slug: {d.slug}</span></>)}
          </div>
        </div>
        <div className="flex items-center gap-3 font-heading text-xl">
          <span className="text-[var(--warn)]">{d.current_score}</span>
          <ArrowRight className="w-4 h-4 text-white/40" />
          <span className="text-[var(--neon)]">{d.proposed_score}</span>
          <span className={`text-xs ${delta > 0 ? "text-[var(--neon)]" : "text-[var(--danger)]"}`}>
            ({delta > 0 ? "+" : ""}{delta})
          </span>
        </div>
      </div>

      <p className="text-sm text-white/85 font-mono leading-relaxed border-l-2 border-white/10 pl-3 mb-4 whitespace-pre-wrap">
        {d.reason}
      </p>

      {isPending && (
        <div className="flex items-center gap-2 pt-2 border-t border-white/10">
          <button
            onClick={() => act(d.id, "approve")}
            disabled={!!busy}
            className="btn-neon text-xs flex items-center gap-1.5"
            data-testid={`approve-${d.id}`}
          >
            <Check className="w-3 h-3" />
            {busy === "approve" ? "Approving..." : "APPROVE & RESCAN"}
          </button>
          <button
            onClick={() => act(d.id, "reject")}
            disabled={!!busy}
            className="btn-ghost text-xs flex items-center gap-1.5"
            data-testid={`reject-${d.id}`}
          >
            <X className="w-3 h-3" />
            {busy === "reject" ? "Rejecting..." : "Reject"}
          </button>
        </div>
      )}

      {!isPending && d.reviewed_by && (
        <p className="text-[10px] text-white/40 font-mono pt-2 border-t border-white/5 mt-2">
          reviewed by {d.reviewed_by} · {d.reviewed_at ? new Date(d.reviewed_at).toLocaleString() : ""}
        </p>
      )}
    </div>
  );
}
