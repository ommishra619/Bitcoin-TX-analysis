from generate_fake_transactions import generate_fake_transactions
from transaction_parser import parse_transaction
from intelligence import compute_risk_score

def parse_fake_transaction(fake_tx):
    if "inputs" in fake_tx and "outputs" in fake_tx:
        return {
            "txid": fake_tx.get("txid", "unknown"),
            "inputs": fake_tx["inputs"],
            "outputs": fake_tx["outputs"]
        }
    return {
        "txid": fake_tx.get("txid", "unknown"),
        "inputs": [
            {
                "address": fake_tx.get("from_address", ""),
                "value": fake_tx.get("amount_btc", 0) + fake_tx.get("fee_btc", 0)
            }
        ],
        "outputs": [
            {
                "address": fake_tx.get("to_address", ""),
                "value": fake_tx.get("amount_btc", 0)
            }
        ]
    }

print("=" * 70)
print("Testing Risk Score Calculation")
print("=" * 70)

for test_num in range(3):
    print(f"\n\nTest {test_num + 1}:")
    print("-" * 70)
    
    # Generate fake transactions
    raw_txs = generate_fake_transactions(100, seed=None)
    parsed_txs = [parse_fake_transaction(tx) for tx in raw_txs]
    
    # Get focus address (first input from first tx)
    focus_address = parsed_txs[0]["inputs"][0]["address"] if parsed_txs else None
    
    # Calculate risk
    risk = compute_risk_score(focus_address, parsed_txs=parsed_txs)
    score = risk.get("score")
    reasons = risk.get("reasons", [])
    breakdown = risk.get("breakdown", {})
    
    print(f"Focus Address: {focus_address}")
    print(f"Risk Score: {score}")
    print(f"Incoming Total: {breakdown.get('incoming_total', 0):.4f}")
    print(f"Outgoing Total: {breakdown.get('outgoing_total', 0):.4f}")
    print(f"Max TX Value: {breakdown.get('max_tx_value', 0):.4f}")
    print(f"Unique Counterparties: {breakdown.get('unique_counterparties', 0)}")
    print(f"TX Count: {breakdown.get('tx_count', 0)}")
    print(f"\nScoring Reasons:")
    for reason in reasons[:5]:
        print(f"  - {reason}")
    if len(reasons) > 5:
        print(f"  ... and {len(reasons) - 5} more")

print("\n" + "=" * 70)
