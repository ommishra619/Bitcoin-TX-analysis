from fastapi.testclient import TestClient

import app as api


client = TestClient(api.app)


def test_health_endpoint():
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_price_endpoint_with_mock(monkeypatch):
    monkeypatch.setattr(api, "get_btc_spot_price", lambda vs_currency="usd": {"currency": vs_currency, "price": 65000.0})
    monkeypatch.setattr(
        api,
        "get_btc_price_history",
        lambda days=30, vs_currency="usd": {
            "currency": vs_currency,
            "days": days,
            "prices": [[1710000000000, 62000.0], [1710086400000, 62500.0]],
            "market_caps": [],
            "total_volumes": [],
        },
    )

    response = client.get("/api/price?days=7&currency=eur")
    assert response.status_code == 200
    payload = response.json()
    assert payload["spot"]["currency"] == "eur"
    assert payload["spot"]["price"] == 65000.0
    assert payload["history"]["currency"] == "eur"
    assert payload["history"]["days"] == 7
    assert len(payload["history"]["prices"]) == 2


def test_price_endpoint_invalid_currency():
    response = client.get("/api/price?currency=abc")
    assert response.status_code == 400


def test_analyze_endpoint_with_mock(monkeypatch):
    parsed_txs = [
        {
            "txid": "tx1",
            "inputs": [{"address": "A", "value": 0.1}],
            "outputs": [{"address": "B", "value": 0.09}],
        }
    ]

    monkeypatch.setattr(api, "parse_transactions", lambda address, limit=100: parsed_txs)
    monkeypatch.setattr(api, "classify_transactions", lambda txs: {"counts": {"Unclassified / Normal": 1}})
    monkeypatch.setattr(api, "classify_behavior", lambda txs: ["Normal/Unclassified"])
    monkeypatch.setattr(
        api,
        "compute_risk_score",
        lambda address, parsed_txs=None: {
            "score": 12,
            "reasons": ["test"],
            "breakdown": {"tx_count": 1},
        },
    )

    response = client.post(
        "/api/analyze",
        json={
            "address": "bc1qtestaddress0000000000000000000000000000",
            "limit": 10,
            "include_graph": False,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["tx_count"] == 1
    assert payload["classification_counts"]["Unclassified / Normal"] == 1
    assert payload["risk"]["score"] == 12
    assert payload["graph"] is None


def test_analyze_txids_endpoint_with_mock(monkeypatch):
    txid1 = "a" * 64
    txid2 = "b" * 64

    monkeypatch.setattr(api, "get_transaction", lambda txid: {"txid": txid, "vin": [], "vout": []})
    monkeypatch.setattr(
        api,
        "parse_transaction",
        lambda tx: {"txid": tx["txid"], "inputs": [{"address": "X", "value": 1.0}], "outputs": [{"address": "Y", "value": 0.9}]},
    )
    monkeypatch.setattr(api, "classify_transactions", lambda txs: {"counts": {"Unclassified / Normal": len(txs)}})
    monkeypatch.setattr(api, "classify_behavior", lambda txs: ["Normal/Unclassified"])
    monkeypatch.setattr(
        api,
        "compute_risk_score",
        lambda address, parsed_txs=None: {"score": 9, "reasons": ["mock"], "breakdown": {}},
    )

    response = client.post(
        "/api/analyze/txids",
        json={
            "txids": [txid1, txid2, txid1],
            "include_graph": False,
            "focus_address": "bc1qtestaddress0000000000000000000000000000",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["txids"] == [txid1, txid2]
    assert payload["tx_count"] == 2
    assert payload["classification_counts"]["Unclassified / Normal"] == 2
    assert payload["risk"]["score"] == 9
    assert payload["graph"] is None


def test_analyze_txids_endpoint_invalid_txid():
    response = client.post(
        "/api/analyze/txids",
        json={
            "txids": ["not-a-valid-txid"],
        },
    )
    assert response.status_code == 422
