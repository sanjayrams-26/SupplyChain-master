"""
test_suite.py — 10-question validation suite for the Supply Chain RAG system.

Each question has:
  - expected_docs   : which doc types must appear in sources ([] = refusal expected)
  - key_facts       : substrings that MUST appear in the answer (case-insensitive)
  - trap_facts      : substrings that must NOT appear (wrong answers / hallucinations)
  - notes           : what the question is testing and why it is tricky

Usage:
  python test_suite.py              # with retrieval debug output
  python test_suite.py --no-debug   # cleaner output
"""

import sys
import json
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv()

from src.generate import generate_answer
from src.store import get_chunk_count

# ── ANSI colours ──────────────────────────────────────────────────────────────
G  = "\033[92m"   # green
Y  = "\033[93m"   # yellow
R  = "\033[91m"   # red
B  = "\033[94m"   # blue
W  = "\033[0m"    # reset
BD = "\033[1m"    # bold

# ── Test questions ────────────────────────────────────────────────────────────
QUESTIONS = [
    {
        "id": 1,
        "label": "Highest-spend supplier + OTD",
        "question": (
            "Which supplier had the highest total spend in the quarter "
            "and what was their on-time delivery percentage?"
        ),
        "expected_docs": ["review"],
        "key_facts": ["shenzhen", "21.9", "79.5"],
        "trap_facts": [],
        "notes": (
            "Pure review question. "
            "Expected: Shenzhen Rui Electronics, ₹21.9 crore spend, 79.5% OTD."
        ),
    },
    {
        "id": 2,
        "label": "Line stoppages & downtime",
        "question": (
            "Describe all line stoppages and downtime incidents reported in the "
            "supply chain performance review — include number of events, total hours "
            "lost, financial impact, and the root cause breakdown."
        ),
        "expected_docs": ["review"],
        "key_facts": ["7", "41", "1.9"],
        "trap_facts": [],
        "notes": (
            "Review-only. "
            "Expected totals: 7 events, 41 hours, ₹1.9 crore. "
            "Breakdown: 4 events/22 hrs microcontrollers, 2 events/11 hrs Trident PCBs, "
            "1 event/5 hrs strike."
        ),
    },
    {
        "id": 3,
        "label": "Approval authority for ₹1.4 crore PO",
        "question": (
            "According to the procurement policy handbook, which authority must approve "
            "a purchase order worth ₹1.4 crore? Cite the exact section number."
        ),
        "expected_docs": ["policy"],
        "key_facts": ["chief operating officer", "section 3"],
        "trap_facts": ["chief financial officer", "cfo", "board"],
        "notes": (
            "Policy section 3. "
            "Must return Chief Operating Officer, NOT CFO or Board. "
            "A common confusion trap."
        ),
    },
    {
        "id": 4,
        "label": "Supplier classification criteria",
        "question": (
            "What are the supplier classification categories defined in the procurement "
            "policy handbook, and what are the qualifying criteria for each?"
        ),
        "expected_docs": ["policy"],
        "key_facts": ["section 2"],
        "trap_facts": [],
        "notes": (
            "Policy section 2. "
            "Should enumerate all tiers and their criteria without inventing new ones."
        ),
    },
    {
        "id": 5,
        "label": "Kaveri Metals — clause precision trap",
        "question": (
            "Kaveri Metals had an on-time delivery rate of 88.1% and a defect rate of "
            "1,150 PPM in the latest quarter. Which specific clauses of the procurement "
            "policy are triggered, and what are the exact financial consequences of each?"
        ),
        "expected_docs": ["review", "policy"],
        "key_facts": ["6.1", "6.3", "1,150", "88.1"],
        "trap_facts": ["clause 6.2"],
        "notes": (
            "PRECISION TRAP (cross-doc). "
            "88.1% OTD is above the 85% two-quarter threshold → clause 6.2 does NOT fire. "
            "Clause 6.1 fires (single-quarter miss <90%). "
            "Clause 6.3 fires (1,150 PPM > 500 PPM threshold). "
            "A system that includes 6.2 here is WRONG."
        ),
    },
    {
        "id": 6,
        "label": "Shenzhen Rui — two-quarter narrative trap",
        "question": (
            "Shenzhen Rui Electronics recorded 79.5% on-time delivery this quarter "
            "and 83.2% in the previous quarter. Based on the procurement policy, "
            "which clause is triggered and what are the required actions?"
        ),
        "expected_docs": ["review", "policy"],
        "key_facts": ["6.2", "79.5", "83.2"],
        "trap_facts": [],
        "notes": (
            "NARRATIVE RETRIEVAL TEST (cross-doc). "
            "79.5% and 83.2% are both below 85% for two consecutive quarters → clause 6.2 fires. "
            "83.2% appears only in narrative prose (not a table), testing deep retrieval. "
            "Expected: debit note + mandatory improvement plan."
        ),
    },
    {
        "id": 7,
        "label": "Safety stock formula — floor trap",
        "question": (
            "Calculate the required safety stock for an imported component sourced from "
            "Shenzhen Rui Electronics, which has a lead time of 46 days and is classified "
            "as a Critical-tier supplier. Show all steps and cite the relevant policy section."
        ),
        "expected_docs": ["policy"],
        "key_facts": ["30", "section 8"],
        "trap_facts": ["11.5", "11 days", "11.5 days"],
        "notes": (
            "FORMULA TRAP. "
            "Step 1: 46 × 0.25 = 11.5 days. "
            "Step 2: imported + Critical tier → minimum floor is 30 days. "
            "Correct answer: 30 days (floor overrides formula). "
            "A system that returns 11.5 has failed to apply the floor rule."
        ),
    },
    {
        "id": 8,
        "label": "Trident PCBs — clause 6.3 + late corrective action",
        "question": (
            "Trident Circuit Boards had a defect rate of 640 PPM. What are the exact "
            "consequences under clause 6.3 of the procurement policy? Also, what additional "
            "issue arose with their corrective action report submission?"
        ),
        "expected_docs": ["review", "policy"],
        "key_facts": ["640", "6.3", "120"],
        "trap_facts": [],
        "notes": (
            "Cross-doc: clause 6.3 consequence (₹120/unit + 100% inspection). "
            "Secondary check: Trident submitted the corrective action report 11 days late "
            "against the 10-day policy requirement."
        ),
    },
    {
        "id": 9,
        "label": "Band C/D standing — legitimate partial-refusal",
        "question": (
            "According to the procurement policy, what standing and escalation procedures "
            "apply to suppliers classified in band C or band D?"
        ),
        "expected_docs": ["policy"],
        "key_facts": ["band", "6.4"],
        "trap_facts": [],
        "notes": (
            "Policy sections 5, 6.4, escalation matrix. "
            "PARTIAL REFUSAL expected: the review provides per-dimension figures only, "
            "not composite scorecard totals, so the system cannot assign a real supplier "
            "to a band — it should answer the policy rules WITHOUT guessing which "
            "suppliers fall into each band."
        ),
    },
    {
        "id": 10,
        "label": "TRAP — approved supplier for gearbox castings",
        "question": (
            "Who is the approved supplier for gearbox castings at Meridian Components, "
            "and what is their current quality rating?"
        ),
        "expected_docs": [],
        "key_facts": ["not", "document"],
        "trap_facts": [],
        "notes": (
            "HALLUCINATION TRAP — 'gearbox castings' does not exist in either document. "
            "System must refuse clearly. Any named supplier or rating is a hallucination."
        ),
    },
]


