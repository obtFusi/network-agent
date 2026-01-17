# Network Agent Appliance Build System
# Usage: make build | make validate | make docker-test | make clean

.PHONY: all build validate docker-test docker-up docker-down clean help

VERSION ?= 0.4.0

# Default target
all: validate build

# Build the qcow2 image
build: validate
	@echo "=== Building qcow2 Image ==="
	cd packer && packer init .
	cd packer && packer build -var "version=$(VERSION)" network-agent.pkr.hcl
	@echo "=== Build complete ==="
	@ls -lh packer/output/*.qcow2 2>/dev/null || true

# Validate Packer template and Docker Compose
validate:
	@echo "=== Validating Packer template ==="
	cd packer && packer validate network-agent.pkr.hcl
	@echo "=== Validating Docker Compose files ==="
	docker compose -f docker/docker-compose.yml config > /dev/null
	docker compose -f docker/docker-compose.yml -f docker/docker-compose.scan-mode.yml config > /dev/null
	docker compose -f docker/docker-compose.yml -f docker/docker-compose.online.yml config > /dev/null
	@echo "=== Validation complete ==="

# Compress and split the image (for GitHub release)
package: build
	@echo "=== Packaging for release ==="
	cd packer/output && \
		zstd -19 --long=31 -T0 network-agent-$(VERSION).qcow2 -o network-agent-$(VERSION).qcow2.zst && \
		split -b 1900M -a 2 network-agent-$(VERSION).qcow2.zst network-agent-$(VERSION).qcow2.zst.part- && \
		for f in *.part-[0-9][0-9]; do \
			num="$${f##*.part-}"; \
			first=$$(printf "\\x$$(printf '%02x' $$((97 + 10#$$num / 26)))"); \
			second=$$(printf "\\x$$(printf '%02x' $$((97 + 10#$$num % 26)))"); \
			mv "$$f" "$${f%.part-*}.part-$${first}$${second}"; \
		done && \
		rm -f network-agent-$(VERSION).qcow2.zst && \
		sha256sum *.part-* > SHA256SUMS
	@echo "=== Package complete ==="
	@ls -lh packer/output/*.part-* packer/output/SHA256SUMS

# Test Docker Compose locally
docker-test:
	@echo "=== Testing Docker Compose ==="
	docker compose -f docker/docker-compose.yml config
	@echo "=== Building net-agent image ==="
	docker compose -f docker/docker-compose.yml build
	@echo "=== Docker test complete ==="

# Start Docker Compose stack locally (requires .env)
docker-up:
	@echo "=== Starting Docker Compose stack ==="
	@if [ ! -f docker/.env ]; then \
		echo "Creating test .env file..."; \
		echo "POSTGRES_USER=agent" > docker/.env; \
		echo "POSTGRES_PASSWORD=testpassword123" >> docker/.env; \
		echo "BASIC_AUTH_USER=admin" >> docker/.env; \
		echo 'BASIC_AUTH_HASH=$$2a$$14$$test' >> docker/.env; \
	fi
	docker compose -f docker/docker-compose.yml up -d
	@echo "=== Stack is starting ==="
	docker compose -f docker/docker-compose.yml ps

# Start with host network (scan mode)
docker-up-scan:
	@echo "=== Starting with host network (scan mode) ==="
	docker compose -f docker/docker-compose.yml -f docker/docker-compose.scan-mode.yml up -d
	docker compose -f docker/docker-compose.yml -f docker/docker-compose.scan-mode.yml ps

# Start with SearXNG (online mode)
docker-up-online:
	@echo "=== Starting with SearXNG (online mode) ==="
	docker compose -f docker/docker-compose.yml -f docker/docker-compose.online.yml up -d
	docker compose -f docker/docker-compose.yml -f docker/docker-compose.online.yml ps

# Stop Docker Compose stack
docker-down:
	@echo "=== Stopping Docker Compose stack ==="
	docker compose -f docker/docker-compose.yml down
	@echo "=== Stack stopped ==="

# View logs
docker-logs:
	docker compose -f docker/docker-compose.yml logs -f

# Clean build artifacts
clean:
	@echo "=== Cleaning build artifacts ==="
	rm -rf packer/output
	rm -f packer/packer_cache/*
	docker compose -f docker/docker-compose.yml down -v --rmi local 2>/dev/null || true
	@echo "=== Clean complete ==="

# Make scripts executable
fix-perms:
	chmod +x scripts/*.sh
	chmod +x packer/scripts/*.sh

# Show help
help:
	@echo "Network Agent Appliance Build System"
	@echo ""
	@echo "Usage: make <target> [VERSION=x.x.x]"
	@echo ""
	@echo "Build Targets:"
	@echo "  build        Build qcow2 image with embedded LLM (~22GB)"
	@echo "  validate     Validate Packer and Docker Compose files"
	@echo "  package      Compress and split image for GitHub release"
	@echo "  clean        Remove build artifacts"
	@echo ""
	@echo "Docker Targets:"
	@echo "  docker-test      Validate and build Docker images"
	@echo "  docker-up        Start stack (default mode)"
	@echo "  docker-up-scan   Start with host network (L2/L3 scans)"
	@echo "  docker-up-online Start with SearXNG (web search)"
	@echo "  docker-down      Stop stack"
	@echo "  docker-logs      Follow logs"
	@echo ""
	@echo "Utility:"
	@echo "  fix-perms    Make scripts executable"
	@echo ""
	@echo "Requirements:"
	@echo "  - Packer >= 1.11.0"
	@echo "  - Docker with Compose plugin"
	@echo "  - KVM/QEMU for image build"
	@echo "  - ~32GB RAM for full build"
	@echo "  - ~150GB disk space"
