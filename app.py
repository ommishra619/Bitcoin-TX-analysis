import logging
import os
import re
from typing import Any, Dict, List, Optional

import uvicorn
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator, model_validator

from data_fetcher import DataFetcherError, get_btc_price_history, get_btc_spot_price, get_transaction
from graph_engine import degree_centrality
from heuristics import classify_behavior
from intelligence import build_graph, classify_transactions, compute_risk_score, parse_transactions
import json
from transaction_parser import parse_transaction
from generate_fake_transactions import generate_fake_transactions

logger = logging.getLogger("bitcoin-api")
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))

# Broad-but-safe validation for P2PKH/P2SH/Bech32(mainnet + testnet) addresses.
_ADDRESS_RE = re.compile(r"^(bc1|tb1|[13mn2])[a-zA-HJ-NP-Z0-9]{20,90}$")
_TXID_RE = re.compile(r"^[0-9a-fA-F]{64}$")


def _validate_bitcoin_address(value: str) -> str:
    v = (value or "").strip()
    if not _ADDRESS_RE.match(v):
        raise ValueError("Invalid Bitcoin address format")
    return v


def _validate_txid(value: str) -> str:
    v = (value or "").strip().lower()
    if not _TXID_RE.match(v):
        raise ValueError("Invalid transaction id format")
    return v


def _serialize_graph(graph: Any, centrality: Dict[str, float]) -> Dict[str, Any]:
    nodes: List[Dict[str, Any]] = []
    edges: List[Dict[str, Any]] = []

    for node in graph.nodes():
        nodes.append(
            {
                "id": str(node),
                "centrality": float(centrality.get(node, 0.0)),
            }
        )

    try:
        raw_edges = list(graph.edges(data=True))
        for source, target, meta in raw_edges:
            weight = 0.0
            if isinstance(meta, dict):
                weight = float(meta.get("weight", 0.0))
            edges.append(
                {
                    "source": str(source),
                    "target": str(target),
                    "weight": weight,
                }
            )
    except TypeError:
        # Fallback graph implementation yields (u, v, w)
        for source, target, weight in graph.edges():
            edges.append(
                {
                    "source": str(source),
                    "target": str(target),
                    "weight": float(weight),
                }
            )

    return {
        "nodes": nodes,
        "edges": edges,
    }


