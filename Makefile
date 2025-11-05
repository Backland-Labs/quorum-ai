.PHONY: help build up down logs status test verify run clean

PROFILE ?= fork

help:
	@echo "Quorum AI Testing Commands"
	@echo ""
	@echo "  make build      - Build Docker image"
	@echo "  make up         - Build and start services (default: fork mode)"
	@echo "  make down       - Stop services"
	@echo "  make logs       - Show live logs"
	@echo "  make status     - Show service status"
	@echo "  make test       - Run health check"
	@echo "  make verify     - Verify attestation count"
	@echo "  make run        - Run agent (existing endpoint)"
	@echo "  make clean      - Stop and remove all data"
	@echo ""
	@echo "Set PROFILE=mock|fork|testnet to change mode"

build:
	./scripts/quorum $(PROFILE) build

up:
	./scripts/quorum $(PROFILE) up

down:
	./scripts/quorum $(PROFILE) down

logs:
	./scripts/quorum $(PROFILE) logs

status:
	./scripts/quorum $(PROFILE) status

test:
	./scripts/quorum $(PROFILE) test

verify:
	./scripts/quorum $(PROFILE) verify

run:
	./scripts/quorum $(PROFILE) run

clean: down
	rm -rf logs/* store/* .anvil.pid
