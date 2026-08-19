# DealDog

Product search and price tracking across retailers. You search for a product; the backend pulls
listings from several shops, works out which of them are the *same* product, and tracks each one's
price per retailer over time.

Comparing prices sounds like a sorting problem. It isn't — it's an identity problem, and that is
what this project is actually about. Before you can say "$50 cheaper at Walmart" you have to be
certain both listings are the same physical thing, and all you ever get from a retailer is a title
someone in marketing wrote. Everything below is a way that goes wrong, and what DealDog does
about it.

> **No real scraping yet.** Listings come from a hardcoded catalog in `backend/app/dummy.py`.
> Everything downstream — extraction, grouping, matching, embeddings, pgvector dedup, price
> history — is real, and reads those titles through exactly the path a scraper's output would
> take. Every example below is a real row from that catalog.

---

## 1. One product, five different titles

These three listings are the same laptop:

```
amazon    Apple 2024 MacBook Air 13-inch Laptop with M3 chip, 8GB Memory, 256GB SSD - Space Gray
bestbuy   Apple MacBook Air 13.6" M3 8GB RAM 256GB SSD Space Gray (2024)
walmart   MacBook Air 13" M3 8/256GB Space Gray Laptop
```

There is no shared word order and no shared vocabulary. One spec appears as `8GB Memory`,
`8GB RAM` and `8/256GB`; one screen appears as `13-inch`, `13.6"` and `13"`; the year is a prefix,
a suffix in parentheses, or absent. The Walmart title never says "Apple" at all.

String similarity is hopeless here — the Walmart title is closer to a Walmart *MacBook Pro* title
than to the Amazon row that describes the identical machine, because retailers are internally
consistent and mutually incompatible.

**What DealDog does.** It never compares titles. An LLM first reads every title into structured
attributes — `brand`, `category`, `item`, `model`, and open-ended per-category `specs` — and
normalizes the wording, so all three rows above collapse to the same thing:

```json
{"brand": "Apple", "category": "laptop", "item": "laptop", "model": "MacBook Air 13-inch",
 "specs": {"chip": "M3", "ram": "8GB", "storage": "256GB", "color": "space gray"}}
```

Identity is then a comparison between attribute sets, not between sentences. `brand` is
deliberately left out of that key, which is the detail that lets the brandless Walmart listing
group with its two Apple-branded twins instead of stranding itself.

## 2. Identifiers solve this — right up until they don't

Amazon and Best Buy both expose ASIN `A1001` for that laptop. Two listings carrying the same
identifier are the same product, full stop: no inference, no threshold, no doubt.

The trap is building on that. The Walmart row has no identifier at all, and that is the ordinary
case — most shops publish their own SKU or nothing.

**What DealDog does.** Identifiers are a fast path, never the mechanism: a shared identifier
short-circuits straight to a match with confidence `1.0`, and everything without one falls through
to the attribute and embedding tiers rather than being treated as unmatchable.

## 3. Two products three characters apart

Take the Amazon title from §1 and change `8GB Memory, 256GB SSD` to `16GB Memory, 512GB SSD`.
Three characters in a hundred-character string, and it is a different laptop — $1,099 against
$1,399. Every text-similarity measure and every embedding puts those two titles almost on top of
each other.

This is the expensive direction to be wrong in, and the asymmetry matters:

- **A missed match** costs the user a duplicate card in their saved list. Annoying, reversible.
- **A false merge** is unrecoverable. Two products' prices land in one history, the chart becomes
  fiction, and every price-drop alert computed from it afterwards is noise. Un-merging cannot
  restore which price came from which product.

**What DealDog does.** Grouping merges two listings only on a shared identifier or on a full
attribute-set match — never on being close. Normalization is scoped to match that: it folds case
and spacing so `8 GB` and `8GB` are one value, but it deliberately leaves unit *names* alone,
because stripping them would make `1 TB` and `1 GB` collide. Cheap ways to look tidy are exactly
how variants get merged.

## 4. Accessories impersonate the product they fit

This is a real row in the catalog:

```
amazon    Apple MacBook Air M3 13-inch Clear Case Cover        $19
```

It shares nearly every word with the $1,099 laptop, and it is cheaper than every genuine listing.
An unguarded pipeline therefore does the worst possible thing with it: presents a $19 case as the
best deal on a MacBook Air, or files it into the laptop's price history as a 98% price crash.

Embeddings make this worse rather than better. Every category shares one vector space, so a case
and the laptop it fits sit close together by construction — they are *about* the same object.

**What DealDog does**, in two places:

- Extraction distinguishes `category`/`item` from the thing an accessory is *made for*. The case
  is `item: laptop case` with the host device recorded as a spec, never as its `model`.
- Matching vetoes on that. A stated disagreement on `brand`, `category` or `item` drops similarity
  to zero before any near-miss score can merge the pair — so `laptop case` cannot land in
  `laptop`'s history regardless of how close the vectors are. A missing value on either side is
  not evidence and never vetoes; only a stated conflict does.

Separately, the relevance filter drops accessories from results whose query asked for the product
itself — unless you actually searched for the case.

## 5. Every product class needs different specs

A laptop is pinned down by chip, RAM and storage. A television needs screen size, resolution and
panel type. Running shoes need gender, colour and size. Olive oil needs volume. A fixed schema
either explodes into hundreds of nullable columns or quietly discards the one spec that
distinguishes two variants.

**What DealDog does.** `specs` is open-ended by design — the model picks the keys that matter for
whatever it's looking at, in `snake_case`, with only attributes that change the physical thing the
buyer receives (no marketing language, no warranty, no shipping). There is no category list and no
hardcoded attribute anywhere in `backend/app/`; `attributes.py` only normalizes what came back.
Adding a product class costs nothing.

