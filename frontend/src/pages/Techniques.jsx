import { useEffect, useState } from "react";
import { api } from "../lib/api";
import { Link, useParams } from "react-router-dom";
import { AlertTriangle, ArrowLeft, BookOpen, Clock, ChevronRight } from "lucide-react";
import TrustedCasinoCTA from "../components/TrustedCasinoCTA";

const SEVERITY_COLOR = {
  low: "text-white/70 border-white/30",
  medium: "text-[var(--warn)] border-[var(--warn)]/60",
  high: "text-orange-400 border-orange-500/60",
  critical: "text-[var(--danger)] border-[var(--danger)]/60",
};

export function Techniques() {
  const [items, setItems] = useState([]);
  useEffect(() => { api.get("/techniques").then((r) => setItems(r.data)); }, []);
  useEffect(() => { document.title = "Casino manipulation techniques — full library · Casino Spotter"; }, []);
  return (
    <div className="max-w-7xl mx-auto px-6 md:px-12 py-16">
      <div className="flex items-end justify-between mb-10">
        <div>
          <p className="text-xs uppercase tracking-[0.3em] text-[var(--neon)] mb-2">// library</p>
          <h1 className="font-heading text-4xl md:text-5xl tracking-tighter">KNOWN TRICKS</h1>
          <p className="text-sm text-white/60 font-mono mt-2 max-w-2xl">
            Every documented manipulation pattern used by online casinos. Long-form articles available on the deep dives.
          </p>
        </div>
        <span className="text-xs font-mono text-white/40 hidden md:inline">{items.length} dossiers</span>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {items.map((t) => (
          <Link
            key={t.slug}
            to={`/techniques/${t.slug}`}
            data-testid={`technique-card-${t.slug}`}
            className={`panel p-6 hover:bg-white/[0.02] transition relative ${t.article ? "border-[var(--neon)]/30" : ""}`}
          >
            {t.article && (
              <span className="absolute top-3 right-3 text-[9px] uppercase tracking-widest text-[var(--neon)] font-mono flex items-center gap-1 bg-black/60 px-1.5 py-0.5 border border-[var(--neon)]/40">
                <BookOpen className="w-2.5 h-2.5" /> deep dive
              </span>
            )}
            <div className="flex items-center justify-between mb-3">
              <span className={`tag ${SEVERITY_COLOR[t.severity]}`}>{t.severity}</span>
              <span className="text-[10px] uppercase tracking-widest text-white/40">{t.category}</span>
            </div>
            <h3 className="font-heading text-xl mb-2">{t.name}</h3>
            <p className="text-xs text-white/70 font-mono leading-relaxed">{t.short}</p>
            <div className="mt-4 flex items-center justify-between">
              <span className="text-[10px] text-[var(--neon)] uppercase tracking-widest">
                {t.article ? `read ${t.article.reading_time_min}-min article` : "read dossier"} &gt;_
              </span>
              {t.article && (
                <span className="text-[10px] text-white/40 font-mono flex items-center gap-1">
                  <Clock className="w-2.5 h-2.5" /> {t.article.reading_time_min}m
                </span>
              )}
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
}

export function TechniqueDetail() {
  const { slug } = useParams();
  const [t, setT] = useState(null);

  useEffect(() => { api.get(`/techniques/${slug}`).then((r) => setT(r.data)); }, [slug]);

  // SEO meta tags + JSON-LD
  useEffect(() => {
    if (!t) return;
    const a = t.article;
    document.title = a ? `${a.seo_title} · Casino Spotter` : `${t.name} · Casino Spotter`;

    // Meta description
    let metaDesc = document.querySelector('meta[name="description"]');
    if (!metaDesc) {
      metaDesc = document.createElement("meta");
      metaDesc.name = "description";
      document.head.appendChild(metaDesc);
    }
    metaDesc.content = a?.meta_description || t.short;

    // Open Graph
    const ogTags = {
      "og:title": a?.seo_title || t.name,
      "og:description": a?.meta_description || t.short,
      "og:type": "article",
      "og:url": window.location.href,
      "twitter:card": "summary_large_image",
      "twitter:title": a?.seo_title || t.name,
      "twitter:description": a?.meta_description || t.short,
    };
    Object.entries(ogTags).forEach(([prop, val]) => {
      let tag = document.querySelector(`meta[property="${prop}"]`) || document.querySelector(`meta[name="${prop}"]`);
      if (!tag) {
        tag = document.createElement("meta");
        if (prop.startsWith("og:")) tag.setAttribute("property", prop);
        else tag.setAttribute("name", prop);
        document.head.appendChild(tag);
      }
      tag.content = val;
    });

    // JSON-LD Article + FAQPage schemas
    if (a) {
      const articleLD = {
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": a.seo_title,
        "description": a.meta_description,
        "datePublished": a.published_date,
        "dateModified": a.updated_date || a.published_date,
        "author": { "@type": "Organization", "name": "Casino Spotter" },
        "publisher": { "@type": "Organization", "name": "Casino Spotter" },
        "mainEntityOfPage": { "@type": "WebPage", "@id": window.location.href },
        "keywords": [t.name, t.category, ...a.related_slugs].join(", "),
      };
      const faqLD = {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": a.faqs.map((f) => ({
          "@type": "Question",
          "name": f.q,
          "acceptedAnswer": { "@type": "Answer", "text": f.a },
        })),
      };
      injectLD("technique-article-ld", articleLD);
      injectLD("technique-faq-ld", faqLD);
    }

    return () => {
      document.getElementById("technique-article-ld")?.remove();
      document.getElementById("technique-faq-ld")?.remove();
    };
  }, [t]);

  if (!t) return <div className="p-10 text-[var(--neon)] font-mono">Loading dossier...</div>;

  const a = t.article;

  return (
    <article className="max-w-3xl mx-auto px-6 md:px-12 py-12" data-testid="technique-detail">
      <Link to="/techniques" className="inline-flex items-center gap-2 text-xs uppercase tracking-widest mb-8 text-white/50 hover:text-[var(--neon)]" data-testid="back-to-techniques">
        <ArrowLeft className="w-3 h-3" /> All techniques
      </Link>

      <span className={`tag ${SEVERITY_COLOR[t.severity]}`} data-testid="technique-severity">{t.severity} severity</span>
      <h1 className="font-heading text-4xl md:text-5xl tracking-tighter mt-4 mb-3 leading-[1.05]" data-testid="technique-title">
        {a ? a.seo_title : t.name}
      </h1>
      <div className="flex flex-wrap items-center gap-4 text-[11px] uppercase tracking-widest text-white/50 font-mono mb-8">
        <span>{t.category}</span>
        {a && (
          <>
            <span className="flex items-center gap-1">
              <Clock className="w-3 h-3" /> {a.reading_time_min} min read
            </span>
            <span>updated {new Date(a.updated_date || a.published_date).toLocaleDateString()}</span>
          </>
        )}
      </div>

      {a ? (
        <>
          {/* Lead paragraph */}
          <p className="text-lg leading-relaxed text-white/85 font-mono mb-10 border-l-2 border-[var(--neon)]/60 pl-4" data-testid="technique-hero-subhead">
            {a.hero_subhead}
          </p>

          {/* Article sections */}
          <div data-testid="technique-article-sections">
            {a.sections.map((sec, i) => (
              <section key={i} className="mb-10" data-testid={`technique-section-${i}`}>
                <h2 className="font-heading text-2xl tracking-tight text-white mb-3 leading-tight">
                  <span className="text-[var(--neon)]">//</span> {sec.heading}
                </h2>
                <ArticleBody body={sec.body} />
              </section>
            ))}
          </div>

          {/* FAQ section — SEO featured-snippet bait */}
          <section className="mt-14 mb-10" data-testid="technique-faqs">
            <h2 className="font-heading text-2xl tracking-tight text-white mb-6 leading-tight">
              <span className="text-[var(--neon)]">//</span> Frequently asked questions
            </h2>
            <div className="space-y-6">
              {a.faqs.map((f, i) => (
                <div key={i} className="panel p-5" data-testid={`technique-faq-${i}`}>
                  <h3 className="font-heading text-base text-[var(--neon)] mb-2">{f.q}</h3>
                  <p className="text-sm font-mono text-white/80 leading-relaxed">{f.a}</p>
                </div>
              ))}
            </div>
          </section>

          {/* Related techniques */}
          {a.related_slugs.length > 0 && (
            <section className="mt-12" data-testid="technique-related">
              <h2 className="font-heading text-lg uppercase tracking-widest text-white/70 mb-3">
                Read next
              </h2>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                {a.related_slugs.map((s) => (
                  <Link
                    key={s}
                    to={`/techniques/${s}`}
                    className="panel p-4 hover:bg-white/[0.02] transition group"
                    data-testid={`technique-related-${s}`}
                  >
                    <p className="text-[10px] uppercase tracking-widest text-[var(--neon)] mb-1">technique</p>
                    <p className="font-heading text-sm text-white group-hover:text-[var(--neon)] transition">
                      {s.replace(/-/g, " ")}
                    </p>
                    <ChevronRight className="w-3 h-3 text-white/40 mt-2 group-hover:text-[var(--neon)] transition" />
                  </Link>
                ))}
              </div>
            </section>
          )}
        </>
      ) : (
        <>
          <Section title="Overview" body={t.description} />
          <Section title="How it works" body={t.how_it_works} />
          <Section title="How to spot it" body={t.how_to_spot} />
        </>
      )}

      {/* CTA after article */}
      <div className="panel p-6 mt-12 border-[var(--warn)]/40">
        <AlertTriangle className="w-5 h-5 text-[var(--warn)] mb-2" />
        <p className="text-sm font-mono text-white/85 mb-3">
          Think you&apos;ve seen this technique in action? Upload a clip and our forensic AI will confirm it frame-by-frame.
        </p>
        <div className="flex gap-3 flex-wrap">
          <Link to="/analyze" className="btn-neon text-xs" data-testid="technique-cta-analyze">RUN A FORENSIC SCAN &gt;_</Link>
          <Link to="/live" className="btn-ghost text-xs">Or try live capture</Link>
        </div>
      </div>

      <TrustedCasinoCTA source={`technique:${t.slug}`} headline={`CASINOS THAT DON'T DO ${t.name.toUpperCase()}`} />
    </article>
  );
}

function injectLD(id, payload) {
  let tag = document.getElementById(id);
  if (!tag) {
    tag = document.createElement("script");
    tag.type = "application/ld+json";
    tag.id = id;
    document.head.appendChild(tag);
  }
  tag.textContent = JSON.stringify(payload);
}

function ArticleBody({ body }) {
  // Parse [link text](path) markdown-style links and render the rest as plain mono prose.
  const linkRe = /\[([^\]]+)\]\(([^)]+)\)/g;
  const parts = [];
  let last = 0;
  let match;
  while ((match = linkRe.exec(body)) !== null) {
    if (match.index > last) parts.push({ type: "text", value: body.slice(last, match.index) });
    parts.push({ type: "link", label: match[1], href: match[2] });
    last = match.index + match[0].length;
  }
  if (last < body.length) parts.push({ type: "text", value: body.slice(last) });

  return (
    <p className="text-[15px] font-mono text-white/80 leading-[1.75] whitespace-pre-line">
      {parts.map((p, i) =>
        p.type === "link" ? (
          p.href.startsWith("http") ? (
            <a key={i} href={p.href} target="_blank" rel="noopener noreferrer" className="text-[var(--neon)] underline">{p.label}</a>
          ) : (
            <Link key={i} to={p.href} className="text-[var(--neon)] underline">{p.label}</Link>
          )
        ) : (
          <span key={i}>{p.value}</span>
        )
      )}
    </p>
  );
}

function Section({ title, body }) {
  return (
    <div className="mb-8">
      <h2 className="font-heading text-lg mb-2 text-[var(--neon)]">// {title}</h2>
      <p className="text-sm font-mono text-white/80 leading-relaxed whitespace-pre-line">{body}</p>
    </div>
  );
}
