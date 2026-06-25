.PHONY: help start stop restart demo test clean ui logs

help: ## Show this help message
	@echo "🎮 DayZ HiveAPI - Quick Commands"
	@echo ""
	@echo "Usage: make [target]"
	@echo ""
	@echo "Targets:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

start: ## Start the full stack (backend + database + monitoring)
	@echo "🚀 Starting HiveAPI stack..."
	cd hiveapi/ops && docker compose up -d --build
	@echo "✅ Stack started!"
	@echo ""
	@echo "   API:        http://localhost:8000"
	@echo "   API Docs:   http://localhost:8000/docs"
	@echo "   Health:     http://localhost:8000/health"
	@echo "   Prometheus: http://localhost:9090"
	@echo "   Grafana:    http://localhost:3000"
	@echo ""
	@echo "💡 Run 'make demo' to create demo data"
	@echo "💡 Run 'make ui' to start the web dashboard"

stop: ## Stop the full stack
	@echo "🛑 Stopping HiveAPI stack..."
	cd hiveapi/ops && docker compose down
	@echo "✅ Stack stopped!"

restart: ## Restart the full stack
	@echo "🔄 Restarting HiveAPI stack..."
	cd hiveapi/ops && docker compose restart
	@echo "✅ Stack restarted!"

demo: ## Create demo data
	@echo "🎲 Creating demo data..."
	cd hiveapi && python scripts/demo_seed.py
	@echo ""
	@echo "✅ Demo data created!"
	@echo "💡 Open http://localhost:3000 to see the dashboard"

test: ## Run the test suite
	@echo "🧪 Running tests..."
	cd hiveapi && pytest -v
	@echo "✅ Tests complete!"

ui: ## Start the web UI (development mode)
	@echo "🎨 Starting web UI..."
	@echo "💡 Make sure the backend is running (make start)"
	cd web-ui && npm install && npm run dev

logs: ## Show logs from all services
	cd hiveapi/ops && docker compose logs -f

clean: ## Clean up Docker volumes and containers
	@echo "🧹 Cleaning up..."
	cd hiveapi/ops && docker compose down -v
	@echo "✅ Cleanup complete!"

all: start demo ## Start everything and create demo data
	@echo ""
	@echo "🎉 Everything is ready!"
	@echo ""
	@echo "   Backend:    http://localhost:8000"
	@echo "   Dashboard:  Run 'make ui' to start"
	@echo ""
	@echo "💡 Run 'make test' to run the test suite"

status: ## Check status of all services
	@echo "📊 Service Status:"
	cd hiveapi/ops && docker compose ps

shell: ## Open a shell in the API container
	cd hiveapi/ops && docker compose exec api /bin/bash

db-shell: ## Open a PostgreSQL shell
	cd hiveapi/ops && docker compose exec db psql -U postgres -d hive

redis-cli: ## Open Redis CLI
	cd hiveapi/ops && docker compose exec redis redis-cli

seed: ## Run basic seed script
	@echo "🌱 Running basic seed..."
	cd hiveapi && python scripts/seed.py

fresh: clean all ## Fresh start - clean everything and start from scratch
	@echo "✅ Fresh environment ready!"
