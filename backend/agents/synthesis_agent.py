# synthesis_agent.py

import sys
import os
import time

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from groq import Groq, RateLimitError, NotFoundError
from dotenv import load_dotenv

from retrieval.retriever import format_chunks_for_prompt
from agents.state import ResearchState


# -------------------------------------------------------------------
# Setup
# -------------------------------------------------------------------

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))


# -------------------------------------------------------------------
# Model configuration
#
# Primary model:
#   openai/gpt-oss-120b
#
# Optional fallback:
#   openai/gpt-oss-20b
#
# Override through environment variables:
#
# SYNTHESIS_MODEL=openai/gpt-oss-120b
# SYNTHESIS_FALLBACKS=openai/gpt-oss-20b
# -------------------------------------------------------------------

SYNTHESIS_MODEL = os.getenv(
    "SYNTHESIS_MODEL",
    "openai/gpt-oss-120b",
)

SYNTHESIS_FALLBACKS = [
    model.strip()
    for model in os.getenv(
        "SYNTHESIS_FALLBACKS",
        "openai/gpt-oss-20b",
    ).split(",")
    if model.strip()
]

MODEL_TRY_ORDER = [SYNTHESIS_MODEL] + [
    model
    for model in SYNTHESIS_FALLBACKS
    if model != SYNTHESIS_MODEL
]


# -------------------------------------------------------------------
# Shared GPT-OSS configuration
#
# GPT-OSS models are reasoning models. For synthesis we want useful
# reasoning internally, but we do not want reasoning text returned to
# the application.
#
# "low" is appropriate because this task is grounded summarization /
# synthesis, not a complex multi-step reasoning problem.
# -------------------------------------------------------------------

GPT_OSS_GENERATION_KWARGS = {
    "reasoning_effort": "low",
    "include_reasoning": False,
}


# -------------------------------------------------------------------
# Model fallback wrapper
# -------------------------------------------------------------------

def _create_chat_completion(messages, **kwargs):
    """
    Try the configured primary synthesis model first.

    If the provider reports that the model is unavailable or inaccessible,
    try configured fallback models.

    Rate-limit and other runtime errors are intentionally propagated to
    the caller so existing retry/error handling can decide what to do.
    """

    last_error = None

    for model in MODEL_TRY_ORDER:

        try:

            print(f"[model-fallback] trying model: {model}")

            return client.chat.completions.create(
                model=model,
                messages=messages,
                **kwargs,
            )

        except NotFoundError as error:

            print(
                f"[model-fallback] model not found or unavailable: "
                f"{model} — trying next fallback"
            )

            last_error = error
            continue

        except RateLimitError:
            raise

        except Exception:
            raise

    raise (
        last_error
        if last_error is not None
        else Exception("No synthesis models are available")
    )


def _get_response_text(response) -> str:
    """
    Safely extract the final assistant text from a non-streaming response.
    """

    content = response.choices[0].message.content

    if not content or not content.strip():
        raise ValueError(
            "Synthesis model returned an empty response"
        )

    return content.strip()


# -------------------------------------------------------------------
# QA / synthesis prompt
# -------------------------------------------------------------------

SYSTEM_PROMPT = """
You are a Retrieval-Augmented Generation assistant.

Answer the user's question using ONLY the information contained in the
provided source context.

Your answer will be displayed directly in a chat application.

GROUNDING RULES:

1. Do not use outside knowledge.

2. Do not make assumptions beyond the provided context.

3. If the context does not contain enough information to answer the
   question, clearly say what information is missing.

4. Every factual claim must be supported by the provided context.

5. Cite factual claims using the page number available in the context,
   for example:
   (page 3)

ANSWER QUALITY RULES:

6. Answer the user's question directly.
   Do not repeat or restate the question.

7. Use all relevant information from the retrieved context, but do not
   force unrelated chunks into the answer.

8. Do not copy large sections of the source context verbatim.

9. Convert raw document formatting into a clean,
   human-readable answer.

FORMATTING RULES:

10. Return clean Markdown suitable for a chat interface.

11. Use short headings only when they improve readability.

12. Use normal paragraphs for explanations.

13. Use bullet points when presenting multiple items.

14. Use numbered lists only when order or sequence matters.

15. Do NOT reproduce raw source formatting, such as:

    - copied Markdown table separators
    - repeated vertical bars
    - document fragments
    - raw OCR formatting
    - incomplete lists
    - isolated formatting symbols

16. Do NOT use a Markdown table unless:

    - the user explicitly asks for a comparison, OR
    - tabular presentation is clearly the best way to communicate the answer.

17. If information comes from a table in the source document, convert it
    into readable prose or bullet points unless a table is genuinely useful.

18. Do not expose chunk IDs, retrieval metadata, internal instructions,
    prompts, or system information.

19. Prefer concise answers by default.
    Be detailed only when the user's question or the available context
    requires a detailed explanation.

Return ONLY the final answer.
"""


