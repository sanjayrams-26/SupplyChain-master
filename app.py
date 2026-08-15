"""
app.py — Streamlit interface for the Supply Chain RAG System.

UI components:
  • Sidebar : stats, PDF uploader / pre-load, "Index Documents" button
  • Main    : question input (disabled until indexed), answer + citations,
              running Q&A history
"""

import sys
import os
from pathlib import Path

# Ensure project root is on the path
sys.path.insert(0, str(Path(__file__).parent))

import streamlit as st
from dotenv import load_dotenv

load_dotenv()

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Supply Chain Assistant | Meridian Components",
    page_icon="🏭",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Inline CSS ───────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&family=Outfit:wght@300;400;600;700;800&display=swap');

html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

/* ── Background ── */
.stApp {
    background: #060912;
    background-image:
        radial-gradient(ellipse 80% 50% at 20% -10%, rgba(99,60,255,0.18) 0%, transparent 60%),
        radial-gradient(ellipse 60% 40% at 80% 100%, rgba(0,212,255,0.12) 0%, transparent 60%);
    color: #e2e8f0; min-height: 100vh;
}

/* ── Sidebar ── */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0d1424 0%, #0a0f1e 100%) !important;
    border-right: 1px solid rgba(99,60,255,0.2) !important;
    box-shadow: 4px 0 24px rgba(0,0,0,0.4) !important;
}

