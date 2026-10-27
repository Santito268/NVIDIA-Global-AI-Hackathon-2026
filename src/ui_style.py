"""Look and feel of the Streamlit page: one stylesheet plus small HTML building blocks.

Every text that comes from a model or a web search is escaped before it goes into HTML.
HTML is written on one line on purpose: Streamlit's Markdown would turn indented or
blank-line-separated HTML into code blocks.
"""

from html import escape

CSS = """<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=Source+Serif+4:wght@400;600;700&display=swap');
:root{--sv-teal:#0F766E;--sv-teal-2:#14B8A6;--sv-navy:#0B1F3A;--sv-green:#16A34A;
--sv-text:#0F172A;--sv-muted:#64748B;--sv-border:#E2E8F0;--sv-card:#FFFFFF}
/* Streamlit sets its own font on every element; icons must keep their icon font. */
.stApp :is(p,li,label,h1,h2,h3,h4,span,div,button,textarea,
input):not([data-testid="stIconMaterial"]){font-family:'Inter',sans-serif}
.block-container{max-width:980px;padding-top:1.2rem;padding-bottom:3rem}
header[data-testid="stHeader"]{background:transparent}

@keyframes sv-fade-up{from{opacity:0;transform:translateY(18px)}to{opacity:1;transform:none}}
@keyframes sv-gradient{0%{background-position:0% 50%}50%{background-position:100% 50%}
100%{background-position:0% 50%}}
@keyframes sv-float{0%,100%{transform:translate(0,0)}50%{transform:translate(-30px,25px)}}
@keyframes sv-pulse{0%{box-shadow:0 0 0 0 rgba(20,184,166,.55)}
70%{box-shadow:0 0 0 12px rgba(20,184,166,0)}100%{box-shadow:0 0 0 0 rgba(20,184,166,0)}}
@keyframes sv-shine{from{background-position:-200% 0}to{background-position:200% 0}}

.sv-brand{font-weight:800;font-size:1.15rem;color:var(--sv-navy);letter-spacing:-.02em}
.st-key-lang{align-items:flex-end}
.sv-brand span{color:var(--sv-teal)}

.sv-hero{position:relative;overflow:hidden;border-radius:26px;padding:52px 44px 44px;
color:#fff;background:linear-gradient(120deg,#0B1F3A 0%,#0F766E 55%,#0B1F3A 100%);
background-size:220% 220%;animation:sv-gradient 14s ease infinite,sv-fade-up .7s ease both;
box-shadow:0 24px 60px -24px rgba(11,31,58,.6)}
.sv-hero::after{content:"";position:absolute;width:440px;height:440px;right:-140px;
top:-170px;background:radial-gradient(circle,rgba(94,234,212,.40),transparent 65%);
animation:sv-float 10s ease-in-out infinite;pointer-events:none}
.sv-pill{display:inline-flex;align-items:center;gap:8px;padding:6px 14px;border-radius:999px;
background:rgba(255,255,255,.12);border:1px solid rgba(255,255,255,.24);font-size:.8rem;
font-weight:500}
.sv-pill i{width:8px;height:8px;border-radius:50%;background:#5EEAD4;
animation:sv-pulse 2s infinite}
.sv-title{font-size:3.4rem;font-weight:800;letter-spacing:-.04em;line-height:1.05;
margin:20px 0 10px;background:linear-gradient(90deg,#FFFFFF,#99F6E4);
-webkit-background-clip:text;background-clip:text;color:transparent}
.sv-tagline{font-size:1.15rem;line-height:1.6;max-width:640px;color:rgba(255,255,255,.88)}
.sv-stats{display:flex;flex-wrap:wrap;gap:14px;margin-top:30px;position:relative;z-index:1}
.sv-stat{min-width:160px;padding:14px 18px;border-radius:16px;
background:rgba(255,255,255,.08);border:1px solid rgba(255,255,255,.18);
animation:sv-fade-up .7s ease both}
.sv-stat:nth-child(2){animation-delay:.12s}.sv-stat:nth-child(3){animation-delay:.24s}
.sv-stat b{display:block;font-size:1.7rem;font-weight:800;letter-spacing:-.02em}
.sv-stat span{font-size:.84rem;color:rgba(255,255,255,.78)}

.sv-section{font-size:1.4rem;font-weight:800;color:var(--sv-navy);letter-spacing:-.02em;
margin:38px 0 14px}
.sv-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:16px}
.sv-card{background:var(--sv-card);border:1px solid var(--sv-border);border-radius:18px;
padding:22px;box-shadow:0 1px 2px rgba(15,23,42,.04);animation:sv-fade-up .6s ease both;
transition:transform .25s ease,box-shadow .25s ease,border-color .25s ease}
.sv-card:hover{transform:translateY(-4px);border-color:#99F6E4;
box-shadow:0 16px 34px -14px rgba(15,118,110,.35)}
.sv-grid .sv-card:nth-child(2){animation-delay:.1s}
.sv-grid .sv-card:nth-child(3){animation-delay:.2s}
.sv-icon{width:46px;height:46px;border-radius:14px;display:grid;place-items:center;
font-size:1.35rem;background:linear-gradient(135deg,#CCFBF1,#E0F2FE);margin-bottom:14px}
.sv-num{font-size:.72rem;font-weight:700;letter-spacing:.1em;color:var(--sv-teal)}
.sv-card-title{font-weight:700;font-size:1.03rem;color:var(--sv-navy);margin:4px 0 6px}
.sv-card-text{color:var(--sv-muted);font-size:.92rem;line-height:1.55}

.sv-notes{display:grid;grid-template-columns:1fr 1fr;gap:14px;margin-top:18px}
.sv-note{display:flex;gap:12px;align-items:flex-start;background:var(--sv-card);
border:1px solid var(--sv-border);border-radius:16px;padding:16px 18px;font-size:.88rem;
line-height:1.5;color:var(--sv-muted);animation:sv-fade-up .6s ease both}
.sv-note b{display:block;color:var(--sv-navy);margin-bottom:2px}
.sv-note-icon{font-size:1.3rem}

.stTextArea [data-baseweb="textarea"]{border-radius:16px;border:1.5px solid var(--sv-border);
background:#fff;transition:border-color .2s ease,box-shadow .2s ease}
.stTextArea [data-baseweb="textarea"]:focus-within{border-color:var(--sv-teal-2);
box-shadow:0 0 0 4px rgba(20,184,166,.16)}
.stTextArea textarea{font-size:1rem;line-height:1.6;background:#fff}
.stButton>button,.stDownloadButton>button{border-radius:12px;font-weight:600;
transition:transform .15s ease,box-shadow .2s ease,border-color .2s ease,color .2s ease}
.stButton>button:hover,.stDownloadButton>button:hover{transform:translateY(-1px)}
[data-testid="stBaseButton-secondary"]{border-radius:999px !important;background:#fff;
border:1px solid var(--sv-border)}
[data-testid="stBaseButton-secondary"]:hover{border-color:var(--sv-teal-2);color:var(--sv-teal)}
[data-testid="stBaseButton-primary"]{background:linear-gradient(135deg,#0F766E,#14B8A6);
border:none;padding:.75rem 1.8rem;font-size:1.05rem;
box-shadow:0 12px 26px -12px rgba(15,118,110,.8)}
[data-testid="stBaseButton-primary"]:hover{filter:brightness(1.06);
box-shadow:0 16px 32px -12px rgba(15,118,110,.9)}

.sv-stepper{background:var(--sv-card);border:1px solid var(--sv-border);border-radius:20px;
padding:22px 24px;animation:sv-fade-up .4s ease both;
box-shadow:0 12px 30px -18px rgba(15,23,42,.25)}
.sv-stepper-title{font-weight:700;color:var(--sv-navy);margin-bottom:12px}
.sv-bar{height:6px;border-radius:999px;background:#EEF2F6;overflow:hidden;margin-bottom:14px}
.sv-bar div{height:100%;border-radius:999px;transition:width .6s ease;
background:linear-gradient(90deg,#0F766E,#14B8A6,#5EEAD4,#14B8A6);background-size:200% 100%;
animation:sv-shine 2s linear infinite}
.sv-step{display:flex;align-items:center;gap:14px;padding:9px 0;color:var(--sv-muted)}
.sv-dot{width:30px;height:30px;flex-shrink:0;border-radius:50%;display:grid;place-items:center;
font-weight:700;font-size:.82rem;background:#EEF2F6;color:var(--sv-muted)}
.sv-step.done .sv-dot{background:var(--sv-green);color:#fff}
.sv-step.active{color:var(--sv-navy);font-weight:600}
.sv-step.active .sv-dot{background:var(--sv-teal);color:#fff;animation:sv-pulse 1.6s infinite}
.sv-model{margin-left:auto;font-size:.72rem;font-weight:600;padding:3px 10px;border-radius:999px;
background:#F0FDFA;color:var(--sv-teal);border:1px solid #99F6E4;white-space:nowrap}
.sv-wait{font-size:.84rem;color:var(--sv-muted);margin-top:8px}

.sv-result-head{display:flex;align-items:center;flex-wrap:wrap;gap:12px;margin:34px 0 14px;
animation:sv-fade-up .5s ease both}
.sv-result-title{font-size:1.6rem;font-weight:800;color:var(--sv-navy);letter-spacing:-.02em}
.sv-badge{padding:6px 14px;border-radius:999px;font-weight:700;font-size:.82rem;color:#fff;
background:linear-gradient(135deg,#0F766E,#14B8A6)}
.sv-badge.derecho_de_peticion{background:linear-gradient(135deg,#1D4ED8,#3B82F6)}
.stTabs [role="tablist"]{gap:6px;background:#E6EDF3;padding:6px;border-radius:14px;
width:fit-content;max-width:100%;overflow-x:auto}
.stTabs [role="tablist"]::after,.stTabs .react-aria-SelectionIndicator{display:none}
.stTabs [data-testid="stTab"]{border-radius:10px;padding:8px 18px;height:auto;
transition:background .2s ease,box-shadow .2s ease}
.stTabs [data-testid="stTab"] p{font-weight:600;color:var(--sv-muted)}
.stTabs [data-testid="stTab"]:hover p{color:var(--sv-navy)}
.stTabs [data-testid="stTab"][aria-selected="true"]{background:#fff;
box-shadow:0 2px 8px rgba(15,23,42,.08)}
.stTabs [data-testid="stTab"][aria-selected="true"] p{color:var(--sv-teal)}
[data-testid="stTabPanel"]{animation:sv-fade-up .4s ease both}

.sv-reason{background:linear-gradient(135deg,#F0FDFA,#EFF6FF);border:1px solid #CCFBF1;
border-radius:16px;padding:16px 18px;color:var(--sv-navy);line-height:1.6;
animation:sv-fade-up .5s ease both}
.sv-reason b{color:var(--sv-teal)}
.sv-h{font-weight:700;color:var(--sv-navy);font-size:1.05rem;margin:24px 0 10px}
.sv-summary{background:var(--sv-card);border:1px solid var(--sv-border);border-radius:16px;
padding:16px 18px;line-height:1.65;color:var(--sv-text)}
.sv-points{display:grid;grid-template-columns:1fr 1fr;gap:12px}
.sv-point{display:flex;gap:10px;background:var(--sv-card);border:1px solid var(--sv-border);
border-radius:14px;padding:14px;line-height:1.5;animation:sv-fade-up .5s ease both}
.sv-point::before{content:"✓";flex-shrink:0;width:22px;height:22px;border-radius:50%;
display:grid;place-items:center;font-size:.75rem;font-weight:800;background:#DCFCE7;
color:#15803D}
.sv-chips{display:flex;flex-wrap:wrap;gap:8px}
.stApp .sv-chip{font-family:ui-monospace,Menlo,monospace;font-size:.78rem;padding:5px 10px;
border-radius:8px;background:#FEF3C7;color:#92400E;border:1px solid #FDE68A}
.sv-timeline{list-style:none;margin:0;padding:0}
.sv-timeline li{position:relative;padding:2px 0 18px 42px;line-height:1.55}
.sv-timeline li::after{content:"";position:absolute;left:13px;top:30px;bottom:0;width:2px;
background:#CCFBF1}
.sv-timeline li:last-child::after{display:none}
.sv-tl-num{position:absolute;left:0;top:0;width:28px;height:28px;border-radius:50%;
display:grid;place-items:center;font-size:.8rem;font-weight:700;color:#fff;
background:linear-gradient(135deg,#0F766E,#14B8A6)}

.st-key-paper{background:#fff;border:1px solid var(--sv-border);border-radius:8px;
padding:48px 56px;box-shadow:0 30px 60px -30px rgba(15,23,42,.35),0 2px 6px rgba(15,23,42,.05);
animation:sv-fade-up .5s ease both}
.st-key-paper .stMarkdown p,.st-key-paper .stMarkdown li{font-family:'Source Serif 4',Georgia,
serif;font-size:1.02rem;line-height:1.7}
.stApp .st-key-paper :is(h1,h2) span{font-family:inherit}
.stApp .st-key-paper h1{font-family:'Source Serif 4',Georgia,serif;font-size:1.5rem;
text-align:center;letter-spacing:.04em}
.stApp .st-key-paper h2{font-family:'Source Serif 4',Georgia,serif;font-size:1rem;
text-transform:uppercase;letter-spacing:.06em;color:var(--sv-navy);
border-bottom:1px solid var(--sv-border);padding-bottom:6px;margin-top:1.4rem}

.sv-source{background:var(--sv-card);border:1px solid var(--sv-border);border-radius:16px;
padding:16px 18px;margin-bottom:12px;animation:sv-fade-up .5s ease both}
.sv-source-title{font-weight:700;color:var(--sv-navy)}
.sv-cited{display:inline-block;margin-left:8px;padding:2px 10px;border-radius:999px;
font-size:.72rem;font-weight:700;background:#DCFCE7;color:#15803D}
.sv-source a{font-size:.8rem;color:var(--sv-teal);word-break:break-all}
.sv-snippet{margin-top:10px;padding-left:12px;border-left:3px solid #99F6E4;
color:var(--sv-muted);font-size:.88rem;line-height:1.6}
[data-testid="stMetric"]{background:var(--sv-card);border:1px solid var(--sv-border);
border-radius:16px;padding:16px 18px}

.sv-footer{margin-top:64px;padding:26px 0 8px;border-top:1px solid var(--sv-border);
text-align:center;color:var(--sv-muted);font-size:.84rem;line-height:1.7}
.sv-footer a{color:var(--sv-teal);font-weight:600;text-decoration:none}

@media (max-width:760px){.sv-hero{padding:34px 22px}.sv-title{font-size:2.5rem}
.sv-grid,.sv-notes,.sv-points{grid-template-columns:1fr}.st-key-paper{padding:26px 20px}}
@media (prefers-reduced-motion:reduce){*{animation:none !important;transition:none !important}}
</style>"""