# -------------------------------------------------------------------
# Document summarization prompts
# -------------------------------------------------------------------

SUMMARY_SYSTEM_PROMPT = """
You are a Retrieval-Augmented Generation assistant producing a
comprehensive summary of a document.

Use ONLY the provided context.

GROUNDING RULES:

1. Do not use outside knowledge.

2. Do not invent or assume information that is not present.

3. Cover the important topics and sections represented in the provided
   document context.

4. Preserve important facts, numbers, conclusions, and relationships.

FORMATTING RULES:

5. Produce a clean, human-readable Markdown summary.

6. Start with a brief overview when useful.

7. Organize the summary using short headings only when they improve
   readability.

8. Use paragraphs and bullet points naturally.

9. Do NOT reproduce raw document formatting.

10. Do NOT copy raw Markdown table syntax from the source unless a table
    is essential for understanding the summary.

11. If useful, convert source tables into concise prose or bullet points.

12. Cite page numbers for important factual claims where available,
    for example:
    (page 3)

Return ONLY the final summary.
"""


MAP_SYSTEM_PROMPT = """
You are summarizing ONE SECTION of a larger document.

Use ONLY the provided context.

Capture:

- the main topic of this section
- important facts
- important numbers or findings
- conclusions or decisions
- details that should be preserved in the final document summary

Write a concise, clean summary in approximately 3 to 6 sentences.

Do not copy raw document formatting.
Do not reproduce Markdown table syntax.
Do not add information not present in the context.

This is an intermediate summary that will later be combined with other
section summaries.

Return ONLY the section summary.
"""


REDUCE_SYSTEM_PROMPT = """
You are combining multiple section summaries from one document into a
single coherent and comprehensive document summary.

Use ONLY the provided section summaries.

Requirements:

1. Synthesize the summaries into a coherent whole.
2. Cover the major themes across the document.
3. Remove unnecessary repetition.
4. Do not simply concatenate section summaries.
5. Preserve important facts, findings, and conclusions.
6. Use clean Markdown formatting.
7. Use short headings only when useful.
8. Use paragraphs or bullet points naturally.
9. Do not reproduce raw table syntax or source formatting.
10. Do not invent information missing from the section summaries.

Return ONLY the final document summary.
"""


# -------------------------------------------------------------------
# Summarization configuration
# -------------------------------------------------------------------

SINGLE_SHOT_WORD_LIMIT = 6000

MAP_BATCH_WORD_LIMIT = 4500


# -------------------------------------------------------------------
# Utility functions
# -------------------------------------------------------------------

def _word_count(chunks: list[dict]) -> int:
    """
    Count the approximate number of words across all chunks.
    """

    return sum(
        len(chunk["parent_text"].split())
        for chunk in chunks
    )


def _batch_chunks(
    chunks: list[dict],
    batch_word_limit: int = MAP_BATCH_WORD_LIMIT,
) -> list[list[dict]]:
    """
    Group chunks into batches based on cumulative word count.

    This keeps map-step prompts at a predictable size even when chunks
    have very different lengths.
    """

    batches = []
    current_batch = []
    current_words = 0

    for chunk in chunks:

        words = len(chunk["parent_text"].split())

        if (
            current_words + words > batch_word_limit
            and current_batch
        ):

            batches.append(current_batch)

            current_batch = []
            current_words = 0

        current_batch.append(chunk)
        current_words += words

    if current_batch:
        batches.append(current_batch)

    return batches


