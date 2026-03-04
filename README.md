# Bitcoin Threat Intelligence Engine

## Description

A Python-based blockchain intelligence tool that analyzes Bitcoin wallet activity using transaction graph analysis, behavioral heuristics, and risk scoring.

## Features

- ✔ Wallet analysis
- ✔ Transaction parsing
- ✔ Behavioral classification
- ✔ Graph analytics
- ✔ Risk scoring engine

## Technologies

- Python
- NetworkX
- Blockchain APIs (Blockstream)
- Graph analytics

## Installation

1. Create a virtual environment (recommended):

```bash
python -m venv venv
source venv/bin/activate  # on Windows: venv\Scripts\activate
```

2. Install requirements:

```bash
python -m pip install -r requirements.txt
```

## Usage

Basic CLI usage:

```bash
python main.py <bitcoin_address>
```

To compute risk score and save a graph image, run without `--no-graph` (default behaviour):

```bash
python main.py bc1q...youraddress...
```

Output includes a behavior summary, risk score (0-100), and `graph.png` if visualization packages are installed.

## Future Work

- CoinJoin detection
- Address clustering
- Ransomware wallet detection
- Web dashboard

---

If you'd like, I can: add unit tests, a small web API, or a demo notebook showing end-to-end analysis for a sample address.

## Example Output

Below is a sample run of the tool for a single Bitcoin address. The CLI prints a short transaction analysis, aggregated behavior patterns, a risk score with reasons, and saves a graph image (`graph.png`).

```text
--- First Transaction Analysis ---
TXID: 59895d26d85732c8d8a0ddce5f79021444e0f2cbfad0634d6b16b7e346acf41e

Inputs:
{'address': 'bc1q73f28vgtaqe2284ln08lakttv5zvnlej448cux', 'value': 0.03108741}

Outputs:
{'address': 'bc1qpww362stdn2vqsucq34kpnup389n36r5wjhd66', 'value': 0.01681408}
{'address': 'bc1q73f28vgtaqe2284ln08lakttv5zvnlej448cux', 'value': 0.01427051}

Graph Stats:
Nodes: 42
Edges: 42

Behavior Pattern: Simple payment (Possible change)

Aggregated Behavior Patterns:
- Recurring payments to single recipient (merchant/subscription)

Top Connected Addresses:
bc1q73f28vgtaqe2284ln08lakttv5zvnlej448cux 0.4634
bc1qz2mwg4ws5xxjfy52xjeclmhfx23eu7k74ls4r4 0.3415
bc1qmzjtf6tq7zv6gk4uuxv4ldae79ky9dd9uswtra 0.1951

Computing risk score...
Risk score: 20
Reasons:
- Exchange-like batch transactions detected
- Moderate graph centrality
Breakdown:
balance: -0.32931298
incoming_total: 0.31698914
outgoing_total: 0.30692688
max_tx_value: 0.04885031
unique_counterparties: 17
tx_count: 25
classifications: {'Simple payment (Possible change)': 15, 'Unclassified / Normal': 4, 'Possible exchange batch': 1}
peeling_chains_count: 0
peeling_chains: []

Graph image saved to graph.png
```

