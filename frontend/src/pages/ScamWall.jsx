import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api } from "../lib/api";
import { useAuth } from "../context/AuthContext";
import { toast } from "sonner";
import { ArrowUp, ArrowDown, Plus, Flame, Clock, ArrowLeft, ExternalLink } from "lucide-react";

export function ScamWall() {
  const [posts, setPosts] = useState([]);
  const [sort, setSort] = useState("top");
  const [loading, setLoading] = useState(true);
  const { user } = useAuth();

  const load = async (s = sort) => {
    setLoading(true);
    try {
      const { data } = await api.get(`/scams?sort=${s}`);
      setPosts(data);
    } catch (e) { /* ignore */ }
    finally { setLoading(false); }
  };

  useEffect(() => { load(sort); /* eslint-disable-next-line */ }, [sort]);

  const vote = async (post, voteType) => {
    if (!user) return toast.error("Sign in to vote");
    const newVote = post.my_vote === voteType ? "none" : voteType;
    try {
      const { data } = await api.post(`/scams/${post.id}/vote`, { vote: newVote });
      setPosts((prev) => prev.map((p) => (p.id === post.id ? data : p)));
    } catch (e) { toast.error("Vote failed"); }
  };

  return (
    <div className="max-w-5xl mx-auto px-6 md:px-12 py-12">
      <div className="flex items-end justify-between flex-wrap gap-4 mb-10">
        <div>
          <p className="text-xs uppercase tracking-[0.3em] text-[var(--neon)] mb-2">// community intel</p>
          <h1 className="font-heading text-4xl md:text-5xl tracking-tighter">SCAM WALL</h1>
          <p className="text-sm text-white/60 font-mono mt-2">&gt; Player-submitted reports. Vote to surface the worst.</p>
        </div>
        <Link to="/scams/new" className="btn-neon flex items-center gap-2" data-testid="new-scam-link">
          <Plus className="w-4 h-4" /> Submit report
        </Link>
      </div>

      <div className="flex gap-2 mb-6">
        <SortBtn active={sort === "top"} onClick={() => setSort("top")} icon={<Flame className="w-3 h-3" />} label="Top" testid="sort-top" />
        <SortBtn active={sort === "new"} onClick={() => setSort("new")} icon={<Clock className="w-3 h-3" />} label="New" testid="sort-new" />
      </div>

      {loading && <div className="text-xs font-mono text-[var(--neon)]">&gt; loading reports...</div>}
      {!loading && posts.length === 0 && (
        <div className="panel p-10 text-center">
          <p className="text-sm font-mono text-white/60">No reports yet. Be the first to expose one.</p>
          <Link to="/scams/new" className="btn-neon inline-block mt-4 text-xs">Submit the first report &gt;_</Link>
        </div>
      )}

      <div className="space-y-3">
        {posts.map((p) => (
          <div key={p.id} className="panel p-5 flex gap-4" data-testid={`scam-post-${p.id}`}>
            <div className="flex flex-col items-center min-w-[44px]">
              <button
                data-testid={`upvote-${p.id}`}
                onClick={() => vote(p, "up")}
                className={`p-1 transition ${p.my_vote === "up" ? "text-[var(--neon)]" : "text-white/40 hover:text-[var(--neon)]"}`}
              >
                <ArrowUp className="w-5 h-5" />
              </button>
              <span className="font-heading text-lg" data-testid={`score-${p.id}`}>{p.score}</span>
              <button
                data-testid={`downvote-${p.id}`}
                onClick={() => vote(p, "down")}
                className={`p-1 transition ${p.my_vote === "down" ? "text-[var(--danger)]" : "text-white/40 hover:text-[var(--danger)]"}`}
              >
                <ArrowDown className="w-5 h-5" />
              </button>
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 flex-wrap mb-1">
                <span className="tag">{p.casino_name}</span>
                <span className="text-[10px] uppercase tracking-widest text-white/40">
                  by {p.author_name} · {new Date(p.created_at).toLocaleDateString()}
                </span>
              </div>
              <Link to={`/scams/${p.id}`} className="font-heading text-xl text-white hover:text-[var(--neon)] transition block">
                {p.title}
              </Link>
              <p className="text-xs text-white/70 font-mono mt-2 line-clamp-2">{p.story}</p>
              <div className="flex items-center gap-4 mt-3 text-[10px] uppercase tracking-widest text-white/50">
                <span>{p.upvotes} up</span>
                <span>{p.downvotes} down</span>
                <Link to={`/scams/${p.id}`} className="text-[var(--neon)]">Read &gt;_</Link>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function SortBtn({ active, onClick, icon, label, testid }) {
  return (
    <button
      data-testid={testid}
      onClick={onClick}
      className={`flex items-center gap-2 px-3 py-1.5 text-xs uppercase tracking-widest font-heading border transition ${
        active ? "border-[var(--neon)] text-[var(--neon)] bg-[var(--neon-glow)]" : "border-white/20 text-white/60 hover:border-[var(--neon)]"
      }`}
    >
      {icon} {label}
    </button>
  );
}

export function NewScam() {
  const nav = useNavigate();
  const { user } = useAuth();
  const [form, setForm] = useState({ casino_name: "", title: "", story: "", evidence_url: "" });
  const [busy, setBusy] = useState(false);

  if (!user) {
    return (
      <div className="max-w-md mx-auto p-10 text-center">
        <p className="font-mono text-sm text-white/70 mb-4">Sign in to submit a scam report.</p>
        <Link to="/login" className="btn-neon">Login &gt;_</Link>
      </div>
    );
  }

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    try {
      const { data } = await api.post("/scams", form);
      toast.success("Report published");
      nav(`/scams/${data.id}`);
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Submission failed");
    } finally { setBusy(false); }
  };

  const upd = (k) => (e) => setForm({ ...form, [k]: e.target.value });

  return (
    <div className="max-w-2xl mx-auto px-6 md:px-12 py-12">
      <Link to="/scams" className="inline-flex items-center gap-2 text-xs uppercase tracking-widest mb-6">
        <ArrowLeft className="w-3 h-3" /> Back to wall
      </Link>
      <p className="text-xs uppercase tracking-[0.3em] text-[var(--neon)] mb-2">// new submission</p>
      <h1 className="font-heading text-4xl tracking-tighter mb-2">FILE A REPORT</h1>
      <p className="text-sm text-white/60 font-mono mb-8">&gt; Detail the manipulation. Other players will vote.</p>

      <form onSubmit={submit} className="panel p-6 space-y-5" data-testid="new-scam-form">
        <Field label="CASINO NAME *" value={form.casino_name} onChange={upd("casino_name")} testid="form-casino-name" />
        <Field label="HEADLINE *" value={form.title} onChange={upd("title")} testid="form-title"
          placeholder="e.g. SuperStarz delayed my $4k withdrawal for 6 weeks" />
        <label className="block">
          <span className="block text-xs uppercase tracking-widest text-white/60 mb-1 font-heading">YOUR STORY *</span>
          <textarea
            data-testid="form-story"
            value={form.story}
            onChange={upd("story")}
            rows={8}
            required minLength={20} maxLength={5000}
            className="input-neon resize-y"
            placeholder="What happened? Be specific: amounts, dates, casino's responses..."
          />
          <span className="text-[10px] text-white/40 font-mono">{form.story.length}/5000</span>
        </label>
        <Field label="EVIDENCE URL (optional)" value={form.evidence_url} onChange={upd("evidence_url")}
          placeholder="Link to screenshot, video, or external proof" testid="form-evidence" />
        <button className="btn-neon w-full" disabled={busy} data-testid="form-submit">
          {busy ? "Publishing..." : "PUBLISH REPORT >_"}
        </button>
      </form>
    </div>
  );
}

export function ScamDetail() {
  const { id } = useParams();
  const { user } = useAuth();
  const [post, setPost] = useState(null);

  const load = async () => {
    try {
      const { data } = await api.get(`/scams/${id}`);
      setPost(data);
    } catch (e) { /* ignore */ }
  };
  useEffect(() => { load(); /* eslint-disable-next-line */ }, [id]);

  const vote = async (voteType) => {
    if (!user) return toast.error("Sign in to vote");
    const newVote = post.my_vote === voteType ? "none" : voteType;
    const { data } = await api.post(`/scams/${id}/vote`, { vote: newVote });
    setPost(data);
  };

  if (!post) return <div className="p-10 text-[var(--neon)] font-mono">Loading...</div>;

  return (
    <div className="max-w-3xl mx-auto px-6 md:px-12 py-12">
      <Link to="/scams" className="inline-flex items-center gap-2 text-xs uppercase tracking-widest mb-6">
        <ArrowLeft className="w-3 h-3" /> All reports
      </Link>
      <div className="flex items-center gap-2 mb-3 flex-wrap">
        <span className="tag">{post.casino_name}</span>
        <span className="text-[10px] uppercase tracking-widest text-white/40">
          by {post.author_name} · {new Date(post.created_at).toLocaleString()}
        </span>
      </div>
      <h1 className="font-heading text-3xl md:text-4xl tracking-tighter mb-6">{post.title}</h1>

      <div className="flex items-center gap-4 mb-6 panel px-4 py-3 w-fit">
        <button
          data-testid="detail-upvote"
          onClick={() => vote("up")}
          className={`flex items-center gap-1 ${post.my_vote === "up" ? "text-[var(--neon)]" : "text-white/60 hover:text-[var(--neon)]"}`}
        >
          <ArrowUp className="w-4 h-4" /> {post.upvotes}
        </button>
        <span className="text-white/30">|</span>
        <button
          data-testid="detail-downvote"
          onClick={() => vote("down")}
          className={`flex items-center gap-1 ${post.my_vote === "down" ? "text-[var(--danger)]" : "text-white/60 hover:text-[var(--danger)]"}`}
        >
          <ArrowDown className="w-4 h-4" /> {post.downvotes}
        </button>
        <span className="text-white/30">|</span>
        <span className="font-heading text-sm">score {post.score}</span>
      </div>

      <p className="text-sm font-mono text-white/85 whitespace-pre-line leading-relaxed">{post.story}</p>

      {post.evidence_url && (
        <a href={post.evidence_url} target="_blank" rel="noopener noreferrer"
          className="inline-flex items-center gap-2 mt-8 btn-ghost text-xs" data-testid="evidence-link">
          <ExternalLink className="w-3 h-3" /> View evidence
        </a>
      )}
    </div>
  );
}

function Field({ label, value, onChange, testid, placeholder }) {
  return (
    <label className="block">
      <span className="block text-xs uppercase tracking-widest text-white/60 mb-1 font-heading">{label}</span>
      <input
        data-testid={testid}
        value={value}
        onChange={onChange}
        required
        placeholder={placeholder}
        className="input-neon"
      />
    </label>
  );
}
