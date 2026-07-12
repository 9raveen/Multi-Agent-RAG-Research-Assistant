# routes_upload.py
# POST /upload — accepts a PDF, runs it through the Phase 1 ingestion pipeline.
# Phase 8: now requires login, tags Qdrant points with the uploader's user_id,
# and records a `documents` row in Postgres so ownership survives page reloads.

import sys, os, shutil, tempfile
sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))

from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from api.schemas import UploadResponse
from ingestion.pdf_parser import parse_pdf
from ingestion.chunker import chunk_pages
from ingestion.embedder import embed_and_store
from auth.dependencies import get_current_user
from db.database import get_db
from db.crud import create_document
from db.models import User

router = APIRouter()


@router.post("/upload", response_model=UploadResponse)
async def upload_pdf(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
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

        # parse_pdf() stamps source_file from the temp file's name (random,
        # e.g. "tmpxyz123.pdf") since that's the path it was given on disk.
        # Override it here with the real uploaded filename BEFORE chunking,
        # so every downstream chunk_id, citation, and payload reflects what
        # the user actually uploaded — not an internal temp artifact.
        for page in pages:
            page["source_file"] = file.filename

        chunks = chunk_pages(pages)
        tables_detected = sum(len(p.get("tables", [])) for p in pages)

        # user.id is a uuid.UUID from the SQLAlchemy model — Qdrant payloads
        # need it as a plain string (UUID objects aren't JSON-serializable).
        vectors_stored = embed_and_store(chunks, user_id=str(user.id))

        # Record ownership relationally too — this is what powers "your
        # documents" listings later; Qdrant's user_id tag alone can't answer
        # "list all documents this user has uploaded" efficiently.
        await create_document(db, user_id=user.id, source_file=file.filename)

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