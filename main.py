from data_fetcher import get_address_txs
from transaction_parser import parse_transaction
from heuristics import classify_transaction

address = input("Enter Bitcoin address: ")

txs = get_address_txs(address)

print("\n--- First Transaction Analysis ---")

if txs:
    parsed = parse_transaction(txs[0])
    print("TXID:", parsed["txid"])

    print("\nInputs:")
    for i in parsed["inputs"]:
        print(i)

    print("\nOutputs:")
    for o in parsed["outputs"]:
        print(o)

classification = classify_transaction(parsed)
print("\nBehavior Pattern:", classification)