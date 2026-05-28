FROM python:3.11-slim

WORKDIR /app

# Install dependencies from both component requirements files
COPY agents/router/requirements.txt /tmp/requirements-router.txt
COPY agents/ads-agent/requirements.txt /tmp/requirements-ads-agent.txt
RUN pip install --no-cache-dir \
    -r /tmp/requirements-router.txt \
    -r /tmp/requirements-ads-agent.txt

# Copy source tree
COPY openclaw/ ./openclaw/
COPY agents/ ./agents/

# Run from the openclaw/ subdirectory so that sibling-module imports (e.g.
# "from openclaw import process_request") resolve against openclaw.py in the
# same directory, matching the local dev invocation pattern.
WORKDIR /app/openclaw

# Port exposed by default; Cloud Run overrides via PORT env var
EXPOSE 8100

# Run OpenClaw HTTP server; PORT defaults to 8100 if not set by the platform
CMD ["sh", "-c", "python -m uvicorn server:app --host 0.0.0.0 --port ${PORT:-8100}"]
