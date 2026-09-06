# AgentTrace demo-agent image.
#
# Runs as a one-off (`docker compose run demo-agent "some topic"`),
# not a long-running service — see docker-compose.yml.

FROM python:3.11-slim

WORKDIR /app

COPY sdk/ /sdk/
RUN pip install --no-cache-dir /sdk

COPY demo-agent/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY demo-agent/ .

ENTRYPOINT ["python", "agent.py"]
