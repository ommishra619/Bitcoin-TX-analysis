#!/usr/bin/env python3
"""Test script to verify fake transaction scores vary"""
import requests
import json

BASE_URL = "http://localhost:8000"

print("Testing fake transaction scoring variance...\n")
print("=" * 60)

scores = []
for i in range(5):
    try:
        response = requests.post(f"{BASE_URL}/api/analyze/fake")
        if response.status_code == 200:
            data = response.json()
            risk = data.get("risk", {})
            score = risk.get("score", "N/A")
            tx_count = data.get("tx_count", 0)
            patterns = data.get("behavior_patterns", [])
            scores.append(score)
            
            print(f"\n--- Test {i+1} ---")
            print(f"Risk Score: {score}")
            print(f"Transaction Count: {tx_count}")
            print(f"Behavior Patterns: {len(patterns)}")
            if patterns:
                print("  Top patterns:")
                for p in patterns[:3]:
                    print(f"    - {p}")
        else:
            print(f"Test {i+1}: ERROR - Status {response.status_code}")
            print(response.text)
    except Exception as e:
        print(f"Test {i+1}: ERROR - {e}")

print("\n" + "=" * 60)
print(f"\nScores obtained: {scores}")
print(f"Unique scores: {set(scores)}")
print(f"Score variance confirmed: {len(set(scores)) > 1}")
