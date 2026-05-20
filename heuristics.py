def _sum_values(items):
    total = 0.0
    for item in items:
        try:
            total += float(item.get("value", 0) or 0)
        except Exception:
            continue
    return total


def extract_behavior_signals(parsed_txs):
    """Extract aggregate suspiciousness signals from parsed transactions."""
    signals = {
        "tx_count": len(parsed_txs),
        "small_output_tx_count": 0,
        "equal_outputs_tx_count": 0,
        "dusting_count": 0,
        "big_incoming": 0,
        "consolidation_count": 0,
        "fan_out_count": 0,
        "fan_in_count": 0,
        "high_fee_count": 0,
        "self_churn_count": 0,
        "round_amount_count": 0,
        "reused_output_addresses": 0,
    }

    recipients = {}

    for tx in parsed_txs:
        inputs = tx.get("inputs", [])
        outputs = tx.get("outputs", [])
        input_count = len(inputs)
        output_count = len(outputs)

        outs = [float(o.get("value", 0) or 0) for o in outputs]
        if outs and max(outs) < 0.001 and len(outs) > 5:
            signals["small_output_tx_count"] += 1

        if len(outs) >= 3 and len(set(outs)) == 1:
            signals["equal_outputs_tx_count"] += 1

        tiny_outputs = [v for v in outs if 0 < v < 0.00001]
        if len(tiny_outputs) >= 3:
            signals["dusting_count"] += 1

        for o in outputs:
            value = float(o.get("value", 0) or 0)
            if value >= 5:
                signals["big_incoming"] += 1

            addr = o.get("address")
            if addr:
                recipients.setdefault(addr, 0)
                recipients[addr] += 1

            # Round amounts can indicate scripted payouts.
            if value > 0:
                sat = int(round(value * 1e8))
                if sat % 100000 == 0:
                    signals["round_amount_count"] += 1

        if input_count >= 4 and output_count <= 2:
            signals["consolidation_count"] += 1
        if input_count <= 2 and output_count >= 8:
            signals["fan_out_count"] += 1
        if input_count >= 8 and output_count <= 2:
            signals["fan_in_count"] += 1

        in_total = _sum_values(inputs)
        out_total = _sum_values(outputs)
        fee = max(0.0, in_total - out_total)
        if in_total > 0:
            fee_ratio = fee / in_total
            if fee >= 0.001 or fee_ratio > 0.05:
                signals["high_fee_count"] += 1

        in_addrs = {i.get("address") for i in inputs if i.get("address")}
        out_addrs = {o.get("address") for o in outputs if o.get("address")}
        if in_addrs and out_addrs and (in_addrs & out_addrs):
            signals["self_churn_count"] += 1

    signals["reused_output_addresses"] = sum(1 for _, c in recipients.items() if c > 2)
    return signals


def classify_transaction(parsed_tx):
    """Classify a parsed transaction using simple heuristics.

    parsed_tx is expected to be a dict with keys "inputs" and "outputs",
    where "outputs" is a list of dicts that may contain a "value" key.
    """
    inputs = parsed_tx.get("inputs", [])
    outputs = parsed_tx.get("outputs", [])

    input_count = len(inputs)
    output_count = len(outputs)
    output_values = [float(o.get("value", 0) or 0) for o in outputs]
    in_total = _sum_values(inputs)
    out_total = _sum_values(outputs)
    fee = max(0.0, in_total - out_total)
    fee_ratio = (fee / in_total) if in_total > 0 else 0.0

    in_addrs = {i.get("address") for i in inputs if i.get("address")}
    out_addrs = {o.get("address") for o in outputs if o.get("address")}

    if input_count == 1 and output_count == 2:
        return "Simple payment (Possible change)"

    if input_count > 3 and output_count == 1:
        return "UTXO consolidation"

    if input_count >= 8 and output_count <= 2:
        return "Fan-in consolidation"

    if input_count <= 2 and output_count >= 8:
        return "Fan-out distribution"

    if output_count > 10:
        return "Possible exchange batch"

    if output_count >= 5:
        unique_values = set(output_values)
        if len(unique_values) == 1:
            return "Possible CoinJoin (Equal outputs)"

    if in_addrs and out_addrs and (in_addrs & out_addrs) and output_count <= 3:
        return "Self-churn / change-heavy"

    if fee >= 0.001 or fee_ratio > 0.05:
        return "High-fee spend"

    return "Unclassified / Normal"


