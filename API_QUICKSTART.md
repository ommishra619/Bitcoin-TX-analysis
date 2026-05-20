# API Quickstart (Phase 1)

This project now includes a FastAPI backend in `app.py`.

## Start API

```powershell
& "c:/Users/mromm/OneDrive/Desktop/Bitcoin TX analysis/.venv/Scripts/python.exe" app.py
```

Server default: `http://localhost:8000`

OpenAPI docs: `http://localhost:8000/docs`

## Endpoints

### GET /api/health

Returns basic service status.

### GET /api/price?days=30

Returns BTC spot + historical market chart data from CoinGecko.

Example:

```powershell
Invoke-RestMethod -Method Get -Uri "http://localhost:8000/api/price?days=30"
```

### POST /api/analyze

Analyzes a Bitcoin address and returns:
- transaction count
- classification counts
- behavior patterns
- risk score breakdown
- optional graph nodes/edges

Example:

```powershell
$body = @{
  address = "bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh"
  limit = 100
  include_graph = $true
} | ConvertTo-Json

Invoke-RestMethod -Method Post -Uri "http://localhost:8000/api/analyze" -Body $body -ContentType "application/json"
```

## Notes

- Address validation is enabled.
- Upstream API calls include retries and timeout handling.
- CORS origins can be configured via `CORS_ORIGINS` env var (comma-separated).
