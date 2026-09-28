"""Quick end-to-end API validation."""
import requests

BASE = "http://localhost:8000"

# Health check
r = requests.get(f"{BASE}/health")
print("=== HEALTH ===")
print(r.json())
print()

# Normal transaction
normal = {
    "transaction_id": "txn_normal_001",
    "user_id": "user_1001",
    "amount": 2500,
    "timestamp": "2026-09-18T14:30:00Z",
    "merchant_id": "merchant_001",
    "device_id": "device_normal_01",
    "ip_address": "172.16.0.1",
    "location_lat": 12.9716,
    "location_long": 77.5946,
}
r = requests.post(f"{BASE}/v1/transactions", json=normal)
d = r.json()
print("=== NORMAL TRANSACTION ===")
print(f"Decision: {d['decision']}")
print(f"ML Risk: {d['ml_risk_score']:.1%}")
print(f"Graph Penalty: {d['graph_penalty']}")
print(f"Reasons: {[rc['code'] for rc in d['reason_codes']]}")
print(f"New Device: {d['features']['is_new_device']}")
print(f"Speed: {d['features']['speed_kmh']} km/h")
print()

# Fraudulent transaction
fraud = {
    "transaction_id": "txn_fraud_001",
    "user_id": "user_1001",
    "amount": 85000,
    "timestamp": "2026-09-18T15:00:00Z",
    "merchant_id": "merchant_002",
    "device_id": "device_suspicious_01",
    "ip_address": "10.10.10.10",
    "location_lat": 28.7041,
    "location_long": 77.1025,
}
r2 = requests.post(f"{BASE}/v1/transactions", json=fraud)
d2 = r2.json()
print("=== FRAUD TRANSACTION ===")
print(f"Decision: {d2['decision']}")
print(f"ML Risk: {d2['ml_risk_score']:.1%}")
print(f"Graph Penalty: {d2['graph_penalty']}")
print(f"Reasons: {[rc['code'] for rc in d2['reason_codes']]}")
print(f"Graph nodes: {len(d2['graph']['nodes'])}")
print(f"Summary: {d2['investigator_summary'][:200]}")
print()

# Model info
r3 = requests.get(f"{BASE}/v1/model/info")
print("=== MODEL INFO ===")
print(r3.json())
