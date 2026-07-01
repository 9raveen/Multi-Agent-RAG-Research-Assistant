# pdf_parser.py
# Responsibility: Extract raw text, section headers, AND structured tables from a PDF, page by page.
# Output: List of dicts → {text, page_number, source_file, section_headers, tables}

import fitz
from pathlib import Path

MIN_WORDS_PER_PAGE = 20


def extract_section_headers(page: fitz.Page) -> list[str]:
    """
    Extract likely section headers using font size heuristics.
    Headers tend to be larger/bolder than body text.
    """
    blocks = page.get_text("dict")["blocks"]

    font_sizes = []
    spans_data = []

    for block in blocks:
        if block["type"] != 0:  # type 0 = text block (not image)
            continue
        for line in block["lines"]:
            for span in line["spans"]:
                font_sizes.append(span["size"])
                spans_data.append(span)

    if not font_sizes:
        return []

    body_size = max(set(font_sizes), key=font_sizes.count)

    headers = []
    for span in spans_data:
        text = span["text"].strip()
        size = span["size"]

        is_larger = size > body_size * 1.15
        is_short_enough = len(text) < 100
        is_not_empty = len(text) > 2

        if is_larger and is_short_enough and is_not_empty:
            headers.append(text)

    seen = set()
    unique_headers = []
    for h in headers:
        if h not in seen:
            seen.add(h)
            unique_headers.append(h)

    return unique_headers


def rows_to_markdown(rows: list[list[str]]) -> str:
    """
    Serialize table rows into a Markdown table string.
    First row is treated as the header row.
    This is what actually gets embedded/sent to the LLM — a structured,
    LLM-parseable representation instead of scrambled flat text.
    """
    if not rows:
        return ""

    header = [str(c).replace("\n", " ").strip() for c in rows[0]]
    col_count = len(header)

    lines = [
        "| " + " | ".join(header) + " |",
        "| " + " | ".join(["---"] * col_count) + " |",
    ]

    for row in rows[1:]:
        row = list(row) + [""] * (col_count - len(row))  # pad short rows
        row = row[:col_count]                             # trim long rows
        cells = [str(c).replace("\n", " ").strip() if c is not None else "" for c in row]
        lines.append("| " + " | ".join(cells) + " |")

    return "\n".join(lines)


def extract_tables(page: fitz.Page, min_rows: int = 2) -> list[dict]:
    """
    Detect and extract tables on a page using PyMuPDF's table finder.
    min_rows filters out false-positive single-row detections
    (common on slide/presentation PDFs where text boxes get
    misidentified as tables).
    """
    tables = []
    try:
        finder = page.find_tables()
    except Exception:
        return tables

    for table in finder.tables:
        try:
            rows = table.extract()
        except Exception:
            continue

        if not rows or len(rows) < min_rows:   # ← reject trivial detections
            continue

        rows = [[cell if cell is not None else "" for cell in row] for row in rows]

        tables.append({
            "bbox": tuple(table.bbox),
            "rows": rows,
        })

    return tables


def _block_in_table(block, table_bboxes: list[tuple], tol: float = 2.0) -> bool:
    """Check whether a text block's center point falls inside any table bbox."""
    bx0, by0, bx1, by1 = block[0], block[1], block[2], block[3]
    cx, cy = (bx0 + bx1) / 2, (by0 + by1) / 2

    for (tx0, ty0, tx1, ty1) in table_bboxes:
        if tx0 - tol <= cx <= tx1 + tol and ty0 - tol <= cy <= ty1 + tol:
            return True
    return False


def extract_page_text_ordered(page: fitz.Page, table_bboxes: list[tuple] | None = None) -> str:
    """
    Extract prose text preserving reading order, EXCLUDING any text block
    that belongs to a detected table (prevents duplicate/scrambled table
    content in the prose stream — tables are handled separately as structured data).
    """
    table_bboxes = table_bboxes or []
    blocks = page.get_text("blocks")

    text_blocks = [b for b in blocks if b[6] == 0]
    text_blocks = [b for b in text_blocks if not _block_in_table(b, table_bboxes)]

    text_blocks.sort(key=lambda b: (round(b[1] / 10) * 10, b[0]))
    page_text = "\n".join(b[4].strip() for b in text_blocks if b[4].strip())
    return page_text


