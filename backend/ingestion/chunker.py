# chunker.py
# Responsibility: Split page text into overlapping chunks with rich metadata.
# Text uses two-pass chunking (parent/child). Tables use row-based chunking
# (never split mid-row, header repeated in every chunk).

from langchain_text_splitters import RecursiveCharacterTextSplitter


SEPARATORS = ["\n\n", "\n", " ", ""]


def chunk_table(
    table: dict,
    page: dict,
    section_header: str,
    global_chunk_index: int,
    table_index: int,
    max_rows_per_child: int = 15,
) -> tuple[list[dict], int]:
    """
    Chunk a single table by ROW COUNT, never by character count.
    Splitting a table by char count risks cutting a row in half —
    that's the exact failure mode this replaces.

    Each child chunk repeats the header row, so it's self-contained
    even if retrieved without its neighbors. parent_text is the FULL
    table markdown, injected into the LLM prompt for complete context.
    """
    rows = table["rows"]
    if not rows:
        return [], global_chunk_index

    header = rows[0]
    body = rows[1:]

    parent_markdown = table["markdown"]
    parent_id = f"{page['source_file']}_p{page['page_number']}_tableparent{table_index}"

    row_groups = (
        [body[i:i + max_rows_per_child] for i in range(0, len(body), max_rows_per_child)]
        if body else [[]]
    )

    chunks = []
    for group in row_groups:
        child_rows = [header] + group
        child_markdown = _rows_to_markdown_local(child_rows)

        chunk_id = f"{page['source_file']}_p{page['page_number']}_c{global_chunk_index}"

        chunks.append({
            "text":            child_markdown,
            "parent_text":     parent_markdown,
            "page_number":     page["page_number"],
            "source_file":     page["source_file"],
            "section_header":  section_header,
            "chunk_id":        chunk_id,
            "parent_chunk_id": parent_id,
            "chunk_index":     global_chunk_index,
            "chunk_type":      "table",
        })
        global_chunk_index += 1

    return chunks, global_chunk_index


def _rows_to_markdown_local(rows: list[list[str]]) -> str:
    """Local copy to avoid importing pdf_parser here — keeps chunker.py standalone/testable."""
    if not rows:
        return ""
    header = [str(c).replace("\n", " ").strip() for c in rows[0]]
    col_count = len(header)
    lines = [
        "| " + " | ".join(header) + " |",
        "| " + " | ".join(["---"] * col_count) + " |",
    ]
    for row in rows[1:]:
        row = list(row) + [""] * (col_count - len(row))
        row = row[:col_count]
        cells = [str(c).replace("\n", " ").strip() if c is not None else "" for c in row]
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def chunk_pages(
    pages: list[dict],
    child_size: int = 1200,
    child_overlap: int = 200,
    parent_size: int = 4000,
    parent_overlap: int = 400,
    table_max_rows_per_chunk: int = 15,
) -> list[dict]:
    """
    Two-pass chunking for prose (parent/child, as before) PLUS a separate
    row-based chunking pass for tables. Every chunk now carries chunk_type
    so downstream (retrieval, prompt assembly) can format table hits
    differently from prose hits.
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
        headers = page.get("section_headers", [])
        section_header = headers[0] if headers else "Unknown"

        # ── Pass 1: prose text (unchanged logic, now tagged chunk_type="text") ──
        parent_texts = parent_splitter.split_text(page["text"])

        for parent_index, parent_text in enumerate(parent_texts):
            parent_id = f"{page['source_file']}_p{page['page_number']}_parent{parent_index}"
            child_texts = child_splitter.split_text(parent_text)

            for child_text in child_texts:
                chunk_id = f"{page['source_file']}_p{page['page_number']}_c{global_chunk_index}"

                all_chunks.append({
                    "text":            child_text,
                    "parent_text":     parent_text,
                    "page_number":     page["page_number"],
                    "source_file":     page["source_file"],
                    "section_header":  section_header,
                    "chunk_id":        chunk_id,
                    "parent_chunk_id": parent_id,
                    "chunk_index":     global_chunk_index,
                    "chunk_type":      "text",
                })
                global_chunk_index += 1

        # ── Pass 2: tables (new — row-based, never mid-row splits) ──
        for table_index, table in enumerate(page.get("tables", [])):
            table_chunks, global_chunk_index = chunk_table(
                table,
                page,
                section_header,
                global_chunk_index,
                table_index=table_index,
                max_rows_per_child=table_max_rows_per_chunk,
            )
            all_chunks.extend(table_chunks)

    return all_chunks


# ── Quick test ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys, os
    sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
    from ingestion.pdf_parser import parse_pdf

    if len(sys.argv) < 2:
        print("Usage: python chunker.py <path_to_pdf>")
        sys.exit(1)

    pages = parse_pdf(sys.argv[1])
    chunks = chunk_pages(pages)

    text_chunks = [c for c in chunks if c["chunk_type"] == "text"]
    table_chunks = [c for c in chunks if c["chunk_type"] == "table"]

    print(f"Total pages       : {len(pages)}")
    print(f"Total chunks      : {len(chunks)}")
    print(f"  text chunks     : {len(text_chunks)}")
    print(f"  table chunks    : {len(table_chunks)}")

    if table_chunks:
        c = table_chunks[0]
        print(f"\n--- First table chunk ---")
        print(f"chunk_id : {c['chunk_id']}")
        print(f"page     : {c['page_number']}")
        print(c["text"])