def esc(text: str) -> str:
    """Escape model or web text for HTML; keep line breaks."""
    return escape(text, quote=False).replace("\n", "<br>")


def hero(title: str, tagline: str, badge: str, stats: list[tuple[str, str]]) -> str:
    items = "".join(
        f'<div class="sv-stat"><b>{v}</b><span>{label}</span></div>' for v, label in stats
    )
    return (
        f'<div class="sv-hero"><div class="sv-pill"><i></i>{badge}</div>'
        f'<div class="sv-title">{title}</div><div class="sv-tagline">{tagline}</div>'
        f'<div class="sv-stats">{items}</div></div>'
    )


def how_it_works(title: str, steps: list[tuple[str, str, str]]) -> str:
    cards = "".join(
        f'<div class="sv-card"><div class="sv-icon">{icon}</div><div class="sv-num">0{i}</div>'
        f'<div class="sv-card-title">{name}</div><div class="sv-card-text">{text}</div></div>'
        for i, (icon, name, text) in enumerate(steps, 1)
    )
    return f'<div class="sv-section">{title}</div><div class="sv-grid">{cards}</div>'


def notes(items: list[tuple[str, str, str]]) -> str:
    cards = "".join(
        f'<div class="sv-note"><span class="sv-note-icon">{icon}</span>'
        f"<div><b>{title}</b>{text}</div></div>"
        for icon, title, text in items
    )
    return f'<div class="sv-notes">{cards}</div>'


