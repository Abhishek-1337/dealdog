# DealDog

Product search and price tracking. You search for a product; the backend pulls listings from
several retailers, works out which of them are the *same* product, and tracks each one's price
per retailer over time.

The hard part is that no two shops write a title the same way. `"Apple 2024 MacBook Air 13-inch
Laptop with M3 chip, 8GB Memory, 256GB SSD"` and `"MacBook Air 13\" M3 8/256GB Space Gray"` are
one product; the same title with `16GB` is not. So before anything is compared or saved:

1. An LLM extracts structured attributes (brand, category, item, model, per-category specs) from
   each raw title.
2. Listings are grouped by those attributes, so clearly-different variants are never compared.
3. A tiered pipeline matches each group against already-tracked products — hard identifiers
   first, then pgvector nearest-neighbour plus conflict rules, then a human yes/no.

Architecture, data model and design rationale live in [CONTEXT.md](CONTEXT.md).

> **No real scraping yet.** Listings come from a hardcoded catalog in `backend/app/dummy.py`.
> Everything downstream — extraction, grouping, matching, embeddings, pgvector dedup, price
> history — is real, and reads the dummy titles through exactly the path a scraper's titles
> would take.

## Stack

| Layer | Choice |
|---|---|
| Frontend | React 18 + Vite + TypeScript (Vercel) |
| Backend | Python 3.11+, FastAPI, SQLAlchemy 2.x (Docker on a VM) |
| Database | Neon Postgres + `pgvector` |
| LLM | OpenAI `gpt-4o-mini` (JSON mode) for extraction and relevance |
| Embeddings | OpenAI `text-embedding-3-small`, 1536-dim |

Attribute extraction has no non-LLM fallback on purpose — a half-understood title yields wrong
groups and a wrong price history, so without `OPENAI_API_KEY` the search endpoint returns 503
rather than guessing. Embeddings do fall back to feature hashing, and without `DATABASE_URL` the
app runs on an in-memory store.

## Local development

```bash
# backend — http://localhost:8000
cd backend
python3 -m venv .venv && .venv/bin/pip install -e ".[dev]"
cp .env.example .env                   # set DATABASE_URL + OPENAI_API_KEY
.venv/bin/python -m app.cli init-db    # one-time: pgvector extension + tables
.venv/bin/uvicorn app.main:app --reload --port 8000

# frontend — http://localhost:5173
cd frontend
npm install
npm run dev
```

Leave `VITE_API_BASE_URL` unset locally: the Vite dev server proxies `/api` to
`localhost:8000`.

`cd backend && make lint` runs ruff. There is no test suite yet — `make test` and the pytest
config are scaffolding for one.

## Deployment

The frontend is a static bundle on Vercel; the backend runs as a container on a VM and talks to
Neon. They are deployed independently.

### Backend (VM)

```bash
git clone <repo> && cd dealdog
cp backend/.env.example backend/.env   # set DATABASE_URL + OPENAI_API_KEY
docker compose up -d --build
```

`docker compose up` is all of it — the database is hosted and TLS is terminated by the VM's
existing reverse proxy, so the compose file defines exactly one service. Schema creation runs on
startup (`ensure_schema`), so `init-db` is not needed here.

The container publishes on `127.0.0.1:8000`, not `0.0.0.0` — point the proxy at that. If your
proxy is itself a container in another compose project, put both on a shared external network
and target `api:8000` instead.

```bash
docker compose logs -f api                       # follow logs
curl -s http://127.0.0.1:8000/api/health         # {"status":"ok"}
docker compose up -d --build                     # redeploy after a pull
```

### Frontend (Vercel)

Root directory `frontend`, build `npm run build`, output `dist`. Set one environment variable:

```
VITE_API_BASE_URL=https://your-backend-domain
```

Backend origin only — no `/api` suffix, no trailing slash. It must be `https://`: Vercel serves
the page over TLS and the browser blocks plain-http requests from it. Vite inlines the value at
build time, so changing it needs a redeploy.

The calls are cross-origin, so the backend has to allow this domain back — put it in
`CORS_ORIGINS` in `backend/.env` and restart the container. Vercel preview deployments get their
own domains, so include those too if you want previews to work.

## Configuration

`backend/.env` — see `backend/.env.example` for the full list.

| Variable | Purpose |
|---|---|
| `DATABASE_URL` | Neon connection string. Use `postgresql://` or `postgresql+psycopg2://` — the `+psycopg` (v3) driver is not installed |
| `OPENAI_API_KEY` | Required; `/api/search` returns 503 without it |
| `CORS_ORIGINS` | Comma-separated browser origins allowed to call the API — set it to your Vercel domain(s) in production. Defaults to `*` |
| `LLM_MODEL`, `EMBEDDING_MODEL`, `EMBEDDING_DIM` | Model selection |
| `MATCH_THRESHOLD`, `PENDING_LOW`, `TOP_K` | Match tiers: above `MATCH_THRESHOLD` auto-matches, above `PENDING_LOW` asks the user, below is a new product |
| `DROP_PERCENT_THRESHOLD`, `DROP_ABSOLUTE_THRESHOLD`, `DROP_WINDOW` | Price-drop detection; a drop must clear both thresholds to be flagged |

## API

| Method | Path | Description |
|---|---|---|
| GET | `/api/health` | Liveness |
| GET | `/api/search?q=` | Search, group, match against tracked products |
| POST | `/api/track` | Save a group as a tracked product, or link it to an existing one |
| GET | `/api/tracked` | Saved products with best price and history |
| GET | `/api/products/{id}` | Product detail with price history |
| GET/POST | `/api/products/{id}/history` | Read or refresh price history |
