# Real-Time Fraud Detection & Investigation Platform

A production-style MVP demonstrating real-time transaction fraud detection using ML, graph intelligence, and deterministic rules — with an explainable investigation dashboard.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    React Dashboard                          │
│  (Transaction Simulator • Risk Breakdown • Graph View)      │
└──────────────────────────┬──────────────────────────────────┘
                           │ REST API
┌──────────────────────────▼──────────────────────────────────┐
│                    FastAPI (app/main.py)                     │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│                  FraudService (orchestrator)                 │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐     │
│  │ FeatureStore│  │ GraphEngine │  │    MLEngine     │     │
│  │  (Redis)    │  │  (NetworkX) │  │ (XGBoost/ONNX) │     │
│  └──────┬──────┘  └──────┬──────┘  └────────┬────────┘     │
│         └────────────────┼──────────────────┘               │
│                          ▼                                   │
│                  Rule Engine (rules.py)                      │
│                          ▼                                   │
│              Investigator (investigator.py)                  │
│                          ▼                                   │
│               TransactionResponse                           │
└─────────────────────────────────────────────────────────────┘
         │                           │
    ┌────▼────┐              ┌───────▼───────┐
    │  Redis  │              │  Kafka (opt)  │
    └─────────┘              └───────────────┘
```

## Features

- **Real-time feature engineering** — velocity, amount aggregation, impossible travel detection via Redis
- **Graph-based risk analysis** — NetworkX entity-link graph with 2-hop neighborhood visualization
- **ML fraud scoring** — XGBoost classifier with ONNX runtime support
- **Deterministic rule engine** — combines ML + graph + velocity into explainable decisions
- **Reason codes** — every decision comes with severity-tagged reasons
- **AI Investigator** — natural language summary (template fallback when no LLM API key)
- **React dashboard** — live risk breakdown, Cytoscape investigation graph, transaction simulator
- **Kafka-ready** — optional event publishing for transaction-events and fraud-decisions topics
- **Docker Compose** — single command to start everything

## Tech Stack

| Layer | Technology |
|-------|-----------|
| API | FastAPI, Pydantic, Uvicorn |
| Feature Store | Redis (sorted sets), in-memory fallback |
| ML | XGBoost, ONNX Runtime, scikit-learn |
| Graph | NetworkX |
| Events | Kafka (optional) |
| Frontend | React, Vite, Tailwind CSS, Cytoscape.js |
| Infra | Docker Compose, Python 3.11 |

## Project Structure

```
fraud-detection-engine/
├── app/
│   ├── main.py              # FastAPI routes
│   ├── config.py             # Environment-based configuration
│   ├── schemas.py            # Pydantic models
│   ├── feature_store.py      # Redis feature engineering
│   ├── graph_engine.py       # NetworkX graph analysis
│   ├── ml_engine.py          # XGBoost/ONNX inference
│   ├── rules.py              # Deterministic decision engine
│   ├── investigator.py       # AI summary generation
│   ├── kafka_producer.py     # Optional Kafka publishing
│   ├── logging_config.py     # Structured logging
│   ├── services/
│   │   └── fraud_service.py  # Pipeline orchestrator
│   └── dashboard/            # React frontend
├── scripts/
│   ├── train_model.py        # Model training
│   └── generate_transactions.py  # Mock data generator
├── tests/
│   ├── test_features.py
│   ├── test_rules.py
│   ├── test_graph.py
│   └── test_api.py
├── models/                   # Trained model artifacts
├── docker-compose.yml
├── Dockerfile
├── Makefile
└── requirements.txt
```

## Installation

### Prerequisites

- Python 3.11+
- Node.js 18+
- Docker & Docker Compose (optional)

### Local Development

```bash
# Clone and enter directory
git clone https://github.com/yourusername/fraud-detection-engine.git
cd fraud-detection-engine

# Create virtual environment
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # Linux/Mac

# Install dependencies
pip install -r requirements.txt

# Copy environment config
cp .env.example .env

# Train the model
python scripts/train_model.py

# Run the API
uvicorn app.main:app --reload --port 8000

# In another terminal, run the frontend
cd app/dashboard
npm install
npm run dev
```

### Docker Setup

```bash
docker compose up --build
```

Services:
- API: http://localhost:8000
- Dashboard: http://localhost:3000
- Redis: localhost:6379
- Kafka: localhost:9092

## Training the Model

```bash
python scripts/train_model.py
```

Output:
- `models/fraud_model.pkl` (XGBoost native)
- `models/fraud_model.onnx` (ONNX export)
- Classification report with precision, recall, F1, ROC-AUC

## Running Mock Transactions

```bash
# Single scenario
python scripts/generate_transactions.py --scenario impossible_travel --count 5

# All scenarios
python scripts/generate_transactions.py --all
```

Scenarios: `normal_user`, `high_velocity`, `new_device`, `impossible_travel`, `suspicious_device`, `suspicious_ip`, `high_amount`

## API Examples

### Process Transaction

```bash
curl -X POST http://localhost:8000/v1/transactions \
  -H "Content-Type: application/json" \
  -d '{
    "transaction_id": "txn_demo_001",
    "user_id": "user_1001",
    "amount": 85000,
    "timestamp": "2026-09-18T14:30:00Z",
    "merchant_id": "merchant_001",
    "device_id": "device_suspicious_01",
    "ip_address": "10.10.10.10",
    "location_lat": 12.9716,
    "location_long": 77.5946
  }'