class AnalyzeRequest(BaseModel):
    address: Optional[str] = Field(default=None, description="Bitcoin address")
    txid: Optional[str] = Field(default=None, description="Single transaction id")
    limit: int = Field(default=100, ge=1, le=500)
    include_graph: bool = Field(default=True)

    @field_validator("address")
    @classmethod
    def validate_address(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        return _validate_bitcoin_address(value)

    @field_validator("txid")
    @classmethod
    def validate_txid(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        return _validate_txid(value)

    @model_validator(mode="after")
    def require_address_or_txid(self):
        if not self.address and not self.txid:
            raise ValueError("Either address or txid must be provided")
        return self


class AnalyzeResponse(BaseModel):
    address: str
    tx_count: int
    classification_counts: Dict[str, int]
    behavior_patterns: List[str]
    risk: Dict[str, Any]
    graph: Optional[Dict[str, Any]] = None


class AnalyzeTxidsRequest(BaseModel):
    txids: List[str] = Field(..., min_length=1, max_length=200)
    include_graph: bool = Field(default=True)
    focus_address: Optional[str] = Field(default=None)

    @field_validator("txids")
    @classmethod
    def validate_txids(cls, values: List[str]) -> List[str]:
        return [_validate_txid(v) for v in values]

    @field_validator("focus_address")
    @classmethod
    def validate_focus_address(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        return _validate_bitcoin_address(value)


class AnalyzeTxidsResponse(BaseModel):
    txids: List[str]
    tx_count: int
    classification_counts: Dict[str, int]
    behavior_patterns: List[str]
    risk: Optional[Dict[str, Any]] = None
    graph: Optional[Dict[str, Any]] = None


class AnalyzeFakeResponse(BaseModel):
    tx_count: int
    classification_counts: Dict[str, int]
    behavior_patterns: List[str]
    risk: Optional[Dict[str, Any]] = None
    graph: Optional[Dict[str, Any]] = None


def parse_fake_transaction(fake_tx: Dict[str, Any]) -> Dict[str, Any]:
    if "inputs" in fake_tx and "outputs" in fake_tx:
        return {
            "txid": fake_tx.get("txid", "unknown"),
            "inputs": fake_tx["inputs"],
            "outputs": fake_tx["outputs"]
        }
    return {
        "txid": fake_tx.get("txid", "unknown"),
        "inputs": [
            {
                "address": fake_tx.get("from_address", ""),
                "value": fake_tx.get("amount_btc", 0) + fake_tx.get("fee_btc", 0)
            }
        ],
        "outputs": [
            {
                "address": fake_tx.get("to_address", ""),
                "value": fake_tx.get("amount_btc", 0)
            }
        ]
    }


app = FastAPI(title="Bitcoin TX Analysis API", version="0.1.0")

SUPPORTED_CURRENCIES = {"usd", "eur", "gbp", "inr", "jpy", "cad", "aud"}

cors_origins = [origin.strip() for origin in os.getenv("CORS_ORIGINS", "*").split(",") if origin.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health() -> Dict[str, str]:
    return {"status": "ok"}


@app.get("/api/price")
def price(
    days: int = Query(default=30, ge=1, le=3650),
    currency: str = Query(default="usd", min_length=3, max_length=3),
) -> Dict[str, Any]:
    try:
        selected_currency = currency.lower()
        if selected_currency not in SUPPORTED_CURRENCIES:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Unsupported currency '{currency}'. "
                    f"Supported: {', '.join(sorted(SUPPORTED_CURRENCIES))}"
                ),
            )

        spot = get_btc_spot_price(selected_currency)
        history = get_btc_price_history(days=days, vs_currency=selected_currency)
        return {
            "spot": spot,
            "history": history,
        }
    except DataFetcherError as exc:
        logger.exception("Price fetch failed")
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@app.post("/api/analyze", response_model=AnalyzeResponse)
def analyze(payload: AnalyzeRequest) -> AnalyzeResponse:
    try:
        if payload.txid:
            raw_tx = get_transaction(payload.txid)
            parsed_txs = [parse_transaction(raw_tx)]
            response_address = payload.address or payload.txid
        else:
            parsed_txs = parse_transactions(payload.address, limit=payload.limit)
            response_address = payload.address

        classifications = classify_transactions(parsed_txs)
        behavior_patterns = classify_behavior(parsed_txs)

        if payload.address:
            risk = compute_risk_score(payload.address, parsed_txs=parsed_txs)
        else:
            risk = {
                "score": 0,
                "reasons": ["Risk score requires an address context"],
                "breakdown": {
                    "tx_count": len(parsed_txs),
                    "classifications": classifications.get("counts", {}),
                },
            }

        graph_payload = None
        if payload.include_graph:
            graph = build_graph(parsed_txs)
            centrality = degree_centrality(graph)
            graph_payload = _serialize_graph(graph, centrality)

        return AnalyzeResponse(
            address=response_address,
            tx_count=len(parsed_txs),
            classification_counts=classifications.get("counts", {}),
            behavior_patterns=behavior_patterns,
            risk=risk,
            graph=graph_payload,
        )
    except DataFetcherError as exc:
        logger.exception("Upstream request failed")
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Unexpected analyze failure")
        raise HTTPException(status_code=500, detail="Internal analysis error") from exc


@app.post("/api/analyze/txids", response_model=AnalyzeTxidsResponse)
def analyze_txids(payload: AnalyzeTxidsRequest) -> AnalyzeTxidsResponse:
    try:
        # De-duplicate while preserving input order.
        deduped_txids = list(dict.fromkeys(payload.txids))

        raw_txs = [get_transaction(txid) for txid in deduped_txids]
        parsed_txs = [parse_transaction(tx) for tx in raw_txs]

        classifications = classify_transactions(parsed_txs)
        behavior_patterns = classify_behavior(parsed_txs)

        graph_payload = None
        if payload.include_graph:
            graph = build_graph(parsed_txs)
            centrality = degree_centrality(graph)
            graph_payload = _serialize_graph(graph, centrality)

        risk_payload = None
        if payload.focus_address:
            risk_payload = compute_risk_score(payload.focus_address, parsed_txs=parsed_txs)

        return AnalyzeTxidsResponse(
            txids=deduped_txids,
            tx_count=len(parsed_txs),
            classification_counts=classifications.get("counts", {}),
            behavior_patterns=behavior_patterns,
            risk=risk_payload,
            graph=graph_payload,
        )
    except DataFetcherError as exc:
        logger.exception("Upstream request failed")
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Unexpected txid analyze failure")
        raise HTTPException(status_code=500, detail="Internal analysis error") from exc


@app.post("/api/analyze/fake", response_model=AnalyzeFakeResponse)
def analyze_fake() -> AnalyzeFakeResponse:
    try:
        # Generate a fresh batch of 100 transactions on-the-fly dynamically
        # No seed passed means it will generate completely different patterns and scores every request
        raw_fake_txs = generate_fake_transactions(count=100, seed=None)
        
        parsed_txs = [parse_fake_transaction(tx) for tx in raw_fake_txs]

        classifications = classify_transactions(parsed_txs)
        behavior_patterns = classify_behavior(parsed_txs)

        graph = build_graph(parsed_txs)
        centrality = degree_centrality(graph)
        graph_payload = _serialize_graph(graph, centrality)

        focus_address = parsed_txs[0]["inputs"][0]["address"] if parsed_txs else None
        risk_payload = None
        if focus_address:
            risk_payload = compute_risk_score(focus_address, parsed_txs=parsed_txs)
            logger.info(f"Fake TX analyze - Generated {len(raw_fake_txs)} txs, Risk Score: {risk_payload.get('score')}")

        return AnalyzeFakeResponse(
            tx_count=len(parsed_txs),
            classification_counts=classifications.get("counts", {}),
            behavior_patterns=behavior_patterns,
            risk=risk_payload,
            graph=graph_payload,
        )
    except Exception as exc:
        logger.exception("Unexpected fake transaction analyze failure")
        raise HTTPException(status_code=500, detail="Internal analysis error") from exc


if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=False)
