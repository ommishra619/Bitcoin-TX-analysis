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
