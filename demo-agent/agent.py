"""
AgentTrace demo agent.

A standalone script simulating a realistic 3-step agent, fully
instrumented with the agenttrace-sdk so running it populates real
trace data for the dashboard:

    1. search   - retrieve information about a given topic
                  (mocked/stubbed search if no search API key is set)
    2. summarize - call an LLM (OpenAI or Anthropic, whichever API
                   key is present in the environment) to summarize
                   the search results
    3. write_file - write the summary to a local output file

Run directly:

    python agent.py "some topic"

Or via Docker Compose (one-off, not a long-running service):

    docker compose run demo-agent "some topic"

Implemented in Phase 4.
"""

# TODO(Phase 4):
# - Instantiate a Tracer(db_path=...) and wrap the whole run in
#   tracer.start_run(name=f"demo-agent:{topic}").
# - @trace_step(name="search", step_type="tool_call") for the
#   search/retrieval step.
# - @trace_step(name="summarize", step_type="llm_call") for the LLM
#   call (auto-detects OpenAI/Anthropic response usage).
# - @trace_step(name="write_file", step_type="tool_call") for writing
#   the output file.
# - Pick ONE of OPENAI_API_KEY / ANTHROPIC_API_KEY based on what's set
#   in the environment; don't over-engineer multi-provider support.

if __name__ == "__main__":
    raise NotImplementedError("Demo agent will be implemented in Phase 4.")
