"""Samples OP Mainnet block headers every 6 hours over the case-study window from the public RPC.

The header carries the gas limit, gas used, base fee and (from Holocene) the EIP-1559 parameters in
`extraData`: version u8 | denominator u32 | elasticity u32 [| minBaseFee u64 from Jovian, version 1].
Spec: https://specs.optimism.io/protocol/holocene/exec-engine.html, .../jovian/exec-engine.html
"""

import time
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta

import polars as pl
import requests

from src.pull_external import OUT, record_pull

RPC = "https://mainnet.optimism.io"
START = datetime(2025, 1, 1, tzinfo=UTC)
END = datetime(2026, 9, 15, 18, tzinfo=UTC)
STEP = timedelta(hours=6)
BLOCK_SECONDS = 2
WORKERS = 4
RETRIES = 8


def get_block(tag: str) -> dict:
    payload = {"jsonrpc": "2.0", "id": 1, "method": "eth_getBlockByNumber", "params": [tag, False]}
    for attempt in range(RETRIES):
        response = requests.post(RPC, json=payload, timeout=60)
        if response.status_code != 429:
            break
        time.sleep(2**attempt)  # public RPC rate limit: back off and retry
    response.raise_for_status()
    return response.json()["result"]


def decode_extra_data(extra: str) -> dict:
    raw = bytes.fromhex(extra[2:])
    if len(raw) < 9:
        return {"extra_data_version": None, "eip1559_denominator": None, "eip1559_elasticity": None, "min_base_fee_wei": None}
    return {
        "extra_data_version": raw[0],
        "eip1559_denominator": int.from_bytes(raw[1:5], "big"),
        "eip1559_elasticity": int.from_bytes(raw[5:9], "big"),
        "min_base_fee_wei": int.from_bytes(raw[9:17], "big") if len(raw) >= 17 else None,
    }


def sample(number: int, at: datetime) -> dict:
    block = get_block(hex(number))
    ts = datetime.fromtimestamp(int(block["timestamp"], 16), UTC)
    assert abs(ts - at) < timedelta(seconds=BLOCK_SECONDS), f"block {number} is at {ts}, expected {at}"
    return {
        "block": number,
        "timestamp_utc": ts.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "date": ts.date().isoformat(),
        "gas_limit": int(block["gasLimit"], 16),
        "gas_used": int(block["gasUsed"], 16),
        "base_fee_wei": int(block["baseFeePerGas"], 16),
        **decode_extra_data(block["extraData"]),
    }


def main() -> None:
    latest = get_block("latest")
    anchor_number, anchor_ts = int(latest["number"], 16), int(latest["timestamp"], 16)
    times = [START + i * STEP for i in range(int((END - START) / STEP) + 1)]
    numbers = [anchor_number - (anchor_ts - int(at.timestamp())) // BLOCK_SECONDS for at in times]
    with ThreadPoolExecutor(WORKERS) as pool:
        rows = list(pool.map(sample, numbers, times))
    pl.DataFrame(rows, infer_schema_length=None).write_csv(OUT / "op_block_headers.csv")
    stamp = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    record_pull("op_block_headers", f"pulled_at_utc: {stamp} {RPC} eth_getBlockByNumber every {STEP} {START:%Y-%m-%d}..{END:%Y-%m-%d}")


if __name__ == "__main__":
    main()
