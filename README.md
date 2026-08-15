# 🏭 Supply Chain Intelligence Assistant
### Meridian Components Pvt. Ltd.

> **An AI-powered Q&A tool that answers questions directly from your supply chain documents — every answer cited, nothing invented.**

---

## What This Does

Instead of manually searching through the Supply Chain Performance Review and Procurement Policy Handbook, team members can **ask questions in plain English** and get instant, cited answers.

**Example questions the system answers:**

| Question | What it retrieves |
|---|---|
| *"Which supplier had the highest spend this quarter?"* | Exact figure + OTD % from the Performance Review |
| *"What authority approves a ₹1.4 crore purchase order?"* | Section 3 of the Policy Handbook |
| *"Which clauses are triggered for Kaveri Metals?"* | Cross-references Review data against Policy clauses 6.1 & 6.3 |
| *"What is the safety stock for a 46-day imported part?"* | Applies the formula AND the mandatory minimum floor (30 days) from Section 8 |

**The system never guesses.** If the answer isn't in the documents, it says so explicitly.

---

## Business Value

- ⏱️ **Saves time** — no more manual document searches during reviews or audits
- ✅ **Traceable answers** — every fact is linked to its source document and page number
- 🚫 **Zero hallucination** — the AI is strictly grounded to your documents only
- 📋 **Cross-document intelligence** — automatically combines data from the Review and the Handbook to answer complex questions
- 🔒 **Data stays local** — documents never leave your machine; only the question text is sent to the AI

---

## Source Documents

The system works with two documents:

| Document | Purpose |
|---|---|
| `Supply_Chain_Performance_Review.pdf` | Quarterly supplier performance data — spend, OTD %, PPM defect rates, line stoppages |
| `Meridian_Procurement_Policy_Handbook_v4_2.pdf` | Procurement rules — approval authorities, penalty clauses, classification criteria, safety stock formula |

---

## How to Run It

