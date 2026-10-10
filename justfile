set shell := ["bash", "-cu"]

# Default recipe: show available commands
default:
    @just --list

# Install dependencies and pre-commit hooks
setup:
    uv sync --all-extras --dev
    uv run pre-commit install

# Run all local verification steps
verify:
    uv run ruff check src tests
    uv run ruff format --check src tests
    uv run pyright src tests
    uv run pytest --cov=src --cov-branch --cov-report=term-missing --cov-fail-under=85

# Terraform dry-run
plan:
    cd infra/terraform && terraform fmt -check && terraform validate && terraform plan -input=false

# Terraform apply (requires explicit human approval)
apply:
    cd infra/terraform && terraform apply -input=false

# Run the capacity runner (dry-run by default)
capacity:
    uv run python -m hypercube.capacity --dry-run

# Destroy infrastructure (requires explicit human approval)
destroy:
    cd infra/terraform && terraform destroy