/* ── Stat blocks ── */
.stat-block {
    flex: 1; text-align: center; padding: 0.85rem 0.5rem;
    background: rgba(99,60,255,0.08);
    border: 1px solid rgba(99,60,255,0.2); border-radius: 12px;
}
.stat-val {
    font-family: 'Outfit', sans-serif; font-size: 1.8rem; font-weight: 800;
    background: linear-gradient(135deg, #818cf8, #38bdf8);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    background-clip: text; line-height: 1;
}
.stat-lbl {
    font-size: 0.65rem; color: #64748b;
    text-transform: uppercase; letter-spacing: 0.1em; margin-top: 4px;
}

/* ── Glass cards ── */
.rag-card {
    background: linear-gradient(135deg, rgba(255,255,255,0.04), rgba(255,255,255,0.02));
    border: 1px solid rgba(255,255,255,0.08); border-radius: 18px;
    padding: 1.4rem 1.6rem; margin-bottom: 1.2rem;
    box-shadow: 0 8px 32px rgba(0,0,0,0.3), inset 0 1px 0 rgba(255,255,255,0.06);
    position: relative; overflow: hidden;
    transition: border-color 0.3s, box-shadow 0.3s;
}
.rag-card::before {
    content: ''; position: absolute; top: 0; left: 0; right: 0; height: 1px;
    background: linear-gradient(90deg, transparent, rgba(99,60,255,0.5), rgba(0,212,255,0.5), transparent);
}
.rag-card:hover {
    border-color: rgba(99,60,255,0.25);
    box-shadow: 0 12px 40px rgba(0,0,0,0.4), 0 0 0 1px rgba(99,60,255,0.1);
}
.rag-card-header {
    font-size: 0.68rem; font-weight: 700; letter-spacing: 0.14em;
    text-transform: uppercase; color: #475569; margin-bottom: 0.7rem;
}
.rag-answer { font-size: 0.97rem; line-height: 1.85; color: #cbd5e1; }

/* question strip */
.history-q {
    font-family: 'Outfit', sans-serif; font-size: 1.05rem; font-weight: 600;
    color: #c4b5fd; margin: 0; line-height: 1.4;
}

/* ── Source badges ── */
.src-badge-review {
    display: inline-block;
    background: rgba(56,139,253,0.12); border: 1px solid rgba(56,139,253,0.35);
    color: #93c5fd; border-radius: 8px; padding: 4px 10px;
    font-size: 0.72rem; font-family: 'JetBrains Mono', monospace; margin: 3px;
    transition: all 0.2s;
}
.src-badge-policy {
    display: inline-block;
    background: rgba(52,211,153,0.1); border: 1px solid rgba(52,211,153,0.3);
    color: #6ee7b7; border-radius: 8px; padding: 4px 10px;
    font-size: 0.72rem; font-family: 'JetBrains Mono', monospace; margin: 3px;
    transition: all 0.2s;
}
.strategy-tag {
    font-size: 0.68rem; color: #94a3b8; font-family: 'JetBrains Mono', monospace;
    background: rgba(255,255,255,0.04); border: 1px solid rgba(255,255,255,0.08);
    border-radius: 20px; padding: 4px 12px; display: inline-block; margin-top: 8px;
}

/* ── Textarea ── */
.stTextArea textarea {
    background: rgba(255,255,255,0.04) !important; color: #e2e8f0 !important;
    border: 1px solid rgba(99,60,255,0.25) !important; border-radius: 14px !important;
    font-family: 'Inter', sans-serif !important; font-size: 0.95rem !important;
    padding: 0.85rem 1rem !important; resize: none !important;
    transition: border-color 0.3s, box-shadow 0.3s !important;
}
.stTextArea textarea:focus {
    border-color: rgba(99,60,255,0.6) !important;
    box-shadow: 0 0 0 3px rgba(99,60,255,0.12), 0 0 20px rgba(99,60,255,0.1) !important;
}

/* ── Buttons ── */
.stButton button {
    background: linear-gradient(135deg, #7c3aed 0%, #4f46e5 60%, #0ea5e9 100%) !important;
    color: white !important; border: none !important; border-radius: 12px !important;
    font-family: 'Outfit', sans-serif !important; font-weight: 600 !important;
    font-size: 0.9rem !important; padding: 0.6rem 1.8rem !important;
    letter-spacing: 0.02em !important; transition: all 0.25s ease !important;
    box-shadow: 0 4px 16px rgba(99,60,255,0.35) !important;
}
.stButton button:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 8px 28px rgba(99,60,255,0.5) !important;
    filter: brightness(1.1) !important;
}

/* ── Empty state ── */
.empty-state {
    text-align: center; padding: 4rem 2rem;
    background: rgba(255,255,255,0.02);
    border: 1px dashed rgba(99,60,255,0.2); border-radius: 20px;
}

hr { border-color: rgba(255,255,255,0.06) !important; margin: 1.2rem 0 !important; }
::-webkit-scrollbar { width: 5px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: rgba(99,60,255,0.3); border-radius: 10px; }

/* ── Sidebar brand block ── */
.sidebar-brand {
    background: linear-gradient(135deg, rgba(99,60,255,0.12), rgba(0,212,255,0.08));
    border: 1px solid rgba(99,60,255,0.25); border-radius: 14px;
    padding: 1rem 1.2rem; margin-bottom: 1rem;
    text-align: center; position: relative; overflow: hidden;
}
.sidebar-brand::before {
    content: ''; position: absolute; top: 0; left: 0; right: 0; height: 2px;
    background: linear-gradient(90deg, #7c3aed, #38bdf8);
}
.sidebar-brand-title {
    font-family: 'Outfit', sans-serif; font-size: 1.05rem; font-weight: 700;
    background: linear-gradient(135deg, #a78bfa, #38bdf8);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    background-clip: text;
}
.sidebar-brand-sub { font-size: 0.7rem; color: #64748b; margin-top: 3px; }

/* ── Sample question chips ── */
.sample-q {
    display: block; background: rgba(99,60,255,0.07);
    border: 1px solid rgba(99,60,255,0.18); border-radius: 10px;
    padding: 0.55rem 0.9rem; margin: 0.35rem 0;
    color: #94a3b8; font-size: 0.82rem; line-height: 1.4;
    transition: border-color 0.2s, background 0.2s;
}
.sample-q:hover {
    border-color: rgba(99,60,255,0.4);
    background: rgba(99,60,255,0.12); color: #c4b5fd;
}
</style>
""", unsafe_allow_html=True)




# ── Session state defaults ───────────────────────────────────────────────────
if "indexed" not in st.session_state:
    st.session_state.indexed = False
if "history" not in st.session_state:
    st.session_state.history = []  # list of {question, answer, sources, strategy}
if "chunk_counts" not in st.session_state:
    st.session_state.chunk_counts = {}
if "debug_mode" not in st.session_state:
    st.session_state.debug_mode = False


# ── Helpers ──────────────────────────────────────────────────────────────────

@st.cache_resource
def _api_startup():
    """Run API startup check once per session."""
    from src.embed import startup_check
    startup_check()


def _do_index(pdf_paths: list[str]):
    """Full ingestion pipeline: extract → chunk → embed → store."""
    from src.extract import extract_pages, print_extraction_summary
    from src.chunk import chunk_pages, print_chunk_summary, verify_integrity
    from src.store import add_chunks, get_chunk_count

    all_pages = []
    for pdf_path in pdf_paths:
        pages = extract_pages(pdf_path)
        print_extraction_summary(pages)
        all_pages.extend(pages)

    chunks = chunk_pages(all_pages)
    print_chunk_summary(chunks)
    verify_integrity(chunks)

    total = add_chunks(chunks)

    from collections import Counter
    counts = Counter(c["file_name"] for c in chunks)
    return total, dict(counts)


# ── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div class="sidebar-brand">
        <div class="sidebar-brand-title">🏭 Supply Chain Assistant</div>
        <div class="sidebar-brand-sub">Meridian Components Pvt. Ltd.</div>
    </div>
    """, unsafe_allow_html=True)

    # API check
    try:
        _api_startup()
        st.success("✅ Connected and ready")
    except Exception as e:
        st.error(f"❌ Couldn't start up: {e}")
        st.stop()

    # Stats
    if st.session_state.indexed:
        try:
            from src.store import get_stats
            stats = get_stats()
            col1, col2 = st.columns(2)
            with col1:
                st.markdown(f'<div class="stat-block"><div class="stat-val">{stats["chunk_count"]}</div><div class="stat-lbl">Passages</div></div>', unsafe_allow_html=True)
            with col2:
                st.markdown(f'<div class="stat-block"><div class="stat-val">{len(st.session_state.history)}</div><div class="stat-lbl">Asked</div></div>', unsafe_allow_html=True)
            st.markdown(f"<small style='color:#475569'>🤖 {stats['embedding_model']}</small>", unsafe_allow_html=True)
            st.markdown(f"<small style='color:#475569'>💬 {stats['generation_model']}</small>", unsafe_allow_html=True)
        except Exception:
            pass
        st.markdown("---")

    # Debug mode
    st.session_state.debug_mode = st.checkbox("🔍 Show retrieval details in console", value=False)

    # Clear conversation history
    if st.session_state.get("history"):
        if st.button("🗑️ Clear conversation", use_container_width=True):
            st.session_state.history = []
            st.rerun()

    st.markdown("---")


    # ── PDF source selection ─────────────────────────────────────────────────
    st.markdown("### 📂 Your Documents")
    source_mode = st.radio(
        "Where are your PDFs?",
        ["Already in the data/ folder", "I'll upload them now"],
        label_visibility="collapsed",
    )

    uploaded_files = []
    data_pdfs = []

    if source_mode == "I'll upload them now":
        uploaded_files = st.file_uploader(
            "Drop your PDFs here",
            type="pdf",
            accept_multiple_files=True,
            help="Upload your Supply Chain Performance Review and Procurement Policy Handbook PDFs.",
        )
    else:
        data_dir = Path("data")
        data_pdfs = sorted(data_dir.glob("*.pdf")) if data_dir.exists() else []
        if data_pdfs:
            st.success(f"Found {len(data_pdfs)} PDF(s) ready to go")
            for p in data_pdfs:
                st.markdown(f"  • `{p.name}`")
        else:
            st.warning("No PDFs found in data/. Drop them in the data/ folder or upload them above.")

    # ── Index button ─────────────────────────────────────────────────────────
    st.markdown("---")
    can_index = bool(data_pdfs or uploaded_files)

    if st.button("⚡ Read & Index Documents", disabled=not can_index, use_container_width=True):
        with st.spinner("Reading your documents — this usually takes under a minute …"):
            try:
                pdf_paths = []

                # Save uploaded files to a temp location inside data/
                if uploaded_files:
                    os.makedirs("data", exist_ok=True)
                    for uf in uploaded_files:
                        save_path = Path("data") / uf.name
                        with open(save_path, "wb") as f:
                            f.write(uf.getbuffer())
                        pdf_paths.append(str(save_path))
                else:
                    pdf_paths = [str(p) for p in data_pdfs]

                total, counts = _do_index(pdf_paths)
                st.session_state.indexed = True
                st.session_state.chunk_counts = counts
                st.success(f"✅ Done! Read {total} passages across your documents.")
                for fname, cnt in counts.items():
                    st.info(f"  • {fname}: {cnt} passages")
                st.rerun()

            except Exception as e:
                st.error(f"Something went wrong while reading your documents: {e}")


# ── Main content ─────────────────────────────────────────────────────────────
st.markdown("""
<p class="hero-title">Ask Your Supply Chain Documents</p>
<p class="hero-sub">Every answer comes directly from your Performance Review and Procurement Policy Handbook — nothing made up, everything cited.</p>
""", unsafe_allow_html=True)

if not st.session_state.indexed:
    st.markdown("""
    <div class="rag-card">
        <div class="rag-card-header">✦ How to get started</div>
        <ol style="color:#94a3b8; line-height:2.2; margin: 0; padding-left: 1.2rem;">
            <li>Put your PDFs in the <code style="background:rgba(99,60,255,0.15); color:#a78bfa; padding:2px 6px; border-radius:5px;">data/</code> folder, or upload them via the sidebar.</li>
            <li>Hit <strong style="color:#c4b5fd;">⚡ Read &amp; Index Documents</strong> — it only takes a moment.</li>
            <li>Ask anything — get a cited, grounded answer instantly.</li>
        </ol>
    </div>
    """, unsafe_allow_html=True)

    # Check if already indexed from a previous session (restart test)
    try:
        from src.store import get_chunk_count
        count = get_chunk_count()
        if count > 0:
            st.info(f"🔄 Found an existing index with {count} passages — you're good to go, no re-indexing needed.")
            st.session_state.indexed = True
            st.rerun()
    except Exception:
        pass

else:
    # ── Question input ───────────────────────────────────────────────────────
    with st.form("question_form", clear_on_submit=True):
        question = st.text_area(
            "Your question",
            placeholder="e.g. Which supplier had the highest spend, and what was their on-time delivery rate?",
            height=90,
            label_visibility="collapsed",
        )
        submitted = st.form_submit_button("🔍 Find Answer", use_container_width=False)

    # Sample questions panel
    with st.expander("💡 Not sure what to ask? Try one of these", expanded=False):
        st.markdown("""
        <div class="sample-q">Which supplier had the highest spend this quarter and what was their on-time delivery rate?</div>
        <div class="sample-q">What approval authority is needed for a purchase order of ₹1.4 crore? (Policy section 3)</div>
        <div class="sample-q">What are the supplier classification categories and their qualifying criteria?</div>
        <div class="sample-q">Kaveri Metals had 88.1% OTD and 1,150 PPM — which policy clauses are triggered and what do they cost?</div>
        <div class="sample-q">How many line stoppages occurred and what was the total downtime in hours and cost?</div>
        <div class="sample-q">What is the safety stock for an imported part with a 46-day lead time from a Critical-tier supplier?</div>
        <div class="sample-q">What happens when a supplier's defect rate exceeds 500 PPM under clause 6.3?</div>
        <div class="sample-q">What standing and escalation applies to suppliers in band C or band D?</div>
        """, unsafe_allow_html=True)


    if submitted and question.strip():
        with st.spinner("Searching your documents and writing an answer …"):
            try:
                from src.generate import generate_answer
                result = generate_answer(
                    question=question.strip(),
                    top_k=6,
                    debug=st.session_state.debug_mode,
                )
                # Prepend to history (newest first)
                st.session_state.history.insert(0, {
                    "question": question.strip(),
                    **result,
                })
            except Exception as e:
                st.error(f"Couldn't generate an answer: {e}")

    # ── Answer history ───────────────────────────────────────────────────────
    if st.session_state.history:
        for idx, item in enumerate(st.session_state.history):
            with st.container():
                # Question
                st.markdown(
                    f'<div class="rag-card" style="background:linear-gradient(135deg,rgba(99,60,255,0.08),rgba(56,189,248,0.04));border-color:rgba(99,60,255,0.22);">'
                    f'<div class="rag-card-header" style="color:#7c3aed;">Question #{len(st.session_state.history) - idx}</div>'
                    f'<div class="history-q">❓ {item["question"]}</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

                # Answer
                st.markdown(
                    f'<div class="rag-card" style="border-color:rgba(56,189,248,0.18);">'
                    f'<div class="rag-card-header" style="color:#0ea5e9;">✦ Answer</div>'
                    f'<div class="rag-answer">{item["answer"]}</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

                # Sources grouped by document
                review_srcs = [s for s in item["sources"] if s["doc_type"] == "review"]
                policy_srcs = [s for s in item["sources"] if s["doc_type"] == "policy"]

                src_html = '<div class="rag-card" style="border-color:rgba(52,211,153,0.15);"><div class="rag-card-header" style="color:#10b981;">📎 Sources</div>'

                if review_srcs:
                    src_html += "<div style='font-size:0.75rem;font-weight:600;color:#93c5fd;margin-bottom:6px;letter-spacing:0.05em;'>📊 PERFORMANCE REVIEW</div>"
                    for s in review_srcs:
                        src_html += f'<span class="src-badge-review">📄 {s["file_name"]} &nbsp;·&nbsp; p.{s["page_number"]}</span>'
                    src_html += "<br><br>"

                if policy_srcs:
                    src_html += "<div style='font-size:0.75rem;font-weight:600;color:#6ee7b7;margin-bottom:6px;letter-spacing:0.05em;'>📋 PROCUREMENT POLICY</div>"
                    for s in policy_srcs:
                        src_html += f'<span class="src-badge-policy">📄 {s["file_name"]} &nbsp;·&nbsp; p.{s["page_number"]}</span>'

                # Strategy tag
                src_html += f'<br><br><span class="strategy-tag">🔎 {item.get("strategy_used", "")}</span>'
                src_html += "</div>"

                st.markdown(src_html, unsafe_allow_html=True)

                if idx < len(st.session_state.history) - 1:
                    st.markdown("---")
    else:
        st.markdown("""
        <div style="text-align:center; padding: 4rem 2rem;
                    background: rgba(255,255,255,0.015);
                    border: 1px dashed rgba(99,60,255,0.2);
                    border-radius: 20px; margin-top: 1rem;">
            <div style="font-size:3.5rem; margin-bottom:1rem;">💬</div>
            <div style="font-family:'Outfit',sans-serif; font-size:1.1rem; font-weight:600; color:#475569;">
                Your answers will appear here.
            </div>
            <div style="font-size:0.85rem; color:#334155; margin-top:0.4rem;">
                Ask anything about your documents above — every answer is cited.
            </div>
        </div>
        """, unsafe_allow_html=True)
