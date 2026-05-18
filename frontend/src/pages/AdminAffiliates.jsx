import { useEffect, useState } from "react";
import { api } from "../lib/api";
import { useAuth } from "../context/AuthContext";
import { toast } from "sonner";
import { Plus, Trash2, Save, BarChart3 } from "lucide-react";
import { Link } from "react-router-dom";

const EMPTY = {
  name: "", url: "", license: "", badge: "", description: "",
  logo_url: "", payout_note: "", sort_order: 0, active: true,
};

export default function AdminAffiliates() {
  const { user } = useAuth();
  const [casinos, setCasinos] = useState([]);
  const [stats, setStats] = useState([]);
  const [form, setForm] = useState(EMPTY);
  const [editId, setEditId] = useState(null);

  const load = async () => {
    try {
      const [a, s] = await Promise.all([
        api.get("/affiliates/casinos/all"),
        api.get("/affiliates/stats"),
      ]);
      setCasinos(a.data); setStats(s.data);
    } catch (e) {
      toast.error("Failed to load. Admins only.");
    }
  };

  useEffect(() => { if (user?.is_admin) load(); }, [user]);

  if (!user) return <div className="p-10 text-center text-white/60 font-mono">Login required.</div>;
  if (!user.is_admin) {
    return (
      <div className="max-w-md mx-auto p-10 text-center">
        <p className="font-mono text-sm text-white/70">Admin access required. Set ADMIN_EMAIL in backend/.env to your email and re-login.</p>
      </div>
    );
  }

  const upd = (k) => (e) => {
    const v = k === "active" ? e.target.checked : (k === "sort_order" ? Number(e.target.value) : e.target.value);
    setForm({ ...form, [k]: v });
  };

  const save = async (e) => {
    e.preventDefault();
    try {
      if (editId) {
        await api.put(`/affiliates/casinos/${editId}`, form);
        toast.success("Updated");
      } else {
        await api.post("/affiliates/casinos", form);
        toast.success("Created");
      }
      setForm(EMPTY); setEditId(null);
      load();
    } catch (e) { toast.error(e?.response?.data?.detail || "Save failed"); }
  };

  const edit = (c) => {
    setForm({ ...c });
    setEditId(c.id);
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  const remove = async (cid) => {
    if (!window.confirm("Delete this casino?")) return;
    await api.delete(`/affiliates/casinos/${cid}`);
    toast.success("Deleted"); load();
  };

  const clicksFor = (cid) => stats.find((s) => s.id === cid)?.clicks ?? 0;

  return (
    <div className="max-w-6xl mx-auto px-6 md:px-12 py-12">
      <p className="text-xs uppercase tracking-[0.3em] text-[var(--neon)] mb-2">// admin</p>
      <h1 className="font-heading text-4xl md:text-5xl tracking-tighter mb-2">AFFILIATE CASINOS</h1>
      <p className="text-sm text-white/60 font-mono mb-10">
        &gt; Manage the trusted-casino CTAs that appear on low-trust reports, technique pages and the scam wall.
        {" "}
        <Link to="/admin/guide" className="text-[var(--neon)] underline" data-testid="link-monetization-guide">
          New here? Read the monetization quick-start &gt;_
        </Link>
      </p>

      <form onSubmit={save} className="panel p-6 mb-10 space-y-4" data-testid="affiliate-form">
        <div className="flex items-center justify-between mb-2">
          <h2 className="font-heading text-lg">{editId ? "Edit casino" : "Add new casino"}</h2>
          {editId && (
            <button type="button" onClick={() => { setForm(EMPTY); setEditId(null); }} className="text-xs text-white/60 underline">
              Cancel edit
            </button>
          )}
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <Field label="NAME *" value={form.name} onChange={upd("name")} testid="aff-name" />
          <Field label="AFFILIATE URL *" value={form.url} onChange={upd("url")} testid="aff-url" placeholder="https://casino.com/?ref=YOUR_ID" />
          <Field label="LICENSE" value={form.license} onChange={upd("license")} testid="aff-license" placeholder="UKGC / MGA / NJ DGE" />
          <Field label="BADGE" value={form.badge} onChange={upd("badge")} testid="aff-badge" placeholder="MGA Licensed" />
          <Field label="PAYOUT NOTE" value={form.payout_note} onChange={upd("payout_note")} testid="aff-payout" placeholder="24h payouts" />
          <Field label="SORT ORDER" type="number" value={form.sort_order} onChange={upd("sort_order")} testid="aff-sort" />
        </div>
        <label className="block">
          <span className="block text-xs uppercase tracking-widest text-white/60 mb-1 font-heading">DESCRIPTION</span>
          <textarea
            data-testid="aff-description"
            value={form.description}
            onChange={upd("description")}
            rows={3}
            maxLength={400}
            className="input-neon resize-y"
            placeholder="Short reason this operator is trusted (audit, license, payout speed...)"
          />
        </label>
        <label className="flex items-center gap-2 text-xs uppercase tracking-widest text-white/60 font-heading">
          <input type="checkbox" checked={form.active} onChange={upd("active")} data-testid="aff-active" />
          Active (shown to users)
        </label>
        <button type="submit" className="btn-neon flex items-center gap-2" data-testid="aff-save">
          {editId ? <><Save className="w-4 h-4"/> Save changes</> : <><Plus className="w-4 h-4"/> Add casino</>}
        </button>
      </form>

      <h2 className="font-heading text-lg mb-3 flex items-center gap-2">
        <BarChart3 className="w-4 h-4 text-[var(--neon)]"/> Current roster ({casinos.length})
      </h2>
      <div className="space-y-3">
        {casinos.length === 0 && (
          <p className="text-xs text-white/40 font-mono">No casinos yet. Add one above.</p>
        )}
        {casinos.map((c) => (
          <div key={c.id} className="panel p-4 flex items-center justify-between gap-4" data-testid={`aff-row-${c.id}`}>
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 flex-wrap">
                <span className="font-heading">{c.name}</span>
                {c.badge && <span className="tag">{c.badge}</span>}
                {!c.active && <span className="tag text-white/40 border-white/20">inactive</span>}
              </div>
              <p className="text-[10px] text-white/50 font-mono truncate">{c.url}</p>
            </div>
            <div className="text-right">
              <div className="font-heading text-2xl text-[var(--neon)]">{clicksFor(c.id)}</div>
              <div className="text-[10px] uppercase tracking-widest text-white/50">clicks</div>
            </div>
            <div className="flex gap-2">
              <button onClick={() => edit(c)} className="btn-ghost text-xs" data-testid={`aff-edit-${c.id}`}>Edit</button>
              <button onClick={() => remove(c.id)} className="btn-ghost text-xs border-[var(--danger)]/50 text-[var(--danger)]" data-testid={`aff-delete-${c.id}`}>
                <Trash2 className="w-3 h-3"/>
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function Field({ label, value, onChange, testid, placeholder, type="text" }) {
  return (
    <label className="block">
      <span className="block text-xs uppercase tracking-widest text-white/60 mb-1 font-heading">{label}</span>
      <input
        data-testid={testid}
        type={type}
        value={value}
        onChange={onChange}
        placeholder={placeholder}
        className="input-neon"
      />
    </label>
  );
}