## 6. Search queries are ambiguous, and guessing is worse than not

`macbook m` doesn't name a generation. `laptop` constrains nothing at all. `size 1` could be a
lot of things. A filter confident enough to resolve those on the user's behalf will silently hide
the listing they were looking for, and neither of you will ever know.

**What DealDog does.** The relevance filter is explicitly rule-bound rather than free to infer: a
query naming no brand, model or spec keeps every listing of that class; a partial fragment does
not pin down a generation, so all candidates survive; and silence is not a contradiction — a
listing that simply fails to mention a spec stays in, while only a stated, *different* value rules
it out.

## 7. Sometimes the text genuinely cannot decide

Two listings can be one product or two, and no amount of parsing settles it. A system that always
guesses is wrong at a rate it cannot even measure.

**What DealDog does.** It declines to guess in the band where guessing is unjustified. Similarity
above `MATCH_THRESHOLD` (0.90) matches automatically; below `PENDING_LOW` (0.80) it's a new
product; in between, the group is surfaced in the UI as a *possible* match with a yes/no, and the
user's answer decides. Nothing is persisted until they choose to track it.

## 8. A broken pipeline should fail, not improvise

Attribute extraction depends on an LLM. The tempting fallback is a regex layer for when the API
key is missing or the call fails — which produces half-understood titles, and therefore wrong
groups, wrong matches, and a wrong price history that looks perfectly plausible on a chart.

**What DealDog does.** Extraction has no fallback on purpose: without `OPENAI_API_KEY`,
`/api/search` returns `503` and says so. Relevance filtering is the one deliberate exception —
it only narrows an already-correct result set, so a failed call degrades to "show everything"
rather than to a wrong answer. Embeddings do fall back to feature hashing, and the app runs on an
in-memory store when `DATABASE_URL` is absent.

---

## How it fits together

```
query ──► listings ──► extract attributes (LLM) ──► group (identifier OR attribute key)
                                                          │
                                                          ▼
                                    T1  shared identifier        ─► matched (1.0)
                                    T2  pgvector nearest
                                        + brand/category/item veto
                                                          │
                                    ┌─────────────────────┼──────────────────────┐
                                 ≥ 0.90              0.80–0.90                < 0.80
                                 matched         T3 ask the user               new
```

`CONTEXT.md` has the architecture, data model and design rationale in full.

| Layer | Choice |
|---|---|
| Frontend | React 18 + Vite + TypeScript (Vercel) |
| Backend | Python 3.11+, FastAPI, SQLAlchemy 2.x (Docker on a VM) |
| Database | Neon Postgres + `pgvector` |
| LLM | OpenAI `gpt-4o-mini`, JSON mode — extraction and relevance |
| Embeddings | OpenAI `text-embedding-3-small`, 1536-dim |

## Running it locally

```bash
cd backend
python3 -m venv .venv && .venv/bin/pip install -e ".[dev]"
cp .env.example .env                   # set DATABASE_URL + OPENAI_API_KEY
.venv/bin/python -m app.cli init-db    # one-time: pgvector extension + tables
.venv/bin/uvicorn app.main:app --reload --port 8000

cd frontend && npm install && npm run dev    # :5173, proxies /api to :8000
```

Leave `VITE_API_BASE_URL` unset locally — the Vite dev proxy handles `/api`. `make lint` runs
ruff; there is no test suite yet.

## Deploying

The frontend is a static bundle on Vercel; the backend is one container on a VM talking to Neon.

```bash
# on the VM
cp backend/.env.example backend/.env   # DATABASE_URL, OPENAI_API_KEY, CORS_ORIGINS
docker compose up -d --build
```

Compose defines a single service — the database is hosted and TLS is terminated by the VM's
existing reverse proxy. Schema creation runs at startup, so `init-db` isn't needed here. The
container publishes on `127.0.0.1:8000`; point the proxy there.

On Vercel: root directory `frontend`, build `npm run build`, output `dist`, and set
`VITE_API_BASE_URL` to the backend origin — no `/api` suffix, no trailing slash, and it must be
`https://`, since the browser blocks plain-http calls from a TLS page. The value is inlined at
build time, so changing it needs a redeploy. Add that Vercel domain to `CORS_ORIGINS` on the
backend, including preview domains if you want previews to work.

## Reference

`backend/.env` — see `backend/.env.example` for the full list.

| Variable | Purpose |
|---|---|
| `DATABASE_URL` | Neon connection string. Use `postgresql://` or `postgresql+psycopg2://` — the `+psycopg` (v3) driver is not installed |
| `OPENAI_API_KEY` | Required; `/api/search` returns 503 without it |
| `CORS_ORIGINS` | Comma-separated browser origins allowed to call the API. Defaults to `*` |
| `LLM_MODEL`, `EMBEDDING_MODEL`, `EMBEDDING_DIM` | Model selection |
| `MATCH_THRESHOLD`, `PENDING_LOW`, `TOP_K` | Match tiers — see §7 |
| `DROP_PERCENT_THRESHOLD`, `DROP_ABSOLUTE_THRESHOLD`, `DROP_WINDOW` | Price-drop detection; a drop must clear both thresholds to be flagged |

| Method | Path | Description |
|---|---|---|
| GET | `/api/health` | Liveness |
| GET | `/api/search?q=` | Search, group, match against tracked products |
| POST | `/api/track` | Save a group, or link it to an existing product |
| GET | `/api/tracked` | Saved products with best price and history |
| GET | `/api/products/{id}` | Product detail with price history |
| GET/POST | `/api/products/{id}/history` | Read or refresh price history |