# ── Helpers ───────────────────────────────────────────────────────────────────

def _check_key_facts(answer: str, key_facts: list[str]) -> tuple[bool, list[str]]:
    """Return (all_present, missing_list)."""
    lower = answer.lower()
    missing = [f for f in key_facts if f.lower() not in lower]
    return (len(missing) == 0, missing)


def _check_trap_facts(answer: str, trap_facts: list[str]) -> tuple[bool, list[str]]:
    """Return (no_traps_present, found_traps_list)."""
    lower = answer.lower()
    found = [f for f in trap_facts if f.lower() in lower]
    return (len(found) == 0, found)


def _verdict(
    coverage_ok: bool,
    key_ok: bool,
    trap_ok: bool,
    is_trap_q: bool,
    answer: str,
) -> tuple[str, str]:
    """Return (symbol, label)."""
    if is_trap_q:
        refuses = any(w in answer.lower() for w in ["not", "no information", "insufficient", "cannot", "don't"])
        if refuses:
            return f"{G}✅{W}", f"{G}TRAP CAUGHT{W}"
        else:
            return f"{R}❌{W}", f"{R}HALLUCINATION{W}"
    if coverage_ok and key_ok and trap_ok:
        return f"{G}✅{W}", f"{G}PASS{W}"
    if not trap_ok:
        return f"{R}❌{W}", f"{R}FAIL — wrong clause fired{W}"
    if not key_ok:
        return f"{Y}⚠️ {W}", f"{Y}PARTIAL — missing key facts{W}"
    return f"{Y}⚠️ {W}", f"{Y}PARTIAL — doc coverage gap{W}"


# ── Main runner ───────────────────────────────────────────────────────────────

