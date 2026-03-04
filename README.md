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
