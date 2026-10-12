import json
from pathlib import Path

PATH = Path(__file__).resolve().parents[1] / "output" / "numbers.json"


def load() -> dict:
    return json.loads(PATH.read_text()) if PATH.exists() else {}


def save(numbers: dict) -> None:
    PATH.write_text(json.dumps(numbers, sort_keys=True, indent=2, default=lambda v: v.item()) + "\n")  # numpy scalars from pandas


def record(key: str, value, note: str = "") -> None:
    save(load() | {key: {"value": value, "note": note}})


def clear(prefix: str) -> None:
    save({k: v for k, v in load().items() if not k.startswith(prefix)})
