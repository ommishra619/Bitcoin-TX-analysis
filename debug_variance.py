from generate_fake_transactions import generate_fake_transactions
import json

print("=" * 70)
print("Testing Fake Transaction Generator Variance")
print("=" * 70)

for test_num in range(3):
    print(f"\nTest {test_num + 1}:")
    txs = generate_fake_transactions(100, seed=None)
    
    # Count different pattern types
    fan_outs = len([t for t in txs if len(t.get("outputs", [])) > 10])
    fan_ins = len([t for t in txs if len(t.get("inputs", [])) > 5])
    high_fees = len([t for t in txs if (sum(i.get("value", 0) for i in t.get("inputs", [])) - sum(o.get("value", 0) for o in t.get("outputs", []))) > 0.5])
    
    print(f"  - Fan-out transactions (>10 outputs): {fan_outs}")
    print(f"  - Fan-in transactions (>5 inputs): {fan_ins}")
    print(f"  - High-fee transactions (>0.5 BTC fee): {high_fees}")
    
    # Show first transaction details
    if txs:
        first = txs[0]
        print(f"  - First TX inputs: {len(first.get('inputs', []))}, outputs: {len(first.get('outputs', []))}")

print("\n" + "=" * 70)
print("If all tests show different counts, the generator is working!")