def _looks_like_header(row: list[str]) -> bool:
    """
    Crude heuristic: header rows are mostly non-numeric labels.
    If more than half the cells parse as numbers, it's probably a data row,
    not a header — used to detect continuation tables (which start headerless).
    """
    if not row:
        return False
    numeric_count = 0
    for c in row:
        c = str(c).strip().replace(",", "")
        try:
            float(c)
            numeric_count += 1
        except ValueError:
            pass
    return numeric_count < len(row) / 2


def _merge_continued_tables(pages: list[dict], page_heights: dict) -> None:
    """
    Mutates `pages` in place. Detects tables that continue across a page
    boundary and merges them into a single logical table.

    Heuristic (all must hold):
      - last table on page N ends near the bottom margin
      - first table on page N+1 starts near the top margin
      - both tables have the same column count
      - the first row of page N+1's table does NOT look like a header
        (i.e. it's data continuing, not a fresh table)
    """
    for i in range(len(pages) - 1):
        cur = pages[i]
        nxt = pages[i + 1]

        if not cur.get("tables") or not nxt.get("tables"):
            continue

        last_table = cur["tables"][-1]
        first_next_table = nxt["tables"][0]

        page_h = page_heights.get(cur["page_number"])
        if not page_h:
            continue

        ends_near_bottom = last_table["bbox"][3] >= page_h * 0.85
        starts_near_top = first_next_table["bbox"][1] <= page_h * 0.15

        last_cols = len(last_table["rows"][0]) if last_table["rows"] else 0
        next_cols = len(first_next_table["rows"][0]) if first_next_table["rows"] else 0
        same_column_count = last_cols == next_cols and last_cols > 0

        next_is_headerless = (
            first_next_table["rows"] and not _looks_like_header(first_next_table["rows"][0])
        )

        if ends_near_bottom and starts_near_top and same_column_count and next_is_headerless:
            last_table["rows"].extend(first_next_table["rows"])
            last_table["markdown"] = rows_to_markdown(last_table["rows"])
            last_table["continued_on_page"] = nxt["page_number"]

            nxt["tables"].pop(0)  # merged — remove from the next page's list


def parse_pdf(file_path: str) -> list[dict]:
    """
    Parse a PDF and return a list of pages with metadata, including
    structured tables (with multi-page continuations merged).

    Returns:
        [
            {
                "text": "prose content, tables excluded...",
                "page_number": 1,
                "source_file": "report.pdf",
                "section_headers": ["Introduction"],
                "tables": [
                    {"rows": [[...], ...], "bbox": (...), "markdown": "| ... |", "continued_on_page": None}
                ]
            },
            ...
        ]
    """
    doc = fitz.open(file_path)
    source_file = Path(file_path).name
    pages = []
    page_heights = {}

    for page_index in range(len(doc)):
        page = doc[page_index]
        page_number = page_index + 1
        page_heights[page_number] = page.rect.height

        raw_tables = extract_tables(page)
        table_bboxes = [t["bbox"] for t in raw_tables]

        text = extract_page_text_ordered(page, table_bboxes)

        word_count = len(text.split())
        # Don't drop a page just because prose is thin if it has real table content
        if word_count < MIN_WORDS_PER_PAGE and not raw_tables:
            continue

        section_headers = extract_section_headers(page)

        tables = [
            {
                "rows": t["rows"],
                "bbox": t["bbox"],
                "markdown": rows_to_markdown(t["rows"]),
                "continued_on_page": None,
            }
            for t in raw_tables
        ]

        pages.append({
            "text": text,
            "page_number": page_number,
            "source_file": source_file,
            "section_headers": section_headers,
            "tables": tables,
        })

    doc.close()

    _merge_continued_tables(pages, page_heights)

    return pages


# ── Quick test ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python pdf_parser.py <path_to_pdf>")
        sys.exit(1)

    pages = parse_pdf(sys.argv[1])

    print(f"Total pages extracted: {len(pages)}")
    total_tables = sum(len(p["tables"]) for p in pages)
    print(f"Total tables detected: {total_tables}")

    for p in pages:
        if p["tables"]:
            print(f"\nPage {p['page_number']}: {len(p['tables'])} table(s)")
            for t in p["tables"]:
                rows = t["rows"]
                cont = f" (continues from earlier page? no — this IS the merge target, continued_on_page={t['continued_on_page']})" if t["continued_on_page"] else ""
                print(f"  rows={len(rows)}, cols={len(rows[0]) if rows else 0}{cont}")
                print("  --- markdown preview ---")
                print("\n".join(t["markdown"].splitlines()[:4]))