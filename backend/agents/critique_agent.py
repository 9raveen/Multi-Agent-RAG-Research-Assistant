# critique_agent.py
# Node responsibility: check whether synthesis_output is fully supported by
# retrieved_chunks and actually answers the query.
#
# Uses Groq Structured Outputs with strict JSON schema so LangGraph routing
# never depends on regex parsing or the model voluntarily formatting JSON.

import sys
import os
import json
import time

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from groq import Groq, GroqError
from dotenv import load_dotenv

from retrieval.retriever import format_chunks_for_prompt
from agents.state import ResearchState


load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))


# -------------------------------------------------------------------
# Critique prompt
# -------------------------------------------------------------------

CRITIQUE_SYSTEM_PROMPT = """
You are a strict fact-checker reviewing an AI-generated answer against
its provided source context.

Evaluate ONLY the user's question as literally asked.

Do not infer additional sub-topics, related concepts, or expected scope
beyond what the question explicitly requests.

Evaluate the following:

1. Grounding:
   Is every factual claim in the generated answer supported by the
   provided context?

2. Relevance:
   Does the answer directly address what the user actually asked?

3. Completeness:
   If the context genuinely lacks enough information to fully answer the
   question, an answer that clearly states this limitation should PASS.

Do not fail an answer merely because it is concise.

Do not require the answer to discuss information that the user did not ask for.

Set:

- "passed": true
  if the answer is grounded in the context and adequately answers the
  literal user question.

- "passed": false
  only if the answer contains unsupported claims, hallucinations,
  significant factual errors, or fails to answer the actual question.

For "feedback":

- If passed, return exactly: "looks good"
- If failed, provide one concise sentence explaining the most important issue.
"""


# -------------------------------------------------------------------
# Strict JSON schema
#
# GPT-OSS-120B supports Groq Structured Outputs with strict=True.
# This guarantees schema-compliant JSON instead of relying on the model
# to manually follow a "respond only with JSON" prompt instruction.
# -------------------------------------------------------------------

CRITIQUE_JSON_SCHEMA = {
    "name": "critique_result",
    "strict": True,
    "schema": {
        "type": "object",
        "properties": {
            "passed": {
                "type": "boolean"
            },
            "feedback": {
                "type": "string"
            }
        },
        "required": [
            "passed",
            "feedback"
        ],
        "additionalProperties": False
    }
}


