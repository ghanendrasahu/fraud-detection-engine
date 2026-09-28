.PHONY: install train run test docker-up docker-down lint format clean

install:
	pip install -r requirements.txt

train:
	python scripts/train_model.py

run:
	uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

test:
	pytest tests/ -v --tb=short

docker-up:
	docker compose up --build -d

docker-down:
	docker compose down

lint:
	ruff check app/ scripts/ tests/

format:
	ruff format app/ scripts/ tests/

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	rm -rf .pytest_cache htmlcov .coverage

mock-normal:
	python scripts/generate_transactions.py --scenario normal_user

mock-fraud:
	python scripts/generate_transactions.py --scenario impossible_travel

mock-all:
	python scripts/generate_transactions.py --all