def detect_peeling_chains(parsed_txs, min_length=3, drop_ratio=0.6):
    """Detect peeling chains in a list of parsed transactions.

    A peeling chain is a sequence where funds are repeatedly spent to new
    addresses with the transferred value decreasing at each step.

    Parameters:
    - parsed_txs: list of parsed transaction dicts (from `parse_transaction`).
    - min_length: minimum number of hops in the chain to report.
    - drop_ratio: maximum allowed fraction of the previous value for the next
      hop (e.g., 0.6 requires the next hop's value to be <= 60% of the prior).

    Returns: list of chains. Each chain is a dict with keys:
      - 'chain': list of {'txid','address','value'} entries
      - 'length': number of hops
      - 'start_tx': starting txid
    """
    # Index transactions by txid and build quick lookup maps
    tx_by_txid = {tx.get('txid'): tx for tx in parsed_txs}

    # map address -> list of txs where the address appears as an input
    spends_by_address = {}
    for tx in parsed_txs:
        for inp in tx.get('inputs', []):
            addr = inp.get('address')
            if not addr:
                continue
            spends_by_address.setdefault(addr, []).append(tx)

    chains = []

    # For each transaction and each output, try to follow a peeling path
    for tx in parsed_txs:
        txid = tx.get('txid')
        for out in tx.get('outputs', []):
            addr = out.get('address')
            val = out.get('value', 0)
            if not addr or val <= 0:
                continue

            chain = [{'txid': txid, 'address': addr, 'value': val}]
            prev_addr = addr
            prev_val = val
            visited_txids = {txid}

            # Follow hops while the next hop spends from prev_addr
            while True:
                next_txs = spends_by_address.get(prev_addr, [])
                # pick the earliest next tx that we haven't visited
                next_tx = None
                for cand in next_txs:
                    cand_id = cand.get('txid')
                    if cand_id in visited_txids:
                        continue
                    next_tx = cand
                    break

                if not next_tx:
                    break

                visited_txids.add(next_tx.get('txid'))

                # choose the largest output (candidate continuation) that is
                # not the same as prev_addr
                next_outs = [o for o in next_tx.get('outputs', []) if o.get('address') != prev_addr]
                if not next_outs:
                    break
                next_out = max(next_outs, key=lambda o: o.get('value', 0))
                next_addr = next_out.get('address')
                next_val = next_out.get('value', 0)

                # require value decrease by drop_ratio (next_val <= prev_val * drop_ratio)
                if next_val <= prev_val * drop_ratio and next_val > 0:
                    chain.append({'txid': next_tx.get('txid'), 'address': next_addr, 'value': next_val})
                    prev_addr = next_addr
                    prev_val = next_val
                    # continue following
                    continue
                else:
                    break

            if len(chain) >= min_length:
                chains.append({'chain': chain, 'length': len(chain), 'start_tx': txid})

    return chains


def classify_behavior(parsed_txs):
    """Aggregate behavior classification for an address based on parsed txs.

    Returns a list of detected behavior labels (strings).
    """
    labels = []
    if not parsed_txs:
        return labels

    total_txs = len(parsed_txs)
    total_inputs = sum(len(tx.get('inputs', [])) for tx in parsed_txs)
    total_outputs = sum(len(tx.get('outputs', [])) for tx in parsed_txs)
    avg_inputs = total_inputs / total_txs if total_txs else 0
    avg_outputs = total_outputs / total_txs if total_txs else 0

    signals = extract_behavior_signals(parsed_txs)
    small_output_tx_count = signals.get('small_output_tx_count', 0)
    equal_outputs_tx_count = signals.get('equal_outputs_tx_count', 0)
    dusting_count = signals.get('dusting_count', 0)
    big_incoming = signals.get('big_incoming', 0)
    fan_out_count = signals.get('fan_out_count', 0)
    fan_in_count = signals.get('fan_in_count', 0)
    high_fee_count = signals.get('high_fee_count', 0)
    self_churn_count = signals.get('self_churn_count', 0)
    reused_output_addresses = signals.get('reused_output_addresses', 0)

    if small_output_tx_count > max(1, total_txs * 0.05):
        labels.append('Possible mixer/tumbler')
    if equal_outputs_tx_count > 0:
        labels.append('Possible CoinJoin')
    if dusting_count > 0:
        labels.append('Possible dusting attack')
    if big_incoming > 0:
        labels.append('Large deposits (exchange/hot wallet)')

    # consolidation: many inputs into very few outputs
    consolidation_count = signals.get('consolidation_count', 0)
    if consolidation_count > max(1, total_txs * 0.02):
        labels.append('UTXO consolidation')

    if fan_out_count > max(1, total_txs * 0.03):
        labels.append('Fan-out payout behavior')

    if fan_in_count > max(1, total_txs * 0.03):
        labels.append('Fan-in aggregation behavior')

    if high_fee_count > max(1, total_txs * 0.02):
        labels.append('Frequent high-fee spending')

    if self_churn_count > max(1, total_txs * 0.05):
        labels.append('Self-churn / change recycling')

    if reused_output_addresses > max(3, total_txs * 0.05):
        labels.append('Address reuse in outputs')

    # frequent small recurring payments -> subscription/merchant
    recipients = {}
    for tx in parsed_txs:
        for o in tx.get('outputs', []):
            addr = o.get('address')
            if not addr:
                continue
            recipients.setdefault(addr, 0)
            recipients[addr] += 1
    top_recipients = sorted(recipients.items(), key=lambda x: x[1], reverse=True)
    if top_recipients and top_recipients[0][1] > max(3, total_txs * 0.1):
        labels.append('Recurring payments to single recipient (merchant/subscription)')

    # classify based on averages
    if avg_inputs > 3 and avg_outputs <= 2:
        labels.append('Likely consolidation/coin management')
    if avg_outputs > 6:
        labels.append('Batch payouts (exchange or payroll)')

    # peeling chains
    peeling = detect_peeling_chains(parsed_txs, min_length=3, drop_ratio=0.7)
    if peeling:
        labels.append(f'Peeling chain detected ({len(peeling)} chains)')

    if not labels:
        labels.append('Normal/Unclassified')

    return labels
