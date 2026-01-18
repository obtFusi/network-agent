# Network Agent - Docker Image
# Production-ready container for appliance deployment
#
# Build context: repo root
#   docker build -t network-agent .

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

# Default: HTTP API server mode for appliance
# For interactive CLI, run: docker run -it --rm network-agent python cli.py
CMD ["python", "cli.py", "--serve"]
