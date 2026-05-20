import json
import random
from faker import Faker
from datetime import datetime, timedelta

def _fake_btc_address(rng: random.Random) -> str:
    charset = "023456789acdefghjklmnpqrstuvwxyz"
    return "bc1q" + "".join(rng.choice(charset) for _ in range(38))

def create_tx(fake, inputs, outputs, i, base_time):
    # Cluster timestamps into seconds-to-minutes ranges to simulate bursts
    # so that the 30-min observation windows are densely populated
    tx_time = base_time + timedelta(seconds=(i * random.randint(5, 60)))
    return {
        "txid": fake.sha256(raw_output=False),
        "timestamp": tx_time.isoformat() + "Z",
        "inputs": inputs,
        "outputs": outputs,
        "block_height": 830000 + (i // 5),
        "confirmations": random.randint(1, 4000),
        "is_coinbase": False,
    }

def generate_fake_transactions(count: int = 100, seed: int = None) -> list[dict]:
    if seed is None:
        seed = random.randint(0, 1000000000)
    fake = Faker()
    # Only seed the local rng, not the global Faker instance
    rng = random.Random(seed)
    
    # Base time for burst simulation
    current_burst_time = datetime.utcnow() - timedelta(minutes=60)

    transactions = []
    
    # Randomize pattern frequencies with wider ranges for more variance
    peel_chains_count = rng.randint(0, 15)
    fan_out_count = rng.randint(0, 10)
    fan_in_count = rng.randint(0, 10)
    mixing_count = rng.randint(0, 8)
    coinjoin_count = rng.randint(0, 8)
    high_value_count = rng.randint(0, 8)
    high_fee_count = rng.randint(0, 12)
    
    # 1. Peeling Chain Scenario
    if peel_chains_count > 0:
        peel_chain_start = _fake_btc_address(rng)
        current_addr = peel_chain_start
        current_amount = 50.0 
        for _ in range(peel_chains_count):
            peel_addr = _fake_btc_address(rng)
            next_change = _fake_btc_address(rng)
            peel_amount = round(rng.uniform(0.1, 5.0), 8)
            fee = round(rng.uniform(0.0001, 0.001), 8)
            next_amount = current_amount - peel_amount - fee
            if next_amount <= 0:
                break
                
            inputs = [{"address": current_addr, "value": current_amount}]
            outputs = [
                {"address": peel_addr, "value": peel_amount},
                {"address": next_change, "value": next_amount}
            ]
            transactions.append(create_tx(fake, inputs, outputs, len(transactions), current_burst_time))
            current_addr = next_change
            current_amount = next_amount

    # 2. Fan-out Distribution
    for _ in range(fan_out_count):
        distributor = _fake_btc_address(rng)
        distribution_amount = round(rng.uniform(5.0, 50.0), 8)
        num_outputs = rng.randint(5, 30)
        inputs = [{"address": distributor, "value": distribution_amount}]
        outputs = []
        per_output = (distribution_amount * 0.99) / num_outputs  # leave 1% for fee
        for _ in range(num_outputs):
            outputs.append({"address": _fake_btc_address(rng), "value": round(per_output, 8)})
        transactions.append(create_tx(fake, inputs, outputs, len(transactions), current_burst_time))

    # 3. Fan-in Consolidation
    for _ in range(fan_in_count):
        consolidator = _fake_btc_address(rng)
        num_inputs = rng.randint(5, 25)
        input_value = round(rng.uniform(0.1, 2.0), 8)
        inputs = []
        for _ in range(num_inputs):
            inputs.append({"address": _fake_btc_address(rng), "value": input_value})
        total_out = num_inputs * input_value - round(rng.uniform(0.001, 0.1), 8)
        outputs = [{"address": consolidator, "value": total_out}]
        transactions.append(create_tx(fake, inputs, outputs, len(transactions), current_burst_time))

    # 4. Mixing / Tiny Outputs / Dust
    for _ in range(mixing_count):
        mixer = _fake_btc_address(rng)
        mixing_amount = round(rng.uniform(0.01, 1.0), 8)
        num_outputs = rng.randint(20, 100)
        inputs = [{"address": mixer, "value": mixing_amount}]
        outputs = []
        per_output = round(mixing_amount / (num_outputs * 1.05), 8)
        for _ in range(num_outputs):
            outputs.append({"address": _fake_btc_address(rng), "value": per_output})
        transactions.append(create_tx(fake, inputs, outputs, len(transactions), current_burst_time))

    # 5. CoinJoin (Equal Outputs)
    for _ in range(coinjoin_count):
        inputs = []
        outputs = []
        num_participants = rng.randint(3, 20)
        per_participant = round(rng.uniform(0.5, 3.0), 8)
        for i in range(num_participants):
            inputs.append({"address": _fake_btc_address(rng), "value": per_participant * 1.02})
            outputs.append({"address": _fake_btc_address(rng), "value": per_participant})
            # Add change output with slight variance
            outputs.append({"address": _fake_btc_address(rng), "value": round(per_participant * 0.02, 8)})
        transactions.append(create_tx(fake, inputs, outputs, len(transactions), current_burst_time))

    # 6. High-value transfers
    for _ in range(high_value_count):
        sender = _fake_btc_address(rng)
        receiver = _fake_btc_address(rng)
        value = round(rng.uniform(50.0, 500.0), 8)
        inputs = [{"address": sender, "value": value * 1.001}]
        outputs = [{"address": receiver, "value": value}]
        transactions.append(create_tx(fake, inputs, outputs, len(transactions), current_burst_time))

    # 7. High-fee transactions
    for _ in range(high_fee_count):
        sender = _fake_btc_address(rng)
        receiver = _fake_btc_address(rng)
        input_value = round(rng.uniform(1.0, 10.0), 8)
        fee_ratio = rng.uniform(0.01, 0.5)  # 1% to 50% fee
        fee = round(input_value * fee_ratio, 8)
        output_value = input_value - fee
        inputs = [{"address": sender, "value": input_value}]
        outputs = [{"address": receiver, "value": output_value}]
        transactions.append(create_tx(fake, inputs, outputs, len(transactions), current_burst_time))

    # 8. Self-churn transactions (address sending to itself via change)
    self_churn_count = rng.randint(0, 8)
    for _ in range(self_churn_count):
        addr = _fake_btc_address(rng)
        amount = round(rng.uniform(0.5, 5.0), 8)
        inputs = [{"address": addr, "value": amount}]
        # Send a portion out and change back to same address
        output_amount = round(amount * rng.uniform(0.3, 0.7), 8)
        change_amount = amount - output_amount - round(rng.uniform(0.0001, 0.001), 8)
        outputs = [
            {"address": _fake_btc_address(rng), "value": output_amount},
            {"address": addr, "value": change_amount}  # change back to self
        ]
        transactions.append(create_tx(fake, inputs, outputs, len(transactions), current_burst_time))

    # 9. Dusting/spam transactions (very small amounts to many addresses)
    dust_count = rng.randint(0, 4)
    for _ in range(dust_count):
        sender = _fake_btc_address(rng)
        inputs = [{"address": sender, "value": 0.001}]
        outputs = []
        for _ in range(rng.randint(5, 15)):
            outputs.append({"address": _fake_btc_address(rng), "value": 0.00001})
        transactions.append(create_tx(fake, inputs, outputs, len(transactions), current_burst_time))

    # 10. Normal random transactions (to fill up to `count`)
    normal_count = count - len(transactions)
    for _ in range(normal_count):
        # Vary transaction types randomly
        tx_type = rng.choice(['simple', 'multiple_inputs', 'multiple_outputs', 'batch'])
        
        if tx_type == 'simple':
            amount = round(rng.uniform(0.001, 10.0), 8)
            fee = round(rng.uniform(0.00001, 0.001), 8)
            inputs = [{"address": _fake_btc_address(rng), "value": amount + fee}]
            outputs = [{"address": _fake_btc_address(rng), "value": amount}]
        
        elif tx_type == 'multiple_inputs':
            num_inputs = rng.randint(2, 8)
            inputs = []
            total_in = 0
            for _ in range(num_inputs):
                inp_val = round(rng.uniform(0.1, 2.0), 8)
                inputs.append({"address": _fake_btc_address(rng), "value": inp_val})
                total_in += inp_val
            fee = round(total_in * rng.uniform(0.001, 0.01), 8)
            outputs = [{"address": _fake_btc_address(rng), "value": total_in - fee}]
        
        elif tx_type == 'multiple_outputs':
            amount = round(rng.uniform(0.5, 5.0), 8)
            num_outputs = rng.randint(2, 6)
            inputs = [{"address": _fake_btc_address(rng), "value": amount}]
            outputs = []
            per_output = (amount * 0.99) / num_outputs
            for _ in range(num_outputs):
                outputs.append({"address": _fake_btc_address(rng), "value": round(per_output, 8)})
        
        else:  # batch - many small outputs
            amount = round(rng.uniform(0.1, 2.0), 8)
            num_outputs = rng.randint(4, 15)
            inputs = [{"address": _fake_btc_address(rng), "value": amount}]
            outputs = []
            per_output = (amount * 0.98) / num_outputs
            for _ in range(num_outputs):
                outputs.append({"address": _fake_btc_address(rng), "value": round(per_output, 8)})
        
        transactions.append(create_tx(fake, inputs, outputs, len(transactions), current_burst_time))

    # Shuffle for realism
    rng.shuffle(transactions)

    # Reassign block heights so they are somewhat ordered
    # and adjust timestamps ascending if we shuffled them
    transactions.sort(key=lambda x: x["timestamp"])
    for i, tx in enumerate(transactions):
        tx["block_height"] = 830000 + (i // 5)

    return transactions


if __name__ == "__main__":
    data = generate_fake_transactions(count=100, seed=123)
    output_file = "fake_transactions_100.json"

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

    print(f"Generated {len(data)} diverse fake transactions -> {output_file}")
