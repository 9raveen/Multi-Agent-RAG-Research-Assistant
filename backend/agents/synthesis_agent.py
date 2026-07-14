# synthesis_agent.py
import sys, os, time
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from groq import Groq, RateLimitError
from dotenv import load_dotenv

from retrieval.retriever import format_chunks_for_prompt
from agents.state import ResearchState

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

SYSTEM_PROMPT = """You are a research assistant. Answer the user's question using ONLY the information in the provided context below.

Rules:
- Do not use outside knowledge. If the context doesn't contain enough information to answer, say so explicitly.
- Cite the source for each claim using the page numbers given in the context (e.g. "(page 3)").
- If the context includes a table, you may reference specific rows/values directly.
- Be thorough: when the context contains enough detail to support it, give a complete,
  well-developed answer — explain reasoning, cover relevant sub-points, and use multiple
  paragraphs or bullet points where that makes the answer clearer. Draw on ALL relevant
  parts of the context, not just the single closest match.
- Do not add unsupported claims, invented examples, or content the context doesn't
  actually contain just to make the answer longer — depth should come from fully using
  what's genuinely there, not from padding.
"""

# ── Document summarization ──────────────────────────────────────────────────
# Separate from the QA path above on purpose: top-k similarity search (used
# for normal questions) is the wrong tool for "summarize this document" —
# the query is topically generic, so vector search has no strong signal for
# what's important and returns some semantically-average handful of chunks,
# not comprehensive document coverage. Summarization instead receives ALL of
# a document's chunks (via retriever.retrieve_all_chunks) and either:
#   - summarizes them in one shot, if the document is short enough to fit
#     comfortably in a single prompt, or
#   - map-reduces: summarizes batches of chunks individually (the "map"
#     step), then combines those batch summaries into one final summary
#     (the "reduce" step) — for documents too large for a single prompt.

SUMMARY_SYSTEM_PROMPT = """You are a research assistant producing a comprehensive summary of a document, using ONLY the provided context.

Rules:
- Base the summary entirely on the context given — do not use outside knowledge.
- Cover the main sections/topics of the document, not just the first part.
- Structure the summary clearly — short paragraphs or bullet points per major topic.
- Cite page numbers for major claims where possible (e.g. "(page 3)").
- Do not invent content the context doesn't support.
"""

MAP_SYSTEM_PROMPT = """You are summarizing ONE SECTION of a larger document, using ONLY the provided context. Write a concise but complete summary of what this section covers, in 3-6 sentences, including specific details worth preserving. This summary will later be combined with summaries of other sections into a full-document summary."""

REDUCE_SYSTEM_PROMPT = """You are combining several section summaries of one document into a single, coherent, comprehensive summary. Synthesize into a well-organized whole covering the main themes across all sections — short paragraphs or bullet points per major theme — rather than just concatenating the section summaries back to back."""

SINGLE_SHOT_WORD_LIMIT = 4000  # below this, summarize all chunks in one call;
                                 # above it, map-reduce (see summarize_document below)


def _word_count(chunks: list[dict]) -> int:
    return sum(len(c["parent_text"].split()) for c in chunks)


def _batch_chunks(chunks: list[dict], batch_word_limit: int = 3500) -> list[list[dict]]:
    """Groups chunks into batches by cumulative word count (not chunk count) —
    keeps each map-step prompt a predictable, safe size regardless of
    whether individual chunks are short paragraphs or long table dumps."""
    batches = []
    current_batch = []
    current_words = 0
    for c in chunks:
        words = len(c["parent_text"].split())
        if current_words + words > batch_word_limit and current_batch:
            batches.append(current_batch)
            current_batch = []
            current_words = 0
        current_batch.append(c)
        current_words += words
    if current_batch:
        batches.append(current_batch)
    return batches


def _summarize_batch(chunks: list[dict]) -> str:
    context = format_chunks_for_prompt(chunks)
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": MAP_SYSTEM_PROMPT},
            {"role": "user", "content": f"Context:\n{context}\n\nSummarize this section."},
        ],
        temperature=0.2,
        max_tokens=400,
    )
    return response.choices[0].message.content