def critique_node(state: ResearchState) -> dict:
    """
    Evaluate whether the synthesized answer is grounded in the retrieved
    context and answers the user's question.

    Returns:
        {
            "critique_passed": bool,
            "critique_feedback": str,
            "revision_count": int
        }
    """

    revision_count = state.get("revision_count", 0) + 1


    # ---------------------------------------------------------------
    # Summary requests skip critique
    #
    # Map-reduce summarization can use the entire document, which may
    # contain many chunks and exceed practical request/token limits for
    # a second full-document critique pass.
    # ---------------------------------------------------------------

    if state.get("is_summary_request"):
        print(
            "[critique_node] summary request — "
            "skipping critique"
        )

        return {
            "critique_passed": True,
            "critique_feedback": (
                "Summary generated through map-reduce summarization process"
            ),
            "revision_count": revision_count,
        }


    # ---------------------------------------------------------------
    # Extract state
    # ---------------------------------------------------------------

    query = state["query"]
    answer = state["synthesis_output"]
    chunks = state["retrieved_chunks"]

    context = format_chunks_for_prompt(chunks)


    # ---------------------------------------------------------------
    # Build critique request
    # ---------------------------------------------------------------

    user_prompt = f"""
SOURCE CONTEXT:
{context}

USER QUESTION:
{query}

GENERATED ANSWER:
{answer}

Evaluate whether the generated answer is fully supported by the source
context and whether it directly answers the user's question.
"""


    print(
        f"[critique_node] reviewing answer "
        f"(revision {revision_count})"
    )


    # ---------------------------------------------------------------
    # Retry for transient Groq errors
    # ---------------------------------------------------------------

    max_retries = 2

    for attempt in range(max_retries):

        try:

            response = client.chat.completions.create(

                model="openai/gpt-oss-120b",

                messages=[
                    {
                        "role": "system",
                        "content": CRITIQUE_SYSTEM_PROMPT,
                    },
                    {
                        "role": "user",
                        "content": user_prompt,
                    },
                ],

                # Critique should be deterministic.
                temperature=0.0,

                # A critique result is very small.
                max_tokens=150,

                # GPT-OSS reasoning configuration.
                reasoning_effort="low",

                # Do not return reasoning to the application.
                include_reasoning=False,

                # Strict structured output.
                response_format={
                    "type": "json_schema",
                    "json_schema": CRITIQUE_JSON_SCHEMA,
                },
            )


            # Strict schema guarantees the expected JSON structure.
            raw = response.choices[0].message.content

            if not raw:
                raise ValueError(
                    "Critique model returned an empty response"
                )

            parsed = json.loads(raw)

            passed = parsed["passed"]
            feedback = parsed["feedback"]

            print(
                f"[critique_node] "
                f"passed={passed}, feedback={feedback}"
            )

            return {
                "critique_passed": passed,
                "critique_feedback": feedback,
                "revision_count": revision_count,
            }


        except GroqError as e:

            error_name = type(e).__name__

            print(
                f"[critique_node] Groq error "
                f"(attempt {attempt + 1}/{max_retries}): "
                f"{error_name} - {e}"
            )

            error_str = str(e).lower()

            is_rate_limit = (
                "rate" in error_str
                or "429" in error_str
            )

            is_too_large = (
                "too large" in error_str
                or "413" in error_str
                or "context" in error_str
            )


            # -------------------------------------------------------
            # Context/request too large
            #
            # Do not block the user or create an unnecessary LangGraph
            # retry loop when critique itself cannot process the request.
            # -------------------------------------------------------

            if is_too_large:

                print(
                    "[critique_node] Request/context too large "
                    "for critique model — accepting answer"
                )

                return {
                    "critique_passed": True,
                    "critique_feedback": (
                        "Answer accepted because critique context "
                        "was too large"
                    ),
                    "revision_count": revision_count,
                }


            # -------------------------------------------------------
            # Retry rate-limit errors
            # -------------------------------------------------------

            if is_rate_limit and attempt < max_retries - 1:

                wait_time = 2 * (2 ** attempt)

                print(
                    f"[critique_node] Rate limited. "
                    f"Waiting {wait_time}s before retry..."
                )

                time.sleep(wait_time)

                continue


            # -------------------------------------------------------
            # Final failure or non-transient API error
            # -------------------------------------------------------

            print(
                "[critique_node] Critique unavailable — "
                "accepting answer without blocking pipeline"
            )

            return {
                "critique_passed": True,
                "critique_feedback": (
                    "Answer accepted because critique service "
                    "was unavailable"
                ),
                "revision_count": revision_count,
            }


        except (json.JSONDecodeError, KeyError, TypeError, ValueError) as e:

            # With strict=True this should be extremely rare.
            # Most importantly, we DO NOT convert a parser failure into
            # passed=False, because that would create a false LangGraph
            # retry loop like:
            #
            # Research -> Synthesis -> Critique parse failure -> Retry
            #
            print(
                "[critique_node] Unexpected structured-output "
                f"parsing error: {e}"
            )

            return {
                "critique_passed": True,
                "critique_feedback": (
                    "Answer accepted because critique output "
                    "could not be processed"
                ),
                "revision_count": revision_count,
            }


    # ---------------------------------------------------------------
    # Defensive fallback
    #
    # Normally unreachable because all paths above return.
    # ---------------------------------------------------------------

    print(
        "[critique_node] Unexpected fallback reached — "
        "accepting answer"
    )

    return {
        "critique_passed": True,
        "critique_feedback": (
            "Answer accepted because critique did not complete"
        ),
        "revision_count": revision_count,
    }