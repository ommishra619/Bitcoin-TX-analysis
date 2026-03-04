from data_fetcher import get_address_txs
from transaction_parser import parse_transaction
from heuristics import classify_transaction
from graph_engine import build_transaction_graph, degree_centrality

address = input("Enter Bitcoin address: ")


txs = get_address_txs(address)

if not txs:
    print(f"No transactions found for address {address}")
    parsed_transactions = []
else:
    print("\n--- First Transaction Analysis ---")

    first_parsed = parse_transaction(txs[0])
    print("TXID:", first_parsed.get("txid"))

    print("\nInputs:")
    for i in first_parsed.get("inputs", []):
        print(i)

    print("\nOutputs:")
    for o in first_parsed.get("outputs", []):
        print(o)

    parsed_transactions = []
    for tx in txs[:20]:
        parsed = parse_transaction(tx)
        parsed_transactions.append(parsed)

G = build_transaction_graph(parsed_transactions)

print("\nGraph Stats:")
print("Nodes:", G.number_of_nodes())
print("Edges:", G.number_of_edges())

if parsed_transactions:
    classification = classify_transaction(parsed_transactions[0])
else:
    classification = "No transactions to classify"

print("\nBehavior Pattern:", classification)
centrality = degree_centrality(G)

sorted_nodes = sorted(centrality.items(), key=lambda x: x[1], reverse=True)

print("\nTop Connected Addresses:")
for addr, score in sorted_nodes[:5]:
    print(addr, score)