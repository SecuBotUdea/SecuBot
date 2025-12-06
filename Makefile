# Makefile para SecuBot - Comandos de desarrollo

.PHONY: help install dev test clean lint format setup

# Variables
PYTHON := python3
PIP := pip3
PYTEST := pytest

help: ## Mostrar este mensaje de ayuda
	@echo "Comandos disponibles:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $1, $2}'

install: ## Instalar dependencias de producción
	$(PIP) install -e .

install-dev: ## Instalar dependencias de desarrollo
	$(PIP) install -e ".[dev]"

dev: ## Iniciar servidor de desarrollo local
	uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

test: ## Ejecutar tests
	$(PYTEST) tests/ -v

test-cov: ## Ejecutar tests con cobertura
	$(PYTEST) tests/ -v --cov=app --cov-report=html --cov-report=term-missing --cov-report=xml

test-watch: ## Ejecutar tests en modo watch
	$(PYTEST) tests/ -v -f

lint: ## Ejecutar linter (ruff)
	ruff check app/ tests/

lint-fix: ## Ejecutar linter y auto-corregir
	ruff check --fix app/ tests/

format: ## Formatear código
	ruff format app/ tests/

format-check: ## Verificar formato sin modificar
	ruff format --check app/ tests/

type-check: ## Verificar tipos con mypy
	mypy app/

check: lint format-check type-check test ## Ejecutar todas las verificaciones (CI local)

clean: ## Limpiar archivos temporales
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	rm -rf htmlcov/ coverage.xml
	rm -rf dist/ build/

seed-db: ## Cargar datos de prueba en la BD
	$(PYTHON) scripts/seed_db.py

reset-db: ## Resetear base de datos (¡CUIDADO!)
	$(PYTHON) scripts/reset_db.py

create-migration: ## Crear nueva migración
	@read -p "Nombre de la migración: " name; \
	$(PYTHON) scripts/create_migration.py "$name"

run-migrations: ## Ejecutar migraciones pendientes
	$(PYTHON) scripts/run_migrations.py

setup: ## Setup inicial del proyecto
	@echo "🚀 Configurando SecuBot..."
	$(PIP) install --upgrade pip
	$(PIP) install -e ".[dev]"
	@if [ ! -f .env ]; then \
		echo "📝 Creando archivo .env desde .env.example..."; \
		cp .env.example .env; \
		echo "⚠️  IMPORTANTE: Edita .env con tus configuraciones"; \
	fi
	@echo ""
	@echo "✅ Proyecto configurado exitosamente"
	@echo ""
	@echo "📋 Próximos pasos:"
	@echo "  1. Edita .env con tu MONGODB_URI"
	@echo "  2. Ejecuta 'make dev' para iniciar el servidor"
	@echo "  3. Visita http://localhost:8000/docs"
	@echo ""

health: ## Verificar que el servidor esté corriendo
	@curl -s http://localhost:8000/health || echo "❌ Servidor no está corriendo"

deps-update: ## Actualizar dependencias
	$(PIP) install --upgrade pip
	$(PIP) install --upgrade -e ".[dev]"

deps-list: ## Listar dependencias instaladas
	$(PIP) list

deps-tree: ## Mostrar árbol de dependencias
	$(PIP) install pipdeptree
	pipdeptree