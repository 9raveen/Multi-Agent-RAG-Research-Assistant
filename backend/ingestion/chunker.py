# chunker.py
# Responsibility: Split page text into overlapping chunks with rich metadata.
# Uses two-pass chunking: large parent chunks + small child chunks.
# Input:  List of page dicts from pdf_parser.py
# Output: List of chunk dicts with full metadata

from langchain_text_splitters import RecursiveCharacterTextSplitter


SEPARATORS = ["\n\n", "\n", " ", ""]


def chunk_pages(
    pages: list[dict],
    child_size: int = 1200,     # ~300 tokens — for retrieval precision
    child_overlap: int = 200,   # overlap between child chunks
    parent_size: int = 4000,    # ~1000 tokens — for context injection into LLM
    parent_overlap: int = 400,
) -> list[dict]:
    """
    Two-pass chunking strategy:

    Pass 1 (parent chunks):
        Large chunks (~1000 tokens). Stored in metadata only.
        Used during answer generation — injected as full context into the LLM.

    Pass 2 (child chunks):
        Small chunks (~300 tokens). These are what get embedded and retrieved.
        Each child knows its parent_chunk_id.

    Why two passes?
        Small chunks = precise retrieval (embedding captures focused meaning)
        Large parent = rich context for LLM to generate a complete answer

    This is "Parent Document Retrieval" — a standard RAG improvement pattern.
    """

    parent_splitter = RecursiveCharacterTextSplitter(
        chunk_size=parent_size,
        chunk_overlap=parent_overlap,
        separators=SEPARATORS
    )

    child_splitter = RecursiveCharacterTextSplitter(
        chunk_size=child_size,
        chunk_overlap=child_overlap,
        separators=SEPARATORS
    )

    all_chunks = []
    global_chunk_index = 0

    for page in pages:
        # Fix: pdf_parser returns section_headers as a list
        headers = page.get("section_headers", [])
        section_header = headers[0] if headers else "Unknown"

        # Pass 1: split page into large parent chunks
        parent_texts = parent_splitter.split_text(page["text"])

        for parent_index, parent_text in enumerate(parent_texts):
            parent_id = f"{page['source_file']}_p{page['page_number']}_parent{parent_index}"

            # Pass 2: split each parent into small child chunks
            child_texts = child_splitter.split_text(parent_text)

            for child_index, child_text in enumerate(child_texts):
                chunk_id = f"{page['source_file']}_p{page['page_number']}_c{global_chunk_index}"

                all_chunks.append({
                    "text":           child_text,           # small — gets embedded
                    "parent_text":    parent_text,          # large — injected into LLM prompt
                    "page_number":    page["page_number"],
                    "source_file":    page["source_file"],
                    "section_header": section_header,
                    "chunk_id":       chunk_id,
                    "parent_chunk_id": parent_id,           # which parent this came from
                    "chunk_index":    global_chunk_index,
                })

                global_chunk_index += 1

    return all_chunks


# ── Quick test ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys, os
    sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
    from ingestion.pdf_parser import parse_pdf

    if len(sys.argv) < 2:
        print("Usage: python chunker.py <path_to_pdf>")
        sys.exit(1)

    pages  = parse_pdf(sys.argv[1])
    chunks = chunk_pages(pages)

    print(f"Total pages  : {len(pages)}")
    print(f"Total chunks : {len(chunks)}")
    print(f"Avg/page     : {len(chunks)/len(pages):.1f}")

    c = chunks[0]
    print(f"\n--- Chunk 0 ---")
    print(f"chunk_id      : {c['chunk_id']}")
    print(f"parent_chunk_id: {c['parent_chunk_id']}")
    print(f"chunk_index   : {c['chunk_index']}")
    print(f"page_number   : {c['page_number']}")
    print(f"section_header: {c['section_header']}")
    print(f"child text    : {c['text'][:200]}")
    print(f"parent text   : {c['parent_text'][:200]}")