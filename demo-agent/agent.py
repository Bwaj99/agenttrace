"""
AgentTrace demo agent.

A standalone 3-step agent, fully instrumented with the agenttrace-sdk
so running it populates real trace data for the dashboard:

    1. search      - retrieve information about a topic (a hardcoded
                      stub — no search API key required)
    2. summarize   - call an LLM to summarize the search results
    3. write_file  - write the summary to a local output file

Works with either OPENAI_API_KEY or ANTHROPIC_API_KEY, whichever is
set (OpenAI takes priority if both are). If neither is set, it falls
back to a clearly-labeled mock response instead of failing outright —
so the whole pipeline (agent -> SDK -> SQLite -> dashboard) can be
verified with zero external setup; set a real key to see real output.

Run directly:

    python agent.py "some topic"

Or via Docker Compose (a one-off command, not a long-running service):

    docker compose run demo-agent "some topic"
"""

import os
import re
import sys
from types import SimpleNamespace
from typing import Optional, Tuple

from agenttrace import Tracer, trace_step

DB_PATH = os.environ.get("AGENTTRACE_DB_PATH", "../agenttrace.db")
OUTPUT_DIR = os.environ.get("AGENTTRACE_OUTPUT_DIR", "./output")

OPENAI_MODEL = os.environ.get("AGENTTRACE_OPENAI_MODEL", "gpt-4o-mini")
ANTHROPIC_MODEL = os.environ.get("AGENTTRACE_ANTHROPIC_MODEL", "claude-3-5-sonnet-20241022")


def _get_provider_and_client() -> Tuple[str, Optional[object]]:
    """Pick ONE provider based on what's configured in the environment
    — not over-engineering multi-provider support, just choosing
    between the two the product spec allows for. Falls back to a mock
    "offline" provider (same response shape as OpenAI's) if neither
    key is set, so the demo still produces a full, real trace."""
    if os.environ.get("OPENAI_API_KEY"):
        from openai import OpenAI

        return "openai", OpenAI()
    if os.environ.get("ANTHROPIC_API_KEY"):
        import anthropic

        return "anthropic", anthropic.Anthropic()

    print(
        "[demo-agent] WARNING: no OPENAI_API_KEY or ANTHROPIC_API_KEY set — "
        "using a mocked LLM response. Set one of them (see .env.example) "
        "to get a real summary.",
        file=sys.stderr,
    )
    return "mock", None


def _mock_llm_response(prompt: str):
    """A response shaped like OpenAI's, so the rest of the pipeline
    (usage extraction, output parsing) doesn't need a special case."""
    fake_summary = (
        "[mocked summary — no LLM API key was configured] "
        "Based on the retrieved results, this topic is an active area "
        "with growing tooling support, and the main open challenges are "
        "around observability, debugging, and reproducibility."
    )
    return SimpleNamespace(
        model="mock-offline-model",
        choices=[SimpleNamespace(message=SimpleNamespace(content=fake_summary))],
        usage=SimpleNamespace(
            prompt_tokens=len(prompt.split()),
            completion_tokens=len(fake_summary.split()),
        ),
    )


def _call_llm(provider: str, client, prompt: str):
    """Calls the configured provider and returns its *raw* response
    object — returning the raw object (rather than pre-extracting text)
    is what lets `@trace_step` auto-detect token usage on this call."""
    if provider == "openai":
        return client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[{"role": "user", "content": prompt}],
        )
    if provider == "anthropic":
        return client.messages.create(
            model=ANTHROPIC_MODEL,
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )
    return _mock_llm_response(prompt)


def _extract_text(provider: str, response) -> str:
    """Anthropic's response shape differs from OpenAI's; the mock
    response reuses OpenAI's shape, so it falls through to that branch."""
    if provider == "anthropic":
        return "".join(getattr(block, "text", "") for block in response.content)
    return response.choices[0].message.content


def _build_prompt(topic: str, results: list[str]) -> str:
    bullet_list = "\n".join(f"- {r}" for r in results)
    return (
        "You are a research assistant. Summarize the following search "
        f"results about '{topic}' into a concise 3-4 sentence summary "
        "for someone who knows nothing about the topic yet.\n\n"
        f"{bullet_list}"
    )


@trace_step(name="search", step_type="tool_call")
def search_step(topic: str) -> list[str]:
    """
    Mocked search/retrieval step. Swap this out for a real search API
    (Tavily, SerpAPI, Bing, ...) if you have a key for one — kept as a
    hardcoded stub here so the demo has zero external dependencies
    beyond the LLM call itself.
    """
    return [
        f"{topic} is an actively developing area with growing tooling and community interest.",
        f"Recent work on {topic} focuses on practical reliability, not just raw capability.",
        f"A common challenge in {topic} is observability: understanding *why* a run failed.",
    ]


@trace_step(name="write_file", step_type="tool_call")
def write_file_step(topic: str, summary: str) -> str:
    """Writes the summary to a local Markdown file and returns its path."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    safe_name = re.sub(r"[^a-zA-Z0-9_-]+", "_", topic.strip().lower())[:50] or "summary"
    path = os.path.join(OUTPUT_DIR, f"{safe_name}.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write(f"# Summary: {topic}\n\n{summary}\n")
    return path


def run_agent(topic: str) -> str:
    provider, client = _get_provider_and_client()
    tracer = Tracer(db_path=DB_PATH)

    # Defined here (rather than at module scope) so it closes over
    # `provider`/`client` without putting them in the traced input —
    # only `prompt` is part of this function's signature, so that's
    # all @trace_step captures as the step's recorded input.
    @trace_step(name="summarize", step_type="llm_call")
    def summarize_step(prompt: str):
        return _call_llm(provider, client, prompt)

    with tracer.start_run(name=f"demo-agent: {topic}", metadata={"topic": topic, "provider": provider}):
        results = search_step(topic)
        prompt = _build_prompt(topic, results)
        response = summarize_step(prompt)
        summary_text = _extract_text(provider, response)
        output_path = write_file_step(topic, summary_text)

    print(f"[demo-agent] provider: {provider}")
    print(f"[demo-agent] summary written to: {output_path}")
    print(f"[demo-agent] trace written to: {DB_PATH}")
    return output_path


if __name__ == "__main__":
    topic_arg = " ".join(sys.argv[1:]) or "LLM agent observability"
    run_agent(topic_arg)
