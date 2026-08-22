# ChartTestUI

## Local Setup

The repository contains a FastAPI backend and a Next.js frontend.

1. Create and activate the Python environment, then install the backend dependencies:

	```bash
	python -m pip install -r requirements.txt
	```

2. Copy the credential template in `.env` and set `MT5_LOGIN`, `MT5_PASSWORD`, and
	`MT5_SERVER`. Keep credentials out of source control. Set `USE_MT5=false` to use the
	cached CoinGecko fallback when MT5 is unavailable.

3. Start the FastAPI backend:

	```bash
	uvicorn main:app --reload --port 8000
	```

4. Install and start the Next.js frontend:

	```bash
	npm install
	npm run dev
	```

	The local WebSocket endpoint is configured in `.env.local` as
	`NEXT_PUBLIC_WS_URL=ws://localhost:8000/ws/signals`.

The unified market adapter is available through `market_aggregator.py`. It accepts one
entry from `UNIFIED_SYMBOLS` and returns a common `time, open, high, low, close, volume`
DataFrame. MT5, CoinGecko, and yfinance failures are isolated per symbol and return
`None`, so a provider outage does not stop the monitoring loop.

## Vercel Test Deployment

Import this repository into Vercel and use the default Next.js build settings. Configure
the following Vercel environment variable:

```text
NEXT_PUBLIC_WS_URL=wss://your-backend.example.com/ws/signals
```

The FastAPI server must be deployed separately on a WebSocket-capable host. Configure its
`BACKEND_CORS_ORIGINS` variable with the exact Vercel origin, for example:

```text
BACKEND_CORS_ORIGINS=https://your-project.vercel.app
```

For local testing, `BACKEND_CORS_ORIGINS=*` is accepted. The frontend uses the live
`chart_data`, `wuxing_phase`, and status fields from the WebSocket to render the command
center and M7 chart. When MT5 is unavailable, the backend falls back to CoinGecko with a
cache interval controlled by `COINGECKO_CACHE_SECONDS`.