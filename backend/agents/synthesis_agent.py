# synthesis_agent.py
import sys, os, time
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from groq import Groq, RateLimitError
from dotenv import load_dotenv

from retrieval.retriever import format_chunks_for_prompt
from agents.state import ResearchState

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))
# Synthesis model is configurable via environment for easy migration.
# Default to Groq-hosted GPT-OSS-120B — llama-3.3-70b-versatile and
# llama-3.1-8b-instant are both deprecated on Groq, shutting down
# 2026-08-16, so neither belongs as the default or fallback anymore.
# You may set SYNTHESIS_MODEL to another provider/model name, and optionally
# set SYNTHESIS_FALLBACKS (comma-separated) to try other model names if the
# chosen model isn't available through the provider/client.
SYNTHESIS_MODEL = os.getenv("SYNTHESIS_MODEL", "openai/gpt-oss-120b")
SYNTHESIS_FALLBACKS = [m.strip() for m in os.getenv("SYNTHESIS_FALLBACKS", "openai/gpt-oss-20b").split(",") if m.strip()]
# Combined try-order (first the requested model, then configured fallbacks)
MODEL_TRY_ORDER = [SYNTHESIS_MODEL] + [m for m in SYNTHESIS_FALLBACKS if m != SYNTHESIS_MODEL]
# Import NotFoundError for graceful fallback handling
from groq import NotFoundError


def _create_chat_completion(messages, **kwargs):
    """Wrapper around client.chat.completions.create that attempts multiple
    model names in MODEL_TRY_ORDER if the provider reports model_not_found.

    Returns the same value as client.chat.completions.create. If stream=True,
    the returned object is an iterator/generator from the client; callers must
    handle streaming as before.
    """
    last_err = None
    for model in MODEL_TRY_ORDER:
        try:
            print(f"[model-fallback] trying model: {model}")
            return client.chat.completions.create(model=model, messages=messages, **kwargs)
        except NotFoundError as e:
            print(f"[model-fallback] model not found or no access: {model} — trying next fallback if any")
            last_err = e
            continue
        except RateLimitError:
            # Rate limit and other transient errors should bubble up to existing
            # retry handlers; re-raise so calling code can handle them.
            raise
        except Exception:
            # Any other unexpected error should be propagated — don't silently
            # swallow errors other than model-not-found.
            raise
    # If we reach here, all models failed with NotFoundError
    raise last_err if last_err is not None else Exception("No models available")


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

SINGLE_SHOT_WORD_LIMIT = 6000  # Increased from 4000 — GPT-OSS-120B handles a
                                 # 131K context comfortably, so raising this
                                 # threshold reduces the chance of triggering
                                 # map-reduce and its multiple API calls. Most
                                 # PDFs under ~10 pages now summarize in a single
                                 # shot (one Groq call instead of 3-5), avoiding
                                 # rate limit issues entirely for small-to-medium
                                 # documents.

MAP_BATCH_WORD_LIMIT = 4500     # Increased from 3500 (in _batch_chunks default) —
                                 # fewer, larger batches = fewer total API calls for
                                 # very large documents, reducing rate limit pressure.


def _word_count(chunks: list[dict]) -> int:
    return sum(len(c["parent_text"].split()) for c in chunks)


def _batch_chunks(chunks: list[dict], batch_word_limit: int = 4500) -> list[list[dict]]:
    """Groups chunks into batches by cumulative word count (not chunk count) —
    keeps each map-step prompt a predictable, safe size regardless of
    whether individual chunks are short paragraphs or long table dumps.
    
    Increased from 3500 to 4500 words per batch to reduce the total number
    of API calls for large documents (fewer batches = fewer Groq requests).
    """
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


def _summarize_batch(chunks: list[dict], retry_count: int = 0) -> str:
    """Summarize a single batch with exponential backoff retry on rate limits."""
    context = format_chunks_for_prompt(chunks)
    max_retries = 3
    
    try:
        response = _create_chat_completion(
            messages=[
                {"role": "system", "content": MAP_SYSTEM_PROMPT},
                {"role": "user", "content": f"Context:\n{context}\n\nSummarize this section."},
            ],
            temperature=0.2,
            max_tokens=400,
        )
        return response.choices[0].message.content
    except RateLimitError as e:
        if retry_count >= max_retries:
            print(f"[_summarize_batch] Rate limit hit after {max_retries} retries, giving up")
            raise
        
        # Exponential backoff: 3s, 6s, 12s
        wait_time = 3 * (2 ** retry_count)
        print(f"[_summarize_batch] Rate limit hit, waiting {wait_time}s before retry {retry_count + 1}/{max_retries}")
        time.sleep(wait_time)
        return _summarize_batch(chunks, retry_count + 1)


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

    batches = _batch_chunks(chunks, batch_word_limit=MAP_BATCH_WORD_LIMIT)
    total_batches = len(batches)
    print(f"[summarize] document too large for single-shot ({total_words} words)")
    print(f"[summarize] using map-reduce across {total_batches} batches (~{total_words // total_batches} words each)")
    print(f"[summarize] estimated time: ~{total_batches * 3}s (with rate limit protection)")

    # Increased delay between batches to prevent rate limit errors.
    # Groq free tier limits vary by model — keep a conservative delay so
    # a large document's map step doesn't burst past the per-minute cap.
    # With 2.5s delay: comfortable safety margin under typical free-tier RPM.
    # With 3.5s delay every 5 batches: prevents sustained burst issues
    batch_summaries = []
    for i, batch in enumerate(batches):
        print(f"[summarize] processing batch {i + 1}/{total_batches}")
        batch_summaries.append(_summarize_batch(batch))
        if i < len(batches) - 1:
            # Adaptive delay: longer wait after every 5 batches to avoid sustained burst
            delay = 3.5 if (i + 1) % 5 == 0 else 2.5
            time.sleep(delay)

    combined = "\n\n".join(f"Section {i + 1} summary:\n{s}" for i, s in enumerate(batch_summaries))
    user_content = f"{combined}\n\nCombine these section summaries into one comprehensive document summary."
    return REDUCE_SYSTEM_PROMPT, user_content


def summarize_document(chunks: list[dict]) -> str:
    """Non-streaming whole-document summary, used by the /query endpoint."""
    if not chunks:
        return "No content was found for this document, so a summary can't be generated."

    system_prompt, user_content = _build_summary_prompt(chunks)

    response = _create_chat_completion(
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

    stream = _create_chat_completion(
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

            response = _create_chat_completion(
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
        model=SYNTHESIS_MODEL,
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