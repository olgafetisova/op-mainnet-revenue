# External snapshots

Each puller writes one line to `PULLED.txt` with its timestamp and exact URLs.

## growthepie_metrics.csv
Pulled by `uv run python -m src.pull_external`. Cut to `date >= 2025-01-01` and runs to the day before the pull
(2026-10-08), so it extends past the case study window (2025-01-01..2026-09-15). The source revises recent days.

growthepie export API (`api.growthepie.com/v1/export/{fees,rent_paid,profit,txcount}.json`), kept for
`origin_key in ('optimism', 'base', 'arbitrum')`. Long format: `origin_key, metric_key, date, value`.

| metric_key | Meaning |
|---|---|
| `fees_paid_eth` / `_usd` | Transaction fees paid by users on the L2 (matches file 01 `total_fee_eth` for optimism) |
| `rent_paid_eth` / `_usd` | What the chain paid Ethereum L1 to post its data (blobs/calldata) |
| `profit_eth` / `_usd` | `fees_paid - rent_paid` |
| `txcount` | Daily transactions |

`export/txcount.json` returned 200, so the `fundamentals.json` fallback was not needed.

## op_block_headers.csv
OP Mainnet block headers sampled every 6 hours (00/06/12/18 UTC, nearest 2-second block) from 2025-01-01 to 2026-09-15,
fetched from the public RPC `https://mainnet.optimism.io` with `eth_getBlockByNumber` by `uv run python -m src.pull_block_headers`
(pulled 2026-10-09). Columns: `block, timestamp_utc, date, gas_limit, gas_used, base_fee_wei`, plus the EIP-1559 parameters
decoded from `extraData` (`extra_data_version, eip1559_denominator, eip1559_elasticity, min_base_fee_wei`). Before Holocene
(2025-01-09 18:00 UTC) `extraData` is empty, so those fields are null; `min_base_fee_wei` exists from Jovian (2025-12-02).
Encoding: https://specs.optimism.io/protocol/holocene/exec-engine.html and .../jovian/exec-engine.html.

## Known quirk
growthepie `fees_paid_eth`/`_usd` (and therefore `profit_*`) for optimism is inflated on 2025-04-13
(exactly double file 01) and 2025-04-14 (+72%); `txcount` and `rent_paid_*` on those days look normal.
The sequencer P&L (notebook 01, `pnl_daily`) takes gross fees from file 01 and only `rent_paid_eth` from growthepie, so it
is unaffected; the reconciliation test and the peer fee-per-transaction change exclude both days. Every other day matches file 01 within 1.7%.
