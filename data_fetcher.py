from typing import Any, Dict, List, Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

BASE_URL = "https://blockstream.info/api"
COINGECKO_BASE_URL = "https://api.coingecko.com/api/v3"
DEFAULT_TIMEOUT_SECONDS = 12


class DataFetcherError(RuntimeError):
    """Raised when an upstream API request fails."""


def _build_session() -> requests.Session:
    session = requests.Session()
    retry = Retry(
        total=3,
        connect=3,
        read=3,
        backoff_factor=0.6,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=frozenset(["GET"]),
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


_SESSION = _build_session()


def _get_json(url: str, timeout: int = DEFAULT_TIMEOUT_SECONDS) -> Any:
    try:
        response = _SESSION.get(url, timeout=timeout)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as exc:
        raise DataFetcherError(f"Request failed for {url}: {exc}") from exc


def get_address_info(address: str) -> Dict[str, Any]:
    url = f"{BASE_URL}/address/{address}"
    return _get_json(url)


def get_transaction(txid: str) -> Dict[str, Any]:
    url = f"{BASE_URL}/tx/{txid}"
    return _get_json(url)


def get_address_txs(address: str, max_txs: Optional[int] = 200) -> List[Dict[str, Any]]:
    """Fetch transactions for an address with pagination support.

    Blockstream returns address transactions in pages (25 per request). This
    function walks pagination via `/txs/chain/{last_seen_txid}` to avoid only
    using the first page.
    """
    collected: List[Dict[str, Any]] = []
    next_url = f"{BASE_URL}/address/{address}/txs"

    while next_url:
        batch = _get_json(next_url)
        if not isinstance(batch, list) or not batch:
            break

        collected.extend(batch)

        if max_txs is not None and len(collected) >= max_txs:
            return collected[:max_txs]

        # Blockstream pagination uses last txid from previous page.
        last_txid = batch[-1].get("txid") if isinstance(batch[-1], dict) else None
        if not last_txid:
            break
        next_url = f"{BASE_URL}/address/{address}/txs/chain/{last_txid}"

    return collected


def get_btc_spot_price(vs_currency: str = "usd") -> Dict[str, float]:
    """Fetch current BTC spot price using CoinGecko simple price endpoint."""
    url = f"{COINGECKO_BASE_URL}/simple/price?ids=bitcoin&vs_currencies={vs_currency}"
    data = _get_json(url)
    price = float(data.get("bitcoin", {}).get(vs_currency, 0.0))
    return {"currency": vs_currency, "price": price}


def get_btc_price_history(days: int = 30, vs_currency: str = "usd") -> Dict[str, Any]:
    """Fetch BTC historical market chart data from CoinGecko.

    Returns a dict that includes a `prices` list with [timestamp_ms, price] tuples.
    """
    safe_days = max(1, min(int(days), 3650))
    url = (
        f"{COINGECKO_BASE_URL}/coins/bitcoin/market_chart"
        f"?vs_currency={vs_currency}&days={safe_days}&interval=daily"
    )
    data = _get_json(url)
    return {
        "currency": vs_currency,
        "days": safe_days,
        "prices": data.get("prices", []),
        "market_caps": data.get("market_caps", []),
        "total_volumes": data.get("total_volumes", []),
    }
