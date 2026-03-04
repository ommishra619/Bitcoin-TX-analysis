def classify_transaction(parsed_tx):
    """Classify a parsed transaction using simple heuristics.

    parsed_tx is expected to be a dict with keys "inputs" and "outputs",
    where "outputs" is a list of dicts that may contain a "value" key.
    """
    inputs = parsed_tx.get("inputs", [])
    outputs = parsed_tx.get("outputs", [])

    input_count = len(inputs)
    output_count = len(outputs)
    output_values = [o.get("value") for o in outputs]

    if input_count == 1 and output_count == 2:
        return "Simple payment (Possible change)"

    if input_count > 3 and output_count == 1:
        return "UTXO consolidation"

    if output_count > 10:
        return "Possible exchange batch"

    if output_count >= 5:
        unique_values = set(output_values)
        if len(unique_values) == 1:
            return "Possible CoinJoin (Equal outputs)"

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

    # Many small outputs -> possible mixer/tumbler
    small_output_tx_count = 0
    equal_outputs_tx_count = 0
    dusting_count = 0
    big_incoming = 0

    for tx in parsed_txs:
        outs = [o.get('value', 0) for o in tx.get('outputs', [])]
        if not outs:
            continue
        if max(outs) < 0.001 and len(outs) > 5:
            small_output_tx_count += 1
        unique_vals = set(outs)
        if len(outs) >= 3 and len(unique_vals) == 1:
            equal_outputs_tx_count += 1
        # dusting: many tiny outputs to many recipients
        tiny_outputs = [v for v in outs if v > 0 and v < 0.00001]
        if len(tiny_outputs) >= 3:
            dusting_count += 1
        # incoming large
        for o in tx.get('outputs', []):
            if o.get('value', 0) >= 5:
                big_incoming += 1

    if small_output_tx_count > max(1, total_txs * 0.05):
        labels.append('Possible mixer/tumbler')
    if equal_outputs_tx_count > 0:
        labels.append('Possible CoinJoin')
    if dusting_count > 0:
        labels.append('Possible dusting attack')
    if big_incoming > 0:
        labels.append('Large deposits (exchange/hot wallet)')

    # consolidation: many inputs into single output
    consolidation_count = 0
    for tx in parsed_txs:
        if len(tx.get('inputs', [])) >= 4 and len(tx.get('outputs', [])) <= 2:
            consolidation_count += 1
    if consolidation_count > max(1, total_txs * 0.02):
        labels.append('UTXO consolidation')

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
