import time
from datetime import UTC, datetime
from pathlib import Path

import polars as pl
import requests

OUT = Path(__file__).resolve().parents[1] / "data" / "external"
START = "2025-01-01"
ORIGINS = ["optimism", "base", "arbitrum"]
GTP_URL = "https://api.growthepie.com/v1/export/{}.json"
GTP_EXPORTS = ["fees", "rent_paid", "profit", "txcount"]
SECONDS_BETWEEN_REQUESTS = 6.5  # keeps us under 10 requests/minute


def fetch(url: str, pulled: list[str]):
    if pulled:
        time.sleep(SECONDS_BETWEEN_REQUESTS)
    response = requests.get(url, timeout=120)
    response.raise_for_status()
    pulled.append(url)
    return response.json()


def pull_growthepie(pulled: list[str]) -> pl.DataFrame:
    frames = [pl.DataFrame(fetch(GTP_URL.format(name), pulled)) for name in GTP_EXPORTS]
    return (
        pl.concat(frames)
        .filter(pl.col("origin_key").is_in(ORIGINS), pl.col("date") >= START)
        .select("origin_key", "metric_key", "date", "value")
        .sort("origin_key", "metric_key", "date")
    )


def main() -> None:
    pulled: list[str] = []
    pull_growthepie(pulled).write_csv(OUT / "growthepie_metrics.csv")
    stamp = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    record_pull("growthepie", f"pulled_at_utc: {stamp} " + " ".join(pulled))


def record_pull(source: str, details: str) -> None:
    """Rewrite this source's line in PULLED.txt, keeping the other pullers' lines."""
    path = OUT / "PULLED.txt"
    lines = path.read_text().splitlines() if path.exists() else []
    kept = [line for line in lines if not line.startswith(f"{source} ")]
    path.write_text("\n".join([*kept, f"{source} {details}"]) + "\n")


if __name__ == "__main__":
    main()
