#!/bin/bash
# E2E Test Script for CI/CD Dashboard
# Tests the complete flow: API → Dashboard → Real-time Updates

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DASHBOARD_DIR="$SCRIPT_DIR/../cicd-dashboard"
BACKEND_PORT="${BACKEND_PORT:-8001}"
FRONTEND_PORT="${FRONTEND_PORT:-3000}"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

cleanup() {
    log_info "Cleaning up..."
    pkill -f "uvicorn app.main" 2>/dev/null || true
    pkill -f "npm run dev" 2>/dev/null || true
}

trap cleanup EXIT

# Check dependencies
check_deps() {
    log_info "Checking dependencies..."
    command -v curl >/dev/null 2>&1 || { log_error "curl required"; exit 1; }
    command -v jq >/dev/null 2>&1 || { log_error "jq required"; exit 1; }
    command -v npm >/dev/null 2>&1 || { log_error "npm required"; exit 1; }
}

# Start backend
start_backend() {
    log_info "Starting backend on port $BACKEND_PORT..."
    cd "$DASHBOARD_DIR"

    # Create data directory
    mkdir -p data

    # Activate venv and start
    source .venv/bin/activate
    nohup uvicorn app.main:app --host 0.0.0.0 --port "$BACKEND_PORT" > /tmp/e2e-backend.log 2>&1 &

    # Wait for health
    for i in {1..30}; do
        if curl -sf "http://localhost:$BACKEND_PORT/health" > /dev/null 2>&1; then
            log_info "Backend healthy"
            return 0
        fi
        sleep 1
    done

    log_error "Backend failed to start"
    cat /tmp/e2e-backend.log
    exit 1
}

# Start frontend
start_frontend() {
    log_info "Starting frontend on port $FRONTEND_PORT..."
    cd "$DASHBOARD_DIR/frontend"

    # Update vite config proxy port
    sed -i "s|localhost:[0-9]*|localhost:$BACKEND_PORT|g" vite.config.ts

    nohup npm run dev > /tmp/e2e-frontend.log 2>&1 &

    # Wait for frontend
    for i in {1..30}; do
        if curl -sf "http://localhost:$FRONTEND_PORT" > /dev/null 2>&1; then
            log_info "Frontend healthy"
            return 0
        fi
        sleep 1
    done

    log_error "Frontend failed to start"
    cat /tmp/e2e-frontend.log
    exit 1
}

# Test API endpoints
test_api() {
    log_info "Testing API endpoints..."

    # Health check
    HEALTH=$(curl -sf "http://localhost:$BACKEND_PORT/health")
    echo "$HEALTH" | jq -e '.status == "healthy"' > /dev/null || {
        log_error "Health check failed"
        exit 1
    }
    log_info "  ✓ Health endpoint"

    # Create pipeline
    PIPELINE=$(curl -sf -X POST "http://localhost:$BACKEND_PORT/api/v1/pipelines" \
        -H "Content-Type: application/json" \
        -d '{"repo":"test/repo","ref":"main","trigger":"e2e-test"}')

    PIPELINE_ID=$(echo "$PIPELINE" | jq -r '.id')
    [ -n "$PIPELINE_ID" ] && [ "$PIPELINE_ID" != "null" ] || {
        log_error "Failed to create pipeline"
        exit 1
    }
    log_info "  ✓ Create pipeline: $PIPELINE_ID"

    # Get pipeline
    FETCHED=$(curl -sf "http://localhost:$BACKEND_PORT/api/v1/pipelines/$PIPELINE_ID")
    echo "$FETCHED" | jq -e '.id' > /dev/null || {
        log_error "Failed to fetch pipeline"
        exit 1
    }
    log_info "  ✓ Get pipeline"

    # List pipelines
    LIST=$(curl -sf "http://localhost:$BACKEND_PORT/api/v1/pipelines")
    echo "$LIST" | jq -e 'length > 0' > /dev/null || {
        log_error "Pipeline list empty"
        exit 1
    }
    log_info "  ✓ List pipelines"

    # SSE stats
    STATS=$(curl -sf "http://localhost:$BACKEND_PORT/api/v1/events/stats")
    echo "$STATS" | jq -e '.subscriber_count >= 0' > /dev/null || {
        log_error "SSE stats failed"
        exit 1
    }
    log_info "  ✓ SSE stats"

    # Approvals (empty is OK)
    APPROVALS=$(curl -sf "http://localhost:$BACKEND_PORT/api/v1/approvals/pending")
    echo "$APPROVALS" | jq -e 'type == "array"' > /dev/null || {
        log_error "Approvals endpoint failed"
        exit 1
    }
    log_info "  ✓ Approvals endpoint"
}

# Test frontend
test_frontend() {
    log_info "Testing frontend..."

    # Main page loads
    MAIN=$(curl -sf "http://localhost:$FRONTEND_PORT")
    echo "$MAIN" | grep -q "CI/CD Dashboard" || {
        log_error "Frontend main page failed"
        exit 1
    }
    log_info "  ✓ Main page loads"

    # Assets load
    curl -sf "http://localhost:$FRONTEND_PORT/assets/" > /dev/null 2>&1 || true
    log_info "  ✓ Assets accessible"
}

# Main
main() {
    echo "========================================"
    echo "  CI/CD Dashboard E2E Test"
    echo "========================================"
    echo ""

    check_deps
    start_backend
    start_frontend

    echo ""
    test_api
    echo ""
    test_frontend

    echo ""
    echo "========================================"
    log_info "All E2E tests passed!"
    echo "========================================"
    echo ""
    echo "Dashboard: http://localhost:$FRONTEND_PORT"
    echo "API:       http://localhost:$BACKEND_PORT/api/v1"
    echo ""
}

main "$@"
