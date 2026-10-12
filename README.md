# OP Mainnet Revenue

## Overview
Who makes money on OP Mainnet, how much the sequencer keeps, and how to grow that take over the next 12 months. This repository holds the data, SQL, notebooks and tests behind the accompanying presentation; [`AI-USAGE.md`](AI-USAGE.md) describes how AI tools were used.

## How to run
Prerequisites: [uv](https://docs.astral.sh/uv/), Python 3.13+.
```bash
uv sync --all-groups
uv run python -m src.pull_external          # optional: refresh the growthepie snapshot (committed)
uv run python -m src.pull_block_headers     # optional: refresh the OP Mainnet block-header sample (committed)
uv run python -m src.build_db               # CSVs + snapshots -> data/opm.duckdb, runs sql/customers.sql
uv run pytest -q                            # reconciliation tests
for nb in notebooks/0*.ipynb; do uv run jupyter nbconvert --execute --to notebook --inplace "$nb"; done   # in order: 01, 02, 03
```

## Layout
| Path | Description |
|---|---|
| `case_study_data/` | Provided data, untouched: CSVs, the SQL that produced them and its README with the dictionary (the JSON copies of the same rows are not included) |
| `data/external/` | growthepie snapshot and OP Mainnet block-header sample, with pull timestamps and URLs |
| `data/overrides/` | Hand-curated address → app mapping with evidence |
| `sql/customers.sql` | Address → app mapping, segments and monthly fees by app, shared by the notebooks and the tests (run by `build_db`) |
| `src/` | Data pulls, database build, chart style, number registry |
| `notebooks/` | 01 revenue · 02 customers · 03 growth: one DuckDB query per cell, pandas tables, the charts inline; each writes its `rev_` / `cust_` / `growth_` numbers to `output/numbers.json` (executed, outputs kept; `uv run jupyter lab`) |
| `tests/` | Reconciliation tests (file 06 ↔ file 01, growthepie ↔ file 01, label coverage, customer mapping) |
| `output/` | `numbers.json`, every figure on the slides with a note on how it was calculated |

## Definitions
- **Window.** Trailing 12 months (TTM) = 2025-09-16 → 2026-09-15. Prior period = 2025-01-01 → 2025-09-15, compared per day.
- **Gross fees.** Fees users pay on OP Mainnet (file 01): L2 execution + L1 data fee.
- **L1 cost (primary basis).** The L1 data fee charged to users, file 01 `l1_data_fee_eth`. This is the internal field; on this basis net sequencer revenue equals execution fees.
- **L1 cost (cross-check).** What OP actually paid Ethereum to post data: growthepie `rent_paid_eth`. growthepie's `fees_paid_eth` reproduces file 01 to within 0.1% in every full month, which is the check that lets us trust its cost series. The two differ: in the trailing year the fee charged covered only about 30% of the actual cost, so the true-cost net is lower than the primary one; both are reported, and the gap is the "L1 fee recovery" lever.
- **Net sequencer revenue ("our share").** Gross fees − L1 cost (primary). ETH is the base unit; USD uses the daily ETH price in file 02.
- **App fees / app revenue.** DefiLlama (file 08). Take rate = OP net / app fees.
- **Customer.** The destination address of a transaction (file 06), grouped into an app via file 07 labels plus `data/overrides/`.

## Assumptions and caveats
- **L1 cost** on the primary basis is the L1 data fee charged (file 01). growthepie's `rent_paid` is the cross-check for what OP actually paid; its OP fee series is anomalous on 2025-04-13 and 2025-04-14 (doubled), and those days are excluded from the reconciliation test and from peer fee-per-transaction changes. The cost series on those days is normal across chains and is kept.
- **High-frequency (bot-like) traffic** = a destination receiving at least 1,000 transactions per distinct sender on a day; this is the behavioural measure the floor model applies retention to. The customer segment **bots and automation** is a different, label-and-rule based grouping of addresses. **Priority bidder** = a destination-day with an effective execution gas price of at least 0.1 gwei; this is inferred from the effective price, since the data has no priority-fee field. Shares move with the thresholds, the direction does not (sensitivity table in notebook 01).
- **Wintermute** is treated as one customer across three contracts. The third, `0x1ef354…`, is unlabelled and is attributed by inference: it started on the day the two labelled contracts stopped, with the same sender count, gas per transaction and price band, and the same handover pattern happened once before in March 2025. It is marked "inferred" wherever it appears.
- **Gas target change** (May 2025) and **minimum base fee = 0** are read from OP Mainnet block headers through the public RPC. No announcement was found; the link to the price fall is stated as consistent with the data, not proven. Contract deployments (file 05) jumped on the day of the first change. The two late-2025 steps in bidder tips coincide with slower trading (files 06, 09, 14); also consistent, not proven.
- **App fees and revenue** are DefiLlama's. Revenue is missing for part of app fees, so "take of app revenue" is an upper bound. 118 of 159 protocols have no labelled address on OP Mainnet and cannot be matched to what they pay in sequencer fees.
- **Growth model** holds priority-bidder fees flat, applies retention only to bot-like traffic, and scales L1 cost with retained transactions. Governance timing and batcher cost at higher volume are not modelled. USD scales one for one with ETH price.
- **Payments and trading levers** are stated assumptions, not estimates: payments = ether.fi's June–August 2026 net run-rate × 50% growth; trading = run-rate net × the trading segments' share (bots and automation, unlabeled, DEX, exchanges: 48%) × 25% more volume, with fees assumed to move one for one with volume (monthly fees and DEX volume in ETH correlate at 0.94, mostly a shared downtrend).
- **Activity table** (first vs second half of the trailing year): stablecoin transfers use Allium's bot-filtered `adjusted_volume_usd`; net bridged excludes bridge aggregators; deposits are DefiLlama headline TVL on the last day of each half (a rebound: TVL was $452M when the year started).
- **Peers** use growthepie's own USD for all three chains over the same daily window; those USD figures differ from the file 02 basis by up to a few percent in some months, so OP's own P&L is never shown next to peer USD on one chart.
