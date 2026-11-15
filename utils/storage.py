"""CSV storage. Every write to database/ and reports/history/ is an append ("a") with fsync (WAL-style)."""
from __future__ import annotations

import csv
import json
import os
import threading
from datetime import datetime
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
_lock = threading.RLock()

CUSTOMER_COLS = ["ts", "customer_id", "profile", "account_id", "account_age_days", "status", "balance", "version"]
TXN_COLS = ["ts", "txn_id", "customer_id", "account_id", "kind", "amount", "status", "idempotency_key",
            "risk_score", "tier", "network", "lock_state", "version", "note"]


def resolve(p) -> Path:
    p = Path(p)
    return p if p.is_absolute() else ROOT / p


def now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]


def append_row(path, row: dict, cols: list[str]) -> None:
    p = resolve(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with _lock:
        new = not p.exists() or p.stat().st_size == 0
        with open(p, "a", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore", restval="", lineterminator="\n")
            if new:
                w.writeheader()
            w.writerow({"ts": now(), **row})
            f.flush()
            os.fsync(f.fileno())


def read_df(path, cols: list[str]) -> pd.DataFrame:
    p = resolve(path)
    if not p.exists() or p.stat().st_size == 0:
        return pd.DataFrame(columns=cols)
    with _lock:
        return pd.read_csv(p)


def append_history(event: dict) -> None:
    p = ROOT / "reports" / "history" / "events.jsonl"
    p.parent.mkdir(parents=True, exist_ok=True)
    with _lock, open(p, "a", encoding="utf-8") as f:
        f.write(json.dumps({"ts": now(), **event}, default=str) + "\n")


def online_url() -> str | None:
    p = ROOT / "database" / "online.txt"
    if not p.exists():
        return None
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            return line
    return None