def run_tests(debug: bool = False) -> list:
    count = get_chunk_count()
    if count == 0:
        print(f"{R}❌ No chunks in store. Index your documents first.{W}")
        sys.exit(1)

    print(f"\n{BD}{'═'*80}{W}")
    print(f"{BD}  SUPPLY CHAIN RAG — 10-QUESTION VALIDATION SUITE  ({count} passages indexed){W}")
    print(f"{BD}{'═'*80}{W}\n")

    results = []

    for q in QUESTIONS:
        is_trap = len(q["expected_docs"]) == 0
        print(f"\n{BD}{'─'*80}{W}")
        label_tag = f"{Y}[TRAP]{W}" if is_trap else f"{B}[Q{q['id']}]{W}"
        print(f"{label_tag} {BD}{q['label']}{W}")
        print(f"{B}Question:{W} {q['question']}")
        print(f"{B}Notes:{W}   {q['notes']}")

        start = time.time()
        try:
            result = generate_answer(q["question"], top_k=6, debug=debug)
            elapsed = round(time.time() - start, 2)

            answer = result["answer"]
            got_types = list({s["doc_type"] for s in result["sources"]})
            expected_set = set(q["expected_docs"])

            # Coverage check (skip for trap questions)
            coverage_ok = expected_set.issubset(set(got_types)) if expected_set else True

            # Key-fact check
            key_ok, missing_facts = _check_key_facts(answer, q["key_facts"])

            # Trap-fact check
            trap_ok, found_traps = _check_trap_facts(answer, q["trap_facts"])

            sym, verdict = _verdict(coverage_ok, key_ok, trap_ok, is_trap, answer)

            print(f"\n{BD}Answer:{W}\n{answer}\n")
            print(f"{BD}Sources{W} ({result['chunks_used']} passages, {elapsed}s):")
            for s in result["sources"]:
                icon = "🟦" if s["doc_type"] == "review" else "🟩"
                print(f"  {icon} {s['file_name']}  p.{s['page_number']}  [{s['doc_type']}]")
            print(f"🔎 Strategy: {result['strategy_used']}")

            if missing_facts:
                print(f"{Y}⚠️  Missing key facts:{W} {missing_facts}")
            if found_traps:
                print(f"{R}❌ Wrong clauses/facts found in answer:{W} {found_traps}")

            print(f"\n{sym} {verdict}")

            results.append({
                "id":              q["id"],
                "label":           q["label"],
                "question":        q["question"],
                "answer":          answer,
                "sources":         result["sources"],
                "strategy_used":   result["strategy_used"],
                "chunks_used":     result["chunks_used"],
                "expected_docs":   q["expected_docs"],
                "got_doc_types":   got_types,
                "coverage_pass":   coverage_ok,
                "key_facts_pass":  key_ok,
                "trap_facts_pass": trap_ok,
                "missing_facts":   missing_facts,
                "found_traps":     found_traps,
                "verdict":         verdict.replace("\033[92m","").replace("\033[93m","")
                                         .replace("\033[91m","").replace("\033[0m",""),
                "elapsed_s":       elapsed,
                "notes":           q["notes"],
            })

        except Exception as e:
            print(f"{R}❌ ERROR: {e}{W}")
            results.append({"id": q["id"], "label": q["label"], "error": str(e)})

    # ── Save JSON ─────────────────────────────────────────────────────────────
    out_path = Path("test_results.json")
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"\n\n{G}✅ Full results saved → {out_path}{W}")

    # ── Summary table ─────────────────────────────────────────────────────────
    print(f"\n{BD}{'═'*80}{W}")
    print(f"{BD}SUMMARY{W}")
    print(f"{BD}{'═'*80}{W}")
    print(f"{'Q':<3} {'Label':<38} {'Verdict':<28} {'Docs'}")
    print(f"{'─'*80}")

    passes = 0
    for r in results:
        if "error" in r:
            print(f"{r['id']:<3} {r['label']:<38} {R}ERROR{W}")
            continue
        sym = "✅" if "PASS" in r["verdict"] or "TRAP" in r["verdict"] else ("⚠️ " if "PARTIAL" in r["verdict"] else "❌")
        docs = "+".join(r["got_doc_types"]) or "—"
        verdict_short = r["verdict"][:26]
        print(f"{r['id']:<3} {r['label']:<38} {sym} {verdict_short:<24} {docs}")
        if "PASS" in r["verdict"] or "TRAP CAUGHT" in r["verdict"]:
            passes += 1

    total = len([r for r in results if "error" not in r])
    print(f"\n{BD}Score: {passes}/{total}{W}  ({round(100*passes/total if total else 0)}%)")
    print(f"{BD}{'═'*80}{W}\n")

    return results


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Supply Chain RAG — test suite")
    parser.add_argument("--debug", action="store_true", help="Print retrieval debug info per question")
    args = parser.parse_args()
    run_tests(debug=args.debug)