def stepper(title: str, steps: list[tuple[str, str]], current: int, wait: str) -> str:
    """Progress of the pipeline. `current` is the index of the running step (len = all done)."""
    rows = ""
    for i, (label, model) in enumerate(steps):
        state = "done" if i < current else "active" if i == current else ""
        mark = "✓" if i < current else str(i + 1)
        rows += (
            f'<div class="sv-step {state}"><div class="sv-dot">{mark}</div>{label}'
            f'<span class="sv-model">{model}</span></div>'
        )
    percent = min(100, round(100 * (current + 0.5) / len(steps)))
    return (
        f'<div class="sv-stepper"><div class="sv-stepper-title">{title}</div>'
        f'<div class="sv-bar"><div style="width:{percent}%"></div></div>{rows}'
        f'<div class="sv-wait">⏱ {wait}</div></div>'
    )


def result_head(title: str, document_type: str, document_name: str) -> str:
    return (
        f'<div class="sv-result-head"><span class="sv-result-title">{title}</span>'
        f'<span class="sv-badge {document_type}">{document_name}</span></div>'
    )


def explanation(
    labels: dict[str, str],
    document_name: str,
    reason: str,
    summary: str,
    key_points: list[str],
    to_fill: list[str],
    next_steps: list[str],
) -> str:
    """The explanation tab. `summary` and `key_points` come from the model: escaped here."""
    points = "".join(f'<div class="sv-point">{esc(p)}</div>' for p in key_points)
    chips = "".join(f'<span class="sv-chip">{esc(p)}</span>' for p in to_fill)
    steps = "".join(
        f'<li><span class="sv-tl-num">{i}</span>{esc(s)}</li>' for i, s in enumerate(next_steps, 1)
    )
    return (
        f'<div class="sv-reason"><b>{labels["document_type"]}: {esc(document_name)}.</b> '
        f"{esc(reason)}</div>"
        f'<div class="sv-h">{labels["summary"]}</div><div class="sv-summary">{esc(summary)}</div>'
        f'<div class="sv-h">{labels["key_points"]}</div><div class="sv-points">{points}</div>'
        f'<div class="sv-h">{labels["to_fill"]}</div><div class="sv-chips">{chips}</div>'
        f'<div class="sv-h">{labels["next_steps"]}</div><ol class="sv-timeline">{steps}</ol>'
    )


def source_card(title: str, url: str, snippet: str, cited_label: str | None) -> str:
    """One search result. Everything here comes from the web: escaped."""
    cited = f'<span class="sv-cited">✓ {cited_label}</span>' if cited_label else ""
    link = esc(url)
    if url.startswith(("https://", "http://")):  # never a javascript: link
        link = f'<a href="{escape(url, quote=True)}" target="_blank" rel="noopener">{link}</a>'
    return (
        f'<div class="sv-source"><div class="sv-source-title">{esc(title)}{cited}</div>{link}'
        f'<div class="sv-snippet">{esc(snippet)}</div></div>'
    )


def footer(text: str, code_label: str, repo_url: str) -> str:
    return (
        f'<div class="sv-footer">{text}<br>'
        f'<a href="{repo_url}" target="_blank" rel="noopener">{code_label} ↗</a>'
        " · Built with NVIDIA Nemotron on Nebius Token Factory</div>"
    )