def _build_summary_prompt(chunks: list[dict]) -> tuple[str, str]:
    """
    Returns (system_prompt, user_content) for the FINAL summary call —
    either the single-shot summary prompt, or the reduce-step prompt fed
    with pre-computed batch summaries. Shared by summarize_document (non-
    streaming) and summarize_document_stream (streaming) so the two can't
    drift out of sync with each other.
    """
    total_words = _word_count(chunks)

    if total_words <= SINGLE_SHOT_WORD_LIMIT:
        context = format_chunks_for_prompt(chunks)
        user_content = f"Context (full document):\n{context}\n\nProvide a comprehensive summary of this document."
        return SUMMARY_SYSTEM_PROMPT, user_content

    batches = _batch_chunks(chunks)
    print(f"[summarize] document too large for single-shot ({total_words} words) — map-reduce across {len(batches)} batches")

    # Small delay between calls (not after the last one) — spaces out what
    # would otherwise be a tight burst of back-to-back Groq requests. Free-
    # tier rate limits are often requests-per-minute, not just tokens-per-
    # minute, so even small/fast calls can trip a limit if fired in a burst.
    # Cheap insurance: adds a few seconds total for a large document, in
    # exchange for real robustness against exactly the 429 you just hit.
    batch_summaries = []
    for i, batch in enumerate(batches):
        batch_summaries.append(_summarize_batch(batch))
        if i < len(batches) - 1:
            time.sleep(1.5)

    combined = "\n\n".join(f"Section {i + 1} summary:\n{s}" for i, s in enumerate(batch_summaries))
    user_content = f"{combined}\n\nCombine these section summaries into one comprehensive document summary."
    return REDUCE_SYSTEM_PROMPT, user_content


def summarize_document(chunks: list[dict]) -> str:
    """Non-streaming whole-document summary, used by the /query endpoint."""
    if not chunks:
        return "No content was found for this document, so a summary can't be generated."

    system_prompt, user_content = _build_summary_prompt(chunks)

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ],
        temperature=0.2,
        max_tokens=1200,
    )
    return response.choices[0].message.content


def summarize_document_stream(chunks: list[dict]):
    """
    Streaming whole-document summary, used by /query/stream. Any map-step
    batch summarization happens non-streamed first (those are intermediate
    results never shown to the user) — only the final summary (single-shot
    or reduce-step) streams token-by-token.
    """
    if not chunks:
        yield "No content was found for this document, so a summary can't be generated."
        return

    system_prompt, user_content = _build_summary_prompt(chunks)

    stream = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ],
        temperature=0.2,
        max_tokens=1200,
        stream=True,
    )
    for chunk in stream:
        delta = chunk.choices[0].delta.content
        if delta:
            yield delta


def synthesis_node(state: ResearchState) -> dict:
    query = state["query"]
    chunks = state["retrieved_chunks"]
    is_summary = state.get("is_summary_request", False)

    print(f"[synthesis_node] generating {'summary' if is_summary else 'answer'} from {len(chunks)} chunks")

    try:
        if is_summary:
            answer = summarize_document(chunks)
        else:
            context = format_chunks_for_prompt(chunks)
            user_prompt = f"""Context:
{context}

Question: {query}

Answer using only the context above."""

            response = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.2,
                max_tokens=1200,  # was 500 — that hard-capped every answer at ~375 words
                                   # regardless of how much the question needed; 1200 gives
                                   # room for genuinely thorough answers without being
                                   # effectively unbounded (still Groq-cost-conscious)
            )
            answer = response.choices[0].message.content
        rate_limited = False
    except RateLimitError as e:
        print(f"[synthesis_node] RATE LIMIT hit — returning empty answer, no retry. {e}")
        answer = "SYNTHESIS FAILED — Groq rate limit reached before answer could be generated."
        rate_limited = True

    print(f"[synthesis_node] answer: {answer[:200]}...")

    return {
        "synthesis_output": answer,
        "rate_limited": rate_limited,
        "previous_answer": state.get("synthesis_output", ""),  # captures OLD answer, BEFORE this call
    }


def synthesize_stream(query: str, chunks: list[dict]):
    """
    Generator version of synthesis — yields text deltas as they arrive from
    Groq, for the SSE streaming endpoint. Does NOT touch graph state directly;
    the caller accumulates the full text and updates state itself.

    Raises RateLimitError up to the caller (does not catch it here) so the
    caller can decide how to represent that in the stream.
    """
    context = format_chunks_for_prompt(chunks)
    user_prompt = f"""Context:
{context}

Question: {query}

Answer using only the context above."""

    stream = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.2,
        max_tokens=1200,  # kept in sync with synthesis_node above
        stream=True,  # KEY CHANGE — enables token-level streaming from Groq
    )

    for chunk in stream:
        delta = chunk.choices[0].delta.content
        if delta:
            yield delta