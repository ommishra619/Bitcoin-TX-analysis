import json
from pathlib import Path

from graph_engine import build_transaction_graph, degree_centrality
from heuristics import classify_behavior
from intelligence import classify_transactions


REQUIRED_FIELDS = {
    "txid",
    "timestamp",
    "from_address",
    "to_address",
    "amount_btc",
    "fee_btc",
    "block_height",
    "confirmations",
    "is_coinbase",
}


def validate_and_convert(data: list[dict]) -> tuple[list[dict], list[int], list[tuple[int, list[str]]]]:
    parsed = []
    invalid_rows = []
    missing_field_rows = []

    for idx, tx in enumerate(data):
        missing = sorted(REQUIRED_FIELDS - tx.keys())
        if missing:
            missing_field_rows.append((idx, missing))
            continue

        valid = True
        if not isinstance(tx["txid"], str) or len(tx["txid"]) != 64:
            valid = False
        if not isinstance(tx["from_address"], str) or not tx["from_address"].startswith("bc1q"):
            valid = False
        if not isinstance(tx["to_address"], str) or not tx["to_address"].startswith("bc1q"):
            valid = False
        if not isinstance(tx["amount_btc"], (int, float)) or tx["amount_btc"] <= 0:
            valid = False
        if not isinstance(tx["fee_btc"], (int, float)) or tx["fee_btc"] < 0:
            valid = False

        if not valid:
            invalid_rows.append(idx)
            continue

        parsed.append(
            {
                "txid": tx["txid"],
                "inputs": [
                    {
                        "address": tx["from_address"],
                        "value": float(tx["amount_btc"]) + float(tx["fee_btc"]),
                    }
                ],
                "outputs": [
                    {
                        "address": tx["to_address"],
                        "value": float(tx["amount_btc"]),
                    }
                ],
            }
        )

    return parsed, invalid_rows, missing_field_rows


def run(path: Path) -> int:
    if not path.exists():
        print(f"File not found: {path}")
        return 1

    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        print("Input JSON must be a list of transactions")
        return 1

    parsed, invalid_rows, missing_field_rows = validate_and_convert(data)

    classifications = classify_transactions(parsed)
    behaviors = classify_behavior(parsed)

    graph = build_transaction_graph(parsed)
    centrality = degree_centrality(graph)
    top_nodes = sorted(centrality.items(), key=lambda x: x[1], reverse=True)[:5]

    print("Validation summary")
    print("------------------")
    print(f"records_total: {len(data)}")
    print(f"records_valid: {len(parsed)}")
    print(f"missing_field_rows: {len(missing_field_rows)}")
    print(f"invalid_rows: {len(invalid_rows)}")
    print(f"classification_counts: {classifications.get('counts', {})}")
    print(f"behavior_patterns: {behaviors}")
    print(f"graph_nodes: {graph.number_of_nodes()}")
    print(f"graph_edges: {graph.number_of_edges()}")
    print(f"top_centrality_nodes: {top_nodes}")

    return 0 if not invalid_rows and not missing_field_rows else 2


if __name__ == "__main__":
    raise SystemExit(run(Path("fake_transactions_100.json")))