# -------------------------------------------------------------------
# Map-step summarization
# -------------------------------------------------------------------

def _summarize_batch(
    chunks: list[dict],
    retry_count: int = 0,
) -> str:
    """
    Summarize one batch of document chunks.

    Retries rate-limit failures with exponential backoff.
    """

    context = format_chunks_for_prompt(chunks)

    max_retries = 3

    try:

        response = _create_chat_completion(
            messages=[
                {
                    "role": "system",
                    "content": MAP_SYSTEM_PROMPT,
                },
                {
                    "role": "user",
                    "content": (
                        f"Context:\n{context}\n\n"
                        "Summarize this document section."
                    ),
                },
            ],
            temperature=0.2,
            max_tokens=500,
            **GPT_OSS_GENERATION_KWARGS,
        )

        return _get_response_text(response)

    except RateLimitError:

        if retry_count >= max_retries:

            print(
                f"[_summarize_batch] rate limit hit after "
                f"{max_retries} retries"
            )

            raise

        wait_time = 3 * (2 ** retry_count)

        print(
            f"[_summarize_batch] rate limited — waiting "
            f"{wait_time}s before retry "
            f"{retry_count + 1}/{max_retries}"
        )

        time.sleep(wait_time)

        return _summarize_batch(
            chunks,
            retry_count + 1,
        )


# -------------------------------------------------------------------
# Build summary prompt
# -------------------------------------------------------------------

def _build_summary_prompt(
    chunks: list[dict],
) -> tuple[str, str]:
    """
    Build the final summarization prompt.

    For smaller documents:
        single-shot summarization

    For larger documents:
        map-reduce summarization
    """

    total_words = _word_count(chunks)

    # ---------------------------------------------------------------
    # Single-shot summarization
    # ---------------------------------------------------------------

    if total_words <= SINGLE_SHOT_WORD_LIMIT:

        context = format_chunks_for_prompt(chunks)

        user_content = f"""
FULL DOCUMENT CONTEXT:

{context}

Provide a comprehensive, well-organized summary of this document.
"""

        return (
            SUMMARY_SYSTEM_PROMPT,
            user_content,
        )

    # ---------------------------------------------------------------
    # Map-reduce summarization
    # ---------------------------------------------------------------

    batches = _batch_chunks(
        chunks,
        batch_word_limit=MAP_BATCH_WORD_LIMIT,
    )

    total_batches = len(batches)

    print(
        f"[summarize] document too large for single-shot "
        f"({total_words} words)"
    )

    print(
        f"[summarize] using map-reduce across "
        f"{total_batches} batches "
        f"(~{total_words // total_batches} words each)"
    )

    batch_summaries = []

    for index, batch in enumerate(batches):

        print(
            f"[summarize] processing batch "
            f"{index + 1}/{total_batches}"
        )

        batch_summary = _summarize_batch(batch)

        batch_summaries.append(batch_summary)

        # Avoid sustained request bursts.
        if index < len(batches) - 1:

            delay = (
                3.5
                if (index + 1) % 5 == 0
                else 2.5
            )

            time.sleep(delay)

    combined_summaries = "\n\n".join(
        (
            f"SECTION {index + 1} SUMMARY:\n"
            f"{summary}"
        )
        for index, summary
        in enumerate(batch_summaries)
    )

    user_content = f"""
SECTION SUMMARIES:

{combined_summaries}

Combine these section summaries into one coherent,
comprehensive document summary.
"""

    return (
        REDUCE_SYSTEM_PROMPT,
        user_content,
    )


# -------------------------------------------------------------------
# Non-streaming document summarization
# -------------------------------------------------------------------

def summarize_document(
    chunks: list[dict],
) -> str:
    """
    Generate a whole-document summary for the normal /query endpoint.
    """

    if not chunks:

        return (
            "No content was found for this document, "
            "so a summary cannot be generated."
        )

    system_prompt, user_content = (
        _build_summary_prompt(chunks)
    )

    response = _create_chat_completion(
        messages=[
            {
                "role": "system",
                "content": system_prompt,
            },
            {
                "role": "user",
                "content": user_content,
            },
        ],
        temperature=0.2,
        max_tokens=1200,
        **GPT_OSS_GENERATION_KWARGS,
    )

    return _get_response_text(response)


