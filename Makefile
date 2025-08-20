# Video Description Generator Makefile

.PHONY: help setup clean test deploy destroy info

# Default environment
ENV ?= dev

# Colors for output
GREEN := \033[0;32m
YELLOW := \033[1;33m
RED := \033[0;31m
NC := \033[0m # No Color

help: ## Show this help message
	@echo "Video Description Generator - Available Commands"
	@echo "================================================"
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "$(GREEN)%-20s$(NC) %s\n", $$1, $$2}' $(MAKEFILE_LIST)

setup: ## Set up development environment
	@echo "$(YELLOW)Setting up development environment...$(NC)"
	@./scripts/setup-environment.sh

clean: ## Clean up temporary files and build artifacts
	@echo "$(YELLOW)Cleaning up temporary files...$(NC)"
	@find . -type f -name "*.pyc" -delete
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.zip" -path "./src/*" -delete
	@rm -f deployment-outputs-*.json
	@rm -rf .pytest_cache
	@rm -rf htmlcov
	@rm -f .coverage

install: ## Install Python dependencies
	@echo "$(YELLOW)Installing dependencies...$(NC)"
	@pip install -r requirements-dev.txt

test: ## Run tests
	@echo "$(YELLOW)Running tests...$(NC)"
	@python -m pytest tests/ -v --cov=src --cov-report=html

lint: ## Run code linting
	@echo "$(YELLOW)Running code linting...$(NC)"
	@black --check src/
	@flake8 src/
	@isort --check-only src/

format: ## Format code
	@echo "$(YELLOW)Formatting code...$(NC)"
	@black src/
	@isort src/

validate-terraform: ## Validate Terraform configuration
	@echo "$(YELLOW)Validating Terraform configuration...$(NC)"
	@cd terraform && terraform fmt -check
	@cd terraform && terraform validate

build-layers: ## Build Lambda layers
	@echo "$(YELLOW)Building Lambda layers...$(NC)"
	@cd src/layers && ./create-layer.sh

package: ## Package Lambda functions
	@echo "$(YELLOW)Packaging Lambda functions...$(NC)"
	@cd src/processors && zip -r package.zip . -x "__pycache__/*" "*.pyc" "tests/*"
	@cd src/handlers && zip -r package.zip . -x "__pycache__/*" "*.pyc" "tests/*"

deploy: build-layers package ## Deploy infrastructure and code
	@echo "$(YELLOW)Deploying to environment: $(ENV)$(NC)"
	@./scripts/deploy.sh $(ENV) deploy

update-code: package ## Update Lambda function code only
	@echo "$(YELLOW)Updating Lambda function code for environment: $(ENV)$(NC)"
	@./scripts/deploy.sh $(ENV) update-code

test-api: ## Test API endpoints
	@echo "$(YELLOW)Testing API endpoints for environment: $(ENV)$(NC)"
	@./scripts/test-api.sh "" basic

smoke-test: ## Run smoke tests
	@echo "$(YELLOW)Running smoke tests for environment: $(ENV)$(NC)"
	@./scripts/deploy.sh $(ENV) smoke-test

destroy: ## Destroy infrastructure
	@echo "$(RED)Destroying infrastructure for environment: $(ENV)$(NC)"
	@./scripts/deploy.sh $(ENV) destroy

info: ## Show deployment information
	@echo "$(YELLOW)Showing deployment info for environment: $(ENV)$(NC)"
	@./scripts/deploy.sh $(ENV) info

logs-processor: ## Show processor Lambda logs
	@echo "$(YELLOW)Showing processor Lambda logs...$(NC)"
	@aws logs tail "/aws/lambda/video-description-gen-$(ENV)-processor" --follow

logs-api: ## Show API Lambda logs
	@echo "$(YELLOW)Showing API Lambda logs...$(NC)"
	@aws logs tail "/aws/lambda/video-description-gen-$(ENV)-api" --follow

docs: ## Generate documentation
	@echo "$(YELLOW)Generating documentation...$(NC)"
	@mkdocs build

serve-docs: ## Serve documentation locally
	@echo "$(YELLOW)Serving documentation at http://localhost:8000$(NC)"
	@mkdocs serve

pre-commit: ## Run pre-commit checks
	@echo "$(YELLOW)Running pre-commit checks...$(NC)"
	@pre-commit run --all-files

init-dev: setup install ## Initialize development environment
	@echo "$(GREEN)Development environment initialized!$(NC)"
	@echo "Next steps:"
	@echo "1. Update terraform/environments/$(ENV).tfvars with your configuration"
	@echo "2. Run 'make deploy ENV=$(ENV)' to deploy the infrastructure"
	@echo "3. Run 'make test-api ENV=$(ENV)' to test the deployment"

# Environment-specific targets
deploy-dev: ## Deploy to development environment
	@$(MAKE) deploy ENV=dev

deploy-prod: ## Deploy to production environment
	@$(MAKE) deploy ENV=prod

test-dev: ## Test development environment
	@$(MAKE) test-api ENV=dev

test-prod: ## Test production environment  
	@$(MAKE) test-api ENV=prod

# CI/CD targets
ci-test: install lint test ## Run CI tests
	@echo "$(GREEN)All CI tests passed!$(NC)"

ci-deploy: build-layers package ## CI deployment
	@echo "$(YELLOW)Running CI deployment...$(NC)"
	@./scripts/deploy.sh $(ENV) deploy