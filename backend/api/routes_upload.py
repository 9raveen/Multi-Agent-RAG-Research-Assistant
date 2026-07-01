# routes_upload.py
# POST /upload — accepts a PDF, runs it through the Phase 1 ingestion pipeline.

import sys, os, shutil, tempfile
sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))

from fastapi import APIRouter, UploadFile, File, HTTPException

from api.schemas import UploadResponse
from ingestion.pdf_parser import parse_pdf
from ingestion.chunker import chunk_pages
from ingestion.embedder import embed_and_store

router = APIRouter()


@router.post("/upload", response_model=UploadResponse)
async def upload_pdf(file: UploadFile = File(...)):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")

    # Save the uploaded file to a temp path — parse_pdf() expects a filesystem
    # path (fitz.open), not an in-memory stream, so we write it to disk first.
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = tmp.name

    try:
        pages = parse_pdf(tmp_path)
        if not pages:
            raise HTTPException(status_code=422, detail="No extractable content found in PDF.")

        chunks = chunk_pages(pages)
        tables_detected = sum(len(p.get("tables", [])) for p in pages)

        vectors_stored = embed_and_store(chunks)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {str(e)}")
    finally:
        os.remove(tmp_path)  # always clean up the temp file, even on failure

    return UploadResponse(
        filename=file.filename,
        pages_extracted=len(pages),
        chunks_created=len(chunks),
        tables_detected=tables_detected,
        vectors_stored=vectors_stored,
    )