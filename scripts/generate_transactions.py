"""Generate mock transactions for testing the fraud detection system."""

from __future__ import annotations

import argparse
import json
import random
import sys
import time
import uuid
from datetime import datetime, timezone

import requests

API_URL = "http://localhost:8000/v1/transactions"

# City coordinates for realistic travel scenarios
CITIES = {
    "mumbai": (19.0760, 72.8777),
    "delhi": (28.7041, 77.1025),
    "bangalore": (12.9716, 77.5946),
    "chennai": (13.0827, 80.2707),
    "kolkata": (22.5726, 88.3639),
    "hyderabad": (17.3850, 78.4867),
    "pune": (18.5204, 73.8567),
    "jaipur": (26.9124, 75.7873),
}

SCENARIOS = {
    "normal_user": {
        "description": "Normal transaction from known device",
        "amount_range": (200, 15000),
        "device": "device_normal_01",
        "ip": "172.16.0.1",
        "city": "bangalore",
        "speed": 0,
    },
    "high_velocity": {
        "description": "Multiple rapid transactions",
        "amount_range": (1000, 50000),
        "device": "device_normal_02",
        "ip": "172.16.0.2",
        "city": "mumbai",
        "speed": 0,
    },
    "new_device": {
        "description": "Transaction from unknown device",
        "amount_range": (5000, 80000),
        "device": "device_new_unknown",
        "ip": "10.0.0.50",
        "city": "delhi",
        "speed": 0,
    },
    "impossible_travel": {
        "description": "Transaction from far away location quickly",
        "amount_range": (20000, 150000),
        "device": "device_normal_01",
        "ip": "172.16.0.1",
        "city": "chennai",  # Far from bangalore
        "speed": 1200,
    },
    "suspicious_device": {
        "description": "Transaction from known suspicious device",
        "amount_range": (30000, 200000),
        "device": "device_suspicious_01",
        "ip": "10.0.0.99",
        "city": "kolkata",
        "speed": 0,
    },
    "suspicious_ip": {
        "description": "Transaction from suspicious IP",
        "amount_range": (15000, 100000),
        "device": "device_normal_03",
        "ip": "10.10.10.10",
        "city": "hyderabad",
        "speed": 0,
    },
    "high_amount": {
        "description": "Very high value transaction",
        "amount_range": (100000, 500000),
        "device": "device_normal_01",
        "ip": "172.16.0.1",
        "city": "bangalore",
        "speed": 0,
    },
}


def generate_transaction(scenario: str, user_id: str = "user_1001") -> dict:
    """Generate a single mock transaction for the given scenario."""
    cfg = SCENARIOS[scenario]
    lat, lon = CITIES[cfg["city"]]
    amount = round(random.uniform(*cfg["amount_range"]), 2)

    return {
        "transaction_id": f"txn_{uuid.uuid4().hex[:12]}",
        "user_id": user_id,
        "amount": amount,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "merchant_id": f"merchant_{random.randint(100, 999)}",
        "device_id": cfg["device"],
        "ip_address": cfg["ip"],
        "location_lat": round(lat + random.uniform(-0.01, 0.01), 6),
        "location_long": round(lon + random.uniform(-0.01, 0.01), 6),
    }


def send_transaction(txn: dict) -> dict | None:
    """Send a transaction to the API and print the result."""
    try:
        resp = requests.post(API_URL, json=txn, timeout=10)
        resp.raise_for_status()
        result = resp.json()
        print(f"\n{'='*70}")
        print(f"Transaction: {result['transaction_id']}")
        print(f"Decision:    {result['decision']}")
        print(f"ML Risk:     {result['ml_risk_score']:.1%}")
        print(f"Graph Pen:   {result['graph_penalty']:.0f}/100")
        print(f"Reasons:     {len(result['reason_codes'])}")
        for rc in result["reason_codes"]:
            print(f"  [{rc['severity']}] {rc['message']}")
        print(f"Summary:     {result['investigator_summary'][:120]}...")
        return result
    except requests.ConnectionError:
        print("ERROR: Cannot connect to API at", API_URL)
        return None
    except Exception as e:
        print(f"ERROR: {e}")
        return None


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate mock fraud detection transactions")
    parser.add_argument(
        "--scenario",
        choices=list(SCENARIOS.keys()),
        default="normal_user",
        help="Transaction scenario to generate",
    )
    parser.add_argument("--count", type=int, default=1, help="Number of transactions")
    parser.add_argument("--user", type=str, default="user_1001", help="User ID")
    parser.add_argument("--all", action="store_true", help="Run all scenarios once each")
    args = parser.parse_args()

    if args.all:
        for scenario in SCENARIOS:
            print(f"\n--- Scenario: {scenario} ---")
            print(f"    {SCENARIOS[scenario]['description']}")
            txn = generate_transaction(scenario, args.user)
            print(f"    Sending: ₹{txn['amount']:,.0f} from {txn['device_id']}")
            send_transaction(txn)
            time.sleep(0.3)
    else:
        for i in range(args.count):
            txn = generate_transaction(args.scenario, args.user)
            send_transaction(txn)
            if i < args.count - 1:
                time.sleep(0.3)


if __name__ == "__main__":
    main()
