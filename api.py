"""
api.py — Optional FastAPI backend (Bonus).

Endpoints:
  POST /index   — upload PDFs, index them, return chunk stats
  POST /ask     — ask a question, get answer + sources
  GET  /stats   — collection statistics

Test via /docs (Swagger UI) before wiring Streamlit to call these.

Run with:
  uvicorn api:app --reload --port 8000
"""

import os
import sys
from pathlib import Path
from typing import List, Optional

sys.path.insert(0, str(Path(__file__).parent))

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(
    title="Supply Chain RAG API",
    description="Retrieval-Augmented Generation over Supply Chain PDFs — Meridian Components Pvt. Ltd.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Request / Response models ────────────────────────────────────────────────

class AskRequest(BaseModel):
    question: str
    top_k: int = 6
    debug: bool = False


class SourceItem(BaseModel):
    file_name: str
    page_number: int
    doc_type: str


class AskResponse(BaseModel):
    answer: str
    sources: List[SourceItem]
    strategy_used: str
    chunks_used: int


class IndexResponse(BaseModel):
    files_processed: int
    total_chunks: int
    chunks_per_file: dict


class StatsResponse(BaseModel):
    collection_name: str
    chunk_count: int
    embedding_model: str
    generation_model: str
    chroma_path: str


# ── Startup check ─────────────────────────────────────────────────────────────
@app.on_event("startup")
async def startup_event():
    from src.embed import startup_check, _get_model
    startup_check()
    _get_model()  # pre-load embedding model at boot so first request is fast


# ── POST /index ───────────────────────────────────────────────────────────────
@app.post("/index", response_model=IndexResponse, summary="Index uploaded PDFs")
async def index_documents(files: List[UploadFile] = File(...)):
    """
    Upload one or more PDF files and index them into ChromaDB.

    Returns the number of files processed, total chunks, and chunks per file.
    """
    if not files:
        raise HTTPException(status_code=400, detail="No files uploaded.")

    data_dir = Path("data")
    data_dir.mkdir(exist_ok=True)

    saved_paths = []
    for uf in files:
        if not uf.filename.endswith(".pdf"):
            raise HTTPException(status_code=400, detail=f"Only PDF files accepted, got: {uf.filename}")
        save_path = data_dir / uf.filename
        content = await uf.read()
        save_path.write_bytes(content)
        saved_paths.append(str(save_path))

    try:
        from src.extract import extract_pages, print_extraction_summary
        from src.chunk import chunk_pages, print_chunk_summary, verify_integrity
        from src.store import add_chunks
        from collections import Counter

        all_pages = []
        for pdf_path in saved_paths:
            pages = extract_pages(pdf_path)
            print_extraction_summary(pages)
            all_pages.extend(pages)

        chunks = chunk_pages(all_pages)
        print_chunk_summary(chunks)
        verify_integrity(chunks)

        total = add_chunks(chunks)
        counts = dict(Counter(c["file_name"] for c in chunks))

        return IndexResponse(
            files_processed=len(saved_paths),
            total_chunks=total,
            chunks_per_file=counts,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── POST /ask ──────────────────────────────────────────────────────────────────
@app.post("/ask", response_model=AskResponse, summary="Ask a supply chain question")
async def ask_question(request: AskRequest):
    """
    Ask a question; retrieves context from ChromaDB and generates a grounded answer.
    """
    if not request.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    try:
        from src.store import get_chunk_count
        if get_chunk_count() == 0:
            raise HTTPException(
                status_code=409,
                detail="No documents indexed yet. Call POST /index first.",
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    try:
        from src.generate import generate_answer
        result = generate_answer(
            question=request.question,
            top_k=request.top_k,
            debug=request.debug,
        )
        return AskResponse(
            answer=result["answer"],
            sources=[SourceItem(**s) for s in result["sources"]],
            strategy_used=result["strategy_used"],
            chunks_used=result["chunks_used"],
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── GET /stats ─────────────────────────────────────────────────────────────────
@app.get("/stats", response_model=StatsResponse, summary="Collection statistics")
async def get_stats():
    """Return metadata about the current ChromaDB collection."""
    try:
        from src.store import get_stats as _get_stats
        return StatsResponse(**_get_stats())
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)
