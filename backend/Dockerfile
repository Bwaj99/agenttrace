# AgentTrace backend image.
#
# Installs agenttrace-sdk from the local sdk/ directory (copied in via
# the docker-compose.yml build context, which is the repo root — see
# `context: .` / `dockerfile: backend/Dockerfile` there) so the
# backend's models.py can `from agenttrace.models import ...` and stay
# in lockstep with the SDK's schema.

FROM python:3.11-slim

WORKDIR /app

# SDK first (rarely changes) so its install layer caches well.
COPY sdk/ /sdk/
RUN pip install --no-cache-dir /sdk

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ .

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
