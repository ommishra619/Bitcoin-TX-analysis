from collections import Counter

from data_fetcher import get_address_info, get_address_txs
from bitcoin_basics import summarize_address as _summarize_address
from transaction_parser import parse_transaction
from heuristics import classify_transaction
from graph_engine import build_transaction_graph, degree_centrality


def summarize_address(address):
    """Fetch address info and return a human-friendly summary."""
    info = get_address_info(address)
    return _summarize_address(info)


def parse_transactions(address, limit=100):
    """Fetch and parse up to `limit` transactions for `address`."""
    txs = get_address_txs(address)
    parsed = []
    for tx in txs[:limit]:
        parsed.append(parse_transaction(tx))
    return parsed


def classify_transactions(parsed_txs):
    """Classify a list of parsed transactions and return counts + labels."""
    labels = [classify_transaction(tx) for tx in parsed_txs]
    counts = Counter(labels)
    return {
        "counts": dict(counts),
        "labels": labels
    }


def build_graph(parsed_txs):
    """Build a directed transaction graph from parsed transactions."""
    return build_transaction_graph(parsed_txs)


def compute_risk_score(address, parsed_txs=None):
    """Return a 0-100 risk score and reasons for the score.

    The scoring is heuristic-based and intended as a lightweight indicator.
    """
    reasons = []
    score = 0

    if parsed_txs is None:
        parsed_txs = parse_transactions(address, limit=100)

    # Address-level summary
    try:
        summary = summarize_address(address)
        balance = summary.get("balance", 0)
        tx_count = summary.get("tx_count", 0)
    except Exception:
        balance = 0
        tx_count = 0

    # Large balance increases risk
    if balance >= 10:
        score += 30
        reasons.append("High balance >= 10 BTC")
    elif balance >= 1:
        score += 10
        reasons.append("Balance >= 1 BTC")

    # Transaction-based heuristics
    classifications = classify_transactions(parsed_txs)
    counts = classifications.get("counts", {})

    if counts.get("Possible CoinJoin (Equal outputs)"):
        score += 15
        reasons.append("CoinJoin-like outputs detected")

    if counts.get("Possible exchange batch"):
        score += 15
        reasons.append("Exchange-like batch transactions detected")

    if counts.get("UTXO consolidation"):
        score += 8
        reasons.append("UTXO consolidation patterns detected")

    # Many transactions -> more data, slightly higher base
    if tx_count > 100:
        score += 5

    # Graph centrality: if this address is highly central, raise risk
    try:
        G = build_graph(parsed_txs)
        centrality = degree_centrality(G)
        node_scores = sorted(centrality.items(), key=lambda x: x[1], reverse=True)
        if node_scores:
            top_node, top_score = node_scores[0]
            if top_node == address and top_score > 0.5:
                score += 20
                reasons.append("Very high graph centrality")
    except Exception:
        pass

    # Normalize to 0-100
    if score > 100:
        score = 100

    return {"score": score, "reasons": reasons, "counts": counts}
