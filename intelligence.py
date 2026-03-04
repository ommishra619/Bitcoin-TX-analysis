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
        parsed_txs = parse_transactions(address, limit=200)

    # Address-level summary
    try:
        summary = summarize_address(address)
        balance = summary.get("balance", 0)
        tx_count = summary.get("tx_count", 0)
    except Exception:
        balance = 0
        tx_count = 0

    # Transaction-level aggregates for the target address
    incoming_total = 0.0
    outgoing_total = 0.0
    max_tx_value = 0.0
    tx_values = []
    counterparties = set()
    small_output_txs = 0

    for tx in parsed_txs:
        tx_in = sum(i.get("value", 0) for i in tx.get("inputs", []))
        tx_out = sum(o.get("value", 0) for o in tx.get("outputs", []))

        # Is the address an output (received) in this tx?
        for o in tx.get("outputs", []):
            if o.get("address") == address:
                incoming_total += o.get("value", 0)
                tx_values.append(o.get("value", 0))
                if o.get("value", 0) > max_tx_value:
                    max_tx_value = o.get("value", 0)
                # collect counterparties from inputs
                for i in tx.get("inputs", []):
                    if i.get("address") and i.get("address") != address:
                        counterparties.add(i.get("address"))

        # Is the address an input (spent) in this tx?
        for i in tx.get("inputs", []):
            if i.get("address") == address:
                outgoing_total += i.get("value", 0)
                tx_values.append(i.get("value", 0))
                if i.get("value", 0) > max_tx_value:
                    max_tx_value = i.get("value", 0)
                for o in tx.get("outputs", []):
                    if o.get("address") and o.get("address") != address:
                        counterparties.add(o.get("address"))

        # small outputs heuristic (many tiny outputs suggest mixing/tumbling)
        outs = [o.get("value", 0) for o in tx.get("outputs", [])]
        if outs and max(outs) < 0.0005 and len(outs) > 5:
            small_output_txs += 1

    # normalize BTC amounts are already in BTC in parsed output
    total_counterparties = len(counterparties)

    # Balance-based scoring
    if balance >= 50:
        score += 40
        reasons.append("Very high balance >= 50 BTC")
    elif balance >= 10:
        score += 25
        reasons.append("High balance >= 10 BTC")
    elif balance >= 1:
        score += 8
        reasons.append("Balance >= 1 BTC")

    # Large single transaction
    if max_tx_value >= 10:
        score += 30
        reasons.append("Large single transaction >= 10 BTC")
    elif max_tx_value >= 1:
        score += 10
        reasons.append("Single transaction >= 1 BTC")

    # Many counterparties may indicate exchange or mixer behavior
    if total_counterparties > 200:
        score += 25
        reasons.append("Many unique counterparties (>200)")
    elif total_counterparties > 50:
        score += 10
        reasons.append("Many unique counterparties (>50)")

    # Incoming/outgoing imbalance
    if outgoing_total == 0 and incoming_total > 0:
        score += 8
        reasons.append("Only incoming funds recorded (possible deposit address)")
    elif incoming_total == 0 and outgoing_total > 0:
        score += 8
        reasons.append("Only outgoing funds recorded (possible hot wallet)")
    else:
        try:
            ratio = incoming_total / (outgoing_total + 1e-9)
            if ratio > 10:
                score += 12
                reasons.append("Incoming >> outgoing (large deposits)")
            elif ratio < 0.1:
                score += 12
                reasons.append("Outgoing >> incoming (rapid spending)")
        except Exception:
            pass

    # small outputs/mixing indicator
    if small_output_txs > 3:
        score += 12
        reasons.append("Multiple transactions with many tiny outputs (mixing)")

    # heuristics from classification
    classifications = classify_transactions(parsed_txs)
    counts = classifications.get("counts", {})

    if counts.get("Possible CoinJoin (Equal outputs)"):
        score += 15
        reasons.append("CoinJoin-like outputs detected")

    if counts.get("Possible exchange batch"):
        score += 12
        reasons.append("Exchange-like batch transactions detected")

    if counts.get("UTXO consolidation"):
        score += 6
        reasons.append("UTXO consolidation patterns detected")

    # Graph centrality: if this address is highly central, raise risk
    try:
        G = build_graph(parsed_txs)
        centrality = degree_centrality(G)
        node_score = centrality.get(address, 0)
        if node_score > 0.6:
            score += 18
            reasons.append("Very high graph centrality")
        elif node_score > 0.3:
            score += 8
            reasons.append("Moderate graph centrality")
    except Exception:
        pass

    # Transaction frequency
    if tx_count > 1000:
        score += 10
        reasons.append("Very high transaction count (>1000)")
    elif tx_count > 200:
        score += 5

    # normalize
    if score > 100:
        score = 100

    breakdown = {
        "balance": balance,
        "incoming_total": incoming_total,
        "outgoing_total": outgoing_total,
        "max_tx_value": max_tx_value,
        "unique_counterparties": total_counterparties,
        "tx_count": tx_count,
        "classifications": counts,
    }

    return {"score": score, "reasons": reasons, "breakdown": breakdown}
