from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
import uuid
import os
from typing import Optional
from pathlib import Path

from .schemas import ChatRequest, ChatResponse, IngestRequest, IngestResponse, HealthResponse
from .db import get_db, init_db, save_message, get_last_response_id
from .rag_indexer import search_rag, ingest_files
from .ai_adapter import get_adapter

app = FastAPI(title="Emotional Reflection Assistant", version="1.0.0")

# -------------------- CORS --------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------------------- PATHS --------------------
BASE_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = BASE_DIR / "frontend"

# -------------------- STARTUP --------------------
@app.on_event("startup")
async def startup_event():
    init_db()
    try:
        from .rag_indexer import get_collection
        collection = get_collection()
        if collection.count() == 0:
            print("RAG collection is empty, ingesting default files...")
            ingest_files()
    except Exception as e:
        print(f"Warning: Could not auto-ingest RAG files: {e}")

# -------------------- HEALTH --------------------
@app.get("/health", response_model=HealthResponse)
async def health_check():
    try:
        adapter = get_adapter()
        return {
            "status": "ok",
            "provider": "yandex",
            "model": adapter.model.split("/")[-1],
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))

# -------------------- CHAT --------------------
@app.post("/v1/chat", response_model=ChatResponse)
async def chat(request: ChatRequest, db: Session = Depends(get_db)):
    try:
        session_id = request.session_id or str(uuid.uuid4())

        save_message(db, session_id, "user", request.message)

        rag_chunks = search_rag(
            request.message,
            top_k=int(os.getenv("RAG_TOP_K", 3))
        )

        adapter = get_adapter()
        previous_response_id = get_last_response_id(db, session_id)

        result = adapter.send_message(
            message=request.message,
            rag_chunks=rag_chunks,
            previous_response_id=previous_response_id,
        )

        save_message(
            db,
            session_id,
            "assistant",
            result["response_text"],
            result.get("response_id"),
        )

        return ChatResponse(
            session_id=session_id,
            reply=result["response_text"],
            meta={
                "rag_hits": len(rag_chunks),
                "model": adapter.model.split("/")[-1],
                "tokens": result.get("tokens"),
            },
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

# -------------------- RAG INGEST --------------------
@app.post("/v1/rag/ingest", response_model=IngestResponse)
async def ingest_rag(request: Optional[IngestRequest] = None):
    try:
        file_paths = request.files if request and request.files else None
        indexed_count = ingest_files(file_paths)
        return IngestResponse(indexed=indexed_count)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# -------------------- FRONTEND --------------------
app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")

@app.get("/")
async def serve_frontend():
    return FileResponse(FRONTEND_DIR / "index.html")

# -------------------- LOCAL RUN --------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