```

### Response

```json
{
  "transaction_id": "txn_demo_001",
  "decision": "INVESTIGATION_REQUIRED",
  "ml_risk_score": 0.974,
  "graph_penalty": 80,
  "features": {
    "account_velocity_1h": 7,
    "amount_sum_24h": 125000,
    "is_new_device": true,
    "speed_kmh": 1240
  },
  "reason_codes": [...],
  "graph": { "nodes": [...], "edges": [...] },
  "investigator_summary": "..."
}
```

### Health Check

```bash
curl http://localhost:8000/health
```

### Model Info

```bash
curl http://localhost:8000/v1/model/info
```

## ML Approach

### Features

| Feature | Description |
|---------|-------------|
| `amount` | Transaction amount in INR |
| `account_velocity_1h` | Transaction count in last hour |
| `amount_sum_24h` | Total amount in last 24 hours |
| `speed_kmh` | Travel speed from previous location |
| `is_new_device` | Whether device is seen for first time |

### Model

- **Algorithm**: XGBoost classifier
- **Training**: Synthetic data with realistic fraud correlations
- **Evaluation**: Precision, Recall, F1, ROC-AUC (not accuracy)
- **Inference**: ONNX Runtime preferred, XGBoost native fallback

### Fraud Decision Logic

```
IF ml_risk_score > 0.85
   OR speed_kmh > 800
   OR graph_penalty > 70
THEN: INVESTIGATION_REQUIRED
ELSE: APPROVED
```

## Graph Intelligence

- **Nodes**: USER, DEVICE, IP
- **Edges**: USES, CONNECTED_FROM, SEEN_WITH, USED_BY
- **Suspicious entity detection**: configurable lists for flagged devices/IPs/users
- **Graph penalty**: accumulates based on suspicious connections (capped at 100)
- **2-hop neighborhood**: exported for frontend Cytoscape visualization

## AI Investigator

Transforms structured fraud signals into a natural-language summary:

> "Transaction ₹85,000 from a new device was detected 1,240 km from the user's previous transaction within 18 minutes. The device is linked to 3 previously flagged accounts."

- **Template fallback**: deterministic when no LLM API key is set
- **LLM integration**: optional, set `LLM_API_KEY` in `.env`
- **Architecture**: Evidence → Summary (LLM never overrides the decision)

## Testing

```bash
pytest tests/ -v
```

Test coverage:
- Feature engineering (velocity, amount, new device, impossible travel)
- Rule engine (thresholds, multiple reasons, boundary cases)
- Graph engine (nodes, edges, penalties, 2-hop)
- API endpoints (validation, schema, health)

## Example Investigation

**Input**: ₹85,000 transaction from suspicious device, IP `10.10.10.10`, new device

**Output**:
- Decision: `INVESTIGATION_REQUIRED`
- ML Risk: 97.4%
- Graph Penalty: 80/100
- Reasons: `HIGH_ML_RISK`, `NEW_DEVICE`, `HIGH_GRAPH_RISK`, `SUSPICIOUS_DEVICE`
- Graph: USER → DEVICE (suspicious) → other flagged users
- Summary: "Transaction ₹85,000 from device_suspicious_01 was flagged..."

## Limitations

- **Synthetic data only** — model performance does NOT represent real-world fraud detection
- **In-memory graph** — NetworkX graph is lost on restart (production would use Neo4j/JanusGraph)
- **No authentication** — API is open (production would add OAuth2/JWT)
- **No persistence** — transaction history lives in Redis/memory (no database)
- **Single-node** — not horizontally scalable (Kafka enables future scaling)
- **Deterministic investigator** — template-based summary (add LLM API key for richer output)

## Recommended Next Improvements

1. Add PostgreSQL for transaction history persistence
2. Replace in-memory graph with Neo4j for production scale
3. Add Apache Kafka consumer for event-driven ingestion
4. Implement real-time model retraining pipeline
5. Add user authentication and RBAC
6. Deploy to Kubernetes with Prometheus metrics
7. Add A/B testing framework for model versions
8. Implement feedback loop for labeling investigation outcomes

## Why This Project Matters

This project demonstrates production engineering skills across the full ML systems stack:

| Skill | Where |
|-------|-------|
| Python | Core backend, all modules |
| FastAPI | REST API with OpenAPI docs |
| Pydantic | Input/output validation |
| Redis | Real-time feature store |
| NetworkX | Graph-based entity analysis |
| XGBoost / ONNX | ML model training & inference |
| Feature Engineering | Velocity, impossible travel, new device |
| Explainability | Reason codes, feature contributions |
| Kafka | Event architecture (optional) |
| React + Tailwind | Investigation dashboard |
| Cytoscape.js | Graph visualization |
| Docker | Containerized deployment |
| Testing | pytest with meaningful coverage |
| GenAI Architecture | Investigator module (template + LLM) |

Built as a portfolio project for Junior ML Engineer / GenAI Engineer / Data Scientist / AI Engineer / Backend Engineer roles.
