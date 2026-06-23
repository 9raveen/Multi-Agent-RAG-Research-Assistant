# pdf_parser.py
# Responsibility: Extract raw text + section headers from a PDF, page by page.
# Output: List of dicts → {text, page_number, source_file, section_headers}

import fitz
from pathlib import Path

# Minimum words for a page to be considered valid content
MIN_WORDS_PER_PAGE = 20

def extract_section_headers(page: fitz.Page) -> list[str]:
    """
    Extract likely section headers using font size heuristics.
    Headers tend to be larger/bolder than body text.
    
    Strategy:
    1. Get all text spans with their font sizes
    2. Find the dominant (body) font size
    3. Any text significantly larger = likely a header
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

    # Body font size = most common font size on this page
    body_size = max(set(font_sizes), key=font_sizes.count)

    headers = []
    for span in spans_data:
        text = span["text"].strip()
        size = span["size"]
        
        # Header condition: font size notably larger than body
        # and not too long (real headers are short)
        is_larger = size > body_size * 1.15
        is_short_enough = len(text) < 100
        is_not_empty = len(text) > 2

        if is_larger and is_short_enough and is_not_empty:
            headers.append(text)

    # Deduplicate while preserving order
    seen = set()
    unique_headers = []
    for h in headers:
        if h not in seen:
            seen.add(h)
            unique_headers.append(h)

    return unique_headers


def extract_page_text_ordered(page: fitz.Page) -> str:
    """
    Extract text preserving reading order using block-level sorting.
    Fixes two-column academic PDF issue where default get_text()
    merges columns left-to-right across the full page width.
    
    Strategy: sort text blocks by vertical position (y), then horizontal (x).
    This respects column layout naturally.
    """
    blocks = page.get_text("blocks")  # returns (x0, y0, x1, y1, text, block_no, block_type)
    
    # Filter to text blocks only (type 0), skip image blocks (type 1)
    text_blocks = [b for b in blocks if b[6] == 0]
    
    # Sort: top-to-bottom first, then left-to-right within same row
    # Round y0 to nearest 10px to group blocks on the same "line"
    text_blocks.sort(key=lambda b: (round(b[1] / 10) * 10, b[0]))
    
    page_text = "\n".join(b[4].strip() for b in text_blocks if b[4].strip())
    return page_text


def parse_pdf(file_path: str) -> list[dict]:
    """
    Parse a PDF and return a list of pages with metadata.

    Args:
        file_path: Path to the PDF file

    Returns:
        List of dicts:
        [
            {
                "text": "page content...",
                "page_number": 1,
                "source_file": "paper.pdf",
                "section_headers": ["Introduction", "2.1 Related Work"]
            },
            ...
        ]
    """
    doc = fitz.open(file_path)
    source_file = Path(file_path).name
    pages = []

    for page_index in range(len(doc)):
        page = doc[page_index]

        # Use ordered extraction (fixes two-column layout)
        text = extract_page_text_ordered(page)

        # Skip pages with too little content
        word_count = len(text.split())
        if word_count < MIN_WORDS_PER_PAGE:
            continue

        # Extract section headers from this page
        section_headers = extract_section_headers(page)

        pages.append({
            "text": text,
            "page_number": page_index + 1,
            "source_file": source_file,
            "section_headers": section_headers  # list, may be empty
        })

    doc.close()
    return pages


# ── Quick test ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python pdf_parser.py <path_to_pdf>")
        sys.exit(1)

    pages = parse_pdf(sys.argv[1])

    print(f"Total pages extracted: {len(pages)}")
    print(f"Source file         : {pages[0]['source_file']}")
    print(f"\n--- Page 1 preview (first 300 chars) ---")
    print(pages[0]['text'][:300])
    print(f"\n--- Section headers found on page 1 ---")
    print(pages[0]['section_headers'])