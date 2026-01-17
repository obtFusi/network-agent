# Network Agent Appliance Container
# Builds from local source code (not PyPI)
#
# Build context must be repo root:
#   docker build -f infrastructure/docker/net-agent/Dockerfile -t network-agent .

FROM python:3.12-slim-bookworm

# Install network scanning tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    nmap \
    masscan \
    netcat-openbsd \
    iputils-ping \
    net-tools \
    curl \
    jq \
    && rm -rf /var/lib/apt/lists/*

# Create app directory
WORKDIR /app

# Copy requirements first (better layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY cli.py .
COPY agent/ ./agent/
COPY tools/ ./tools/
COPY config/ ./config/

# Create data volume mount point
VOLUME /app/data

# Expose web interface port
EXPOSE 8080

# Note: network-agent currently only supports REPL mode
# TODO: Add HTTP server mode for appliance use-case
# For now, this container is meant to be run interactively:
#   docker run -it --rm network-agent
# or with a specific command via stdin

# Default: interactive REPL mode
CMD ["python", "cli.py"]