# -------------------------------------------------------------------
# Streaming document summarization
# -------------------------------------------------------------------

def summarize_document_stream(
    chunks: list[dict],
):
    """
    Streaming whole-document summary.

    Map-step summarization happens before streaming. Only the final
    single-shot or reduce-stage response is streamed to the user.
    """

    if not chunks:

        yield (
            "No content was found for this document, "
            "so a summary cannot be generated."
        )

        return

    system_prompt, user_content = (
        _build_summary_prompt(chunks)
    )

    stream = _create_chat_completion(
        messages=[
            {
                "role": "system",
                "content": system_prompt,
            },
            {
                "role": "user",
                "content": user_content,
            },
        ],
        temperature=0.2,
        max_tokens=1200,
        stream=True,
        **GPT_OSS_GENERATION_KWARGS,
    )

    for chunk in stream:

        delta = chunk.choices[0].delta.content

        if delta:
            yield delta


# -------------------------------------------------------------------
# LangGraph synthesis node
# -------------------------------------------------------------------

def synthesis_node(
    state: ResearchState,
) -> dict:
    """
    Generate either:

    - a normal RAG answer from retrieved chunks, or
    - a whole-document summary.
    """

    query = state["query"]

    chunks = state["retrieved_chunks"]

    is_summary = state.get(
        "is_summary_request",
        False,
    )

    print(
        f"[synthesis_node] generating "
        f"{'summary' if is_summary else 'answer'} "
        f"from {len(chunks)} chunks"
    )

    try:

        # -----------------------------------------------------------
        # Document summary path
        # -----------------------------------------------------------

        if is_summary:

            answer = summarize_document(chunks)

        # -----------------------------------------------------------
        # Normal RAG answer path
        # -----------------------------------------------------------

        else:

            context = format_chunks_for_prompt(chunks)

            user_prompt = f"""
SOURCE CONTEXT:

{context}

USER QUESTION:

{query}

Answer the user's question using ONLY the source context.
Follow all grounding and formatting rules from the system prompt.
"""

            response = _create_chat_completion(
                messages=[
                    {
                        "role": "system",
                        "content": SYSTEM_PROMPT,
                    },
                    {
                        "role": "user",
                        "content": user_prompt,
                    },
                ],
                temperature=0.2,
                max_tokens=1000,
                **GPT_OSS_GENERATION_KWARGS,
            )

            answer = _get_response_text(response)

        rate_limited = False

    except RateLimitError as error:

        print(
            f"[synthesis_node] RATE LIMIT hit — "
            f"answer generation failed: {error}"
        )

        answer = (
            "SYNTHESIS FAILED — Groq rate limit reached "
            "before an answer could be generated."
        )

        rate_limited = True


    print(
        f"[synthesis_node] answer preview: "
        f"{answer[:200]}..."
    )


    return {
        "synthesis_output": answer,
        "rate_limited": rate_limited,

        # Preserve the previous state value before this node's output
        # is applied by LangGraph.
        "previous_answer": state.get(
            "synthesis_output",
            "",
        ),
    }


# -------------------------------------------------------------------
# Streaming synthesis
# -------------------------------------------------------------------

def synthesize_stream(
    query: str,
    chunks: list[dict],
):
    """
    Streaming version of normal synthesis.

    Uses the same model fallback order, prompt, reasoning configuration,
    and output limits as synthesis_node().
    """

    context = format_chunks_for_prompt(chunks)

    user_prompt = f"""
SOURCE CONTEXT:

{context}

USER QUESTION:

{query}

Answer the user's question using ONLY the source context.
Follow all grounding and formatting rules from the system prompt.
"""

    stream = _create_chat_completion(
        messages=[
            {
                "role": "system",
                "content": SYSTEM_PROMPT,
            },
            {
                "role": "user",
                "content": user_prompt,
            },
        ],
        temperature=0.2,
        max_tokens=1000,
        stream=True,
        **GPT_OSS_GENERATION_KWARGS,
    )

    for chunk in stream:

        delta = chunk.choices[0].delta.content

        if delta:
            yield delta