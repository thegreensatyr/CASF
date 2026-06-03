import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../lib/api";
import { Quote } from "lucide-react";

export default function CommunityQuote() {
  const [post, setPost] = useState(null);
  useEffect(() => {
    api.get("/scams?sort=top").then((r) => {
      const sorted = (r.data || []).filter((p) => p.score >= 0);
      if (sorted.length) setPost(sorted[0]);
    }).catch(() => {});
  }, []);

  if (!post) return null;

  return (
    <section className="border-t border-white/10 bg-black">
      <div className="max-w-4xl mx-auto px-6 md:px-12 py-20">
        <div className="flex items-start gap-4">
          <Quote className="w-10 h-10 text-[var(--neon)] shrink-0 mt-1" />
          <div>
            <p className="text-xs uppercase tracking-[0.3em] text-[var(--neon)] mb-3">// player verdict · top voted</p>
            <p className="font-heading text-2xl md:text-4xl tracking-tighter leading-tight mb-6">
              "{post.title}"
            </p>
            <p className="text-sm font-mono text-white/70 leading-relaxed line-clamp-3 mb-4">
              {post.story}
            </p>
            <div className="flex items-center gap-4 text-[10px] uppercase tracking-widest text-white/50 font-mono">
              <span>{post.author_name}</span>
              <span>·</span>
              <span>{post.casino_name}</span>
              <span>·</span>
              <span className="text-[var(--neon)]">{post.score} upvotes</span>
              <span>·</span>
              <Link to={`/scams/${post.id}`} className="text-[var(--neon)]">Read &gt;_</Link>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
