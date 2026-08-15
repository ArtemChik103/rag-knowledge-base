import os
import shutil
import time
import mimetypes
from pathlib import Path
from typing import Optional, List, Dict, Any

# Ensure standard MIME types on all operating systems (Windows fix for module scripts)
mimetypes.init()
mimetypes.add_type("application/javascript", ".js")
mimetypes.add_type("application/javascript", ".mjs")
mimetypes.add_type("text/css", ".css")
mimetypes.add_type("application/json", ".json")

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field

from backend.config import settings
from backend.rag_engine import RAGEngine, QueryResponse
from backend.vector_store import VectorStore
from backend.generate_sample_pdf import generate_company_policy_pdf

app = FastAPI(
    title="RAG Knowledge Base API",
    description="Vector search & Q&A service over corporate documents and regulations",
    version="1.0.0",
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize vector store & RAG engine
vector_store = VectorStore()
rag_engine = RAGEngine(vector_store=vector_store)

# Request Models
class QueryRequest(BaseModel):
    query: str = Field(..., min_length=1, description="Question or search query")
    top_k: Optional[int] = Field(default=settings.TOP_K, ge=1, le=20)
    doc_id: Optional[str] = Field(default=None, description="Optional document ID filter")

class DocumentSummary(BaseModel):
    doc_id: str
    filename: str
    chunk_count: int
    total_pages: int
    total_chars: int

@app.get("/api/health")
def health_check():
    return {
        "status": "healthy",
        "timestamp": time.time(),
        "vector_store": "ready",
        "embedding_model": settings.EMBEDDING_MODEL,
    }

@app.get("/api/stats")
def get_stats():
    return vector_store.get_stats()

@app.get("/api/documents", response_model=List[DocumentSummary])
def list_documents():
    return vector_store.list_documents()

@app.get("/api/documents/{doc_id}/chunks")
def get_document_chunks(doc_id: str):
    chunks = vector_store.get_document_chunks(doc_id)
    if not chunks:
        raise HTTPException(status_code=404, detail="Document not found or has no indexed chunks.")
    return chunks

@app.post("/api/documents/upload")
async def upload_document(file: UploadFile = File(...)):
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename is empty.")

    original_filename = file.filename
    clean_filename = Path(original_filename).name
    save_path = settings.UPLOAD_DIR / clean_filename

    try:
        with open(save_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save uploaded file: {e}")

    try:
        ingestion_result = rag_engine.ingest_file(
            file_path=save_path,
            original_filename=original_filename
        )
        return {
            "message": "Document uploaded and indexed successfully.",
            "document": ingestion_result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process document: {e}")

@app.delete("/api/documents/{doc_id}")
def delete_document(doc_id: str):
    success = vector_store.delete_document(doc_id)
    if not success:
        raise HTTPException(status_code=500, detail=f"Failed to delete document with ID: {doc_id}")
    return {"message": "Document and associated vectors deleted successfully.", "doc_id": doc_id}

@app.post("/api/query", response_model=QueryResponse)
def run_query(request: QueryRequest):
    try:
        response = rag_engine.query(
            query_text=request.query,
            top_k=request.top_k or settings.TOP_K,
            doc_id=request.doc_id
        )
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Query failed: {e}")

@app.post("/api/sample-document")
def create_and_index_sample():
    sample_path = settings.UPLOAD_DIR / "sample_company_policy.pdf"
    generate_company_policy_pdf(sample_path)
    
    ingestion_result = rag_engine.ingest_file(
        file_path=sample_path,
        original_filename="sample_company_policy.pdf"
    )
    
    return {
        "message": "Sample company policy PDF created and indexed successfully.",
        "document": ingestion_result
    }

@app.post("/api/reset")
def reset_database():
    success = vector_store.reset()
    if not success:
        raise HTTPException(status_code=500, detail="Failed to reset vector database.")
    return {"message": "Vector database reset successfully."}

# Mount static frontend if available
frontend_dist = settings.BASE_DIR / "frontend" / "dist"
if frontend_dist.exists() and (frontend_dist / "index.html").exists():
    app.mount("/assets", StaticFiles(directory=str(frontend_dist / "assets"), html=False), name="static_assets")

    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        target = frontend_dist / full_path
        if target.exists() and target.is_file():
            # Explicit media type if needed
            mime_type, _ = mimetypes.guess_type(str(target))
            return FileResponse(target, media_type=mime_type)
        return FileResponse(frontend_dist / "index.html", media_type="text/html")

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    host = os.environ.get("HOST", "0.0.0.0")
    logger.info(f"Starting server on {host}:{port}")
    uvicorn.run("backend.main:app", host=host, port=port, reload=False)