### Prerequisites
- Python 3.10 or later
- A free [Groq API key](https://console.groq.com) (takes 2 minutes to create)

### Setup (one-time)

```bash
# 1. Clone the project
git clone <repo-url>
cd supply-chain-rag

# 2. Create a virtual environment
python3 -m venv venv
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Add your Groq API key
cp .env.example .env
# Open .env and set:  GROQ_API_KEY=gsk_...

# 5. Place your PDFs in the data/ folder
#    data/Supply_Chain_Performance_Review.pdf
#    data/Meridian_Procurement_Policy_Handbook_v4_2.pdf
```

### Launch the App

```bash
streamlit run app.py
```

Open **http://localhost:8501** in your browser.

**First use:** Click **⚡ Read & Index Documents** in the sidebar — takes about 60 seconds.  
**Next time:** The index is saved on disk — the app is ready instantly, no re-indexing needed.

---

## How It Works (Non-Technical Summary)

```
Your Question
     │
     ▼
┌─────────────────────────────────────────────────┐
│  1. SEARCH                                       │
│     Finds the most relevant passages from both  │
│     PDFs using semantic similarity               │
└─────────────────────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────────────────┐
│  2. ANSWER                                       │
│     Sends only those passages to the AI — which │
│     writes a cited answer using only that text   │
└─────────────────────────────────────────────────┘
     │
     ▼
Cited Answer  +  Source badges (document · page)
```

**Key guarantee:** The AI is explicitly instructed that it *cannot* use any knowledge outside the retrieved passages. If asked about something not in the documents, it refuses rather than guessing.

---

## Validation — 10-Question Test Suite

The system is validated against 10 structured test questions covering every major capability:

| # | Test | What it checks |
|---|---|---|
| 1 | Highest-spend supplier + OTD % | Correct figure retrieval from the Review |
| 2 | Line stoppages — events, hours, cost | Multi-value extraction from the Review |
| 3 | Approval authority for ₹1.4 Cr PO | Policy Section 3 — must say COO, not CFO |
| 4 | Supplier classification criteria | Policy Section 2 — all tiers enumerated |
| 5 | Kaveri Metals — clauses triggered | **Precision trap:** 6.1 and 6.3 fire; 6.2 must NOT (88.1% OTD is above the two-quarter threshold) |
| 6 | Shenzhen Rui — two consecutive quarters | Tests retrieval of narrative prose, not just tables |
| 7 | Safety stock for a 46-day imported part | **Formula trap:** raw formula gives 11.5 days; correct answer is 30 days (policy floor overrides) |
| 8 | Trident PCBs clause 6.3 + late report | Cost consequence + secondary compliance check |
| 9 | Band C/D escalation procedure | Policy rules retrieved; system refuses to assign suppliers to bands without composite scores |
| 10 | Gearbox castings approved supplier | **Hallucination trap:** topic doesn't exist in either document — system must refuse |

Run the test suite:
```bash
python test_suite.py
```

Results are saved to `test_results.json` with pass/fail verdicts per question.

---

## Technology Stack

| Component | Technology | Why |
|---|---|---|
| **AI Model** | Llama 3.3 70B via Groq | Fast, free, production-grade LLM |
| **Embeddings** | all-MiniLM-L6-v2 (local ONNX) | No API cost — runs entirely on-device |
| **Vector Store** | ChromaDB (on-disk) | Persistent index — no re-processing on restart |
| **PDF Extraction** | pypdf + pdfplumber | Handles text-layer PDFs with fallback |
| **Interface** | Streamlit | Clean browser UI, no frontend code needed |
| **API** | FastAPI | REST endpoints for programmatic access |

**Zero ongoing cost** — the embedding model runs locally; only LLM inference calls Groq (free tier).

---

## Project Structure

```
supply-chain-rag/
│
├── app.py                  ← Streamlit web interface
├── api.py                  ← FastAPI REST endpoints
├── test_suite.py           ← 10-question validation suite
├── requirements.txt
│
├── data/                   ← Place your PDFs here
├── chroma_store/           ← Auto-created vector index (persistent)
│
└── src/
    ├── extract.py          ← PDF → page text
    ├── chunk.py            ← Smart text splitting (1200-char, clause-aware)
    ├── embed.py            ← Local embedding model
    ├── store.py            ← ChromaDB operations
    ├── retrieve.py         ← Semantic search + cross-document logic
    ├── prompt.py           ← Grounding rules for the AI
    └── generate.py         ← Full RAG pipeline
```

---

## Chunking & Retrieval Design

Two technical choices that directly affect answer quality:

**Chunk size: 1,200 characters (not the standard 800)**  
Policy clauses (e.g. 6.1–6.6) include a heading, a trigger condition, and a cost consequence — often over 800 characters together. Splitting a clause in the middle means the AI sees the penalty without its trigger, or vice versa. Using 1,200 keeps each clause intact.

**Three retrieval modes (automatic)**

| Mode | When it activates | How it works |
|---|---|---|
| Standard search | General questions | Top-6 most relevant passages from both documents |
| Cross-document search | Question spans metrics AND policy keywords | Separate searches per document, then merged |
| Focused search | Safety stock / formula questions | Guarantees passages from both documents, regardless of similarity score |

---

## Frequently Asked Questions

**Can it answer questions about documents other than the two PDFs?**  
Yes — upload any PDF via the sidebar. The system treats it the same way.

**Does it retain conversation history?**  
Within a session, yes. History is cleared when the browser is closed or when "Clear conversation" is clicked in the sidebar. Nothing is stored externally.

**What happens if I ask something not in the documents?**  
The system explicitly refuses: *"The provided documents do not contain sufficient information to answer this question."* It will never invent an answer.

**Can multiple people use it at the same time?**  
Currently it runs as a single-user local app. For multi-user deployment, it can be hosted on Streamlit Cloud or as a Docker container — the vector index is already file-based and shareable.

---

*Built for Meridian Components Pvt. Ltd. — Supply Chain Analytics, 2025*
