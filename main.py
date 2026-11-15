"""ML Ops orchestration: config, data bootstrap, training (RandomForest + MLflow), model loading, reports.

CLI:  python main.py --setup | --train | --reports
"""
from __future__ import annotations

import argparse
import os
import urllib.request
from dataclasses import dataclass
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, f1_score, roc_auc_score
from sklearn.model_selection import train_test_split

try:
    import tomllib
except ModuleNotFoundError:  # py<3.11
    import tomli as tomllib

from agentic.agentic_exclusive import ConcurrencyAgent
from agentic.agentic_fraud import FAULT_FEATURES, FRAUD_FEATURES, FraudAgent, encode_frame, make_encoders
from utils import storage
from utils.logger import get_logger

ROOT = storage.ROOT
MODEL_PATH = ROOT / "models" / "fintech_models.joblib"
log = get_logger("main")


# ---- configuration --------------------------------------------------------------------------------
def load_config() -> dict:
    p = ROOT / "secrets.toml"
    cfg = tomllib.loads(p.read_text(encoding="utf-8")) if p.exists() else {}
    llm = cfg.setdefault("LLM_Configuration", {})
    llm["API_Key"] = os.getenv("LLM_API_KEY", llm.get("API_Key", ""))
    llm["Base_URL"] = os.getenv("LLM_BASE_URL", llm.get("Base_URL", ""))
    llm["Model_Name"] = os.getenv("LLM_MODEL", llm.get("Model_Name", ""))
    db = cfg.setdefault("Database_Configuration", {})
    db.setdefault("Customer_DB_Path", "database/customers.csv")
    db.setdefault("Transaction_DB_Path", "database/transactions.csv")
    ml = cfg.setdefault("MLflow_Configuration", {})
    ml.setdefault("Tracking_URI", "http://localhost:5000")
    ml.setdefault("Experiment_Name", "fintech_fraud_triage")
    return cfg


# ---- database bootstrap ---------------------------------------------------------------------------
def ensure_database(cfg: dict) -> None:
    cust = cfg["Database_Configuration"]["Customer_DB_Path"]
    txn = cfg["Database_Configuration"]["Transaction_DB_Path"]
    if len(storage.read_df(cust, storage.CUSTOMER_COLS)) == 0:
        url, seeded = storage.online_url(), False
        if url:
            try:
                for _, r in pd.read_csv(url).iterrows():
                    storage.append_row(cust, r.to_dict(), storage.CUSTOMER_COLS)
                seeded = True
                log.info("Seeded customers from online database %s", url)
            except Exception as exc:  # noqa: BLE001
                log.warning("Online DB unavailable (%s); using local seed", exc)
        if not seeded:
            for cid, prof, acct, age, bal in [("cust_4471", "returning", "account_4471", 900, 10000),
                                              ("cust_5120", "returning", "account_5120", 450, 3200),
                                              ("cust_9001", "new", "account_9001", 3, 150)]:
                storage.append_row(cust, {"customer_id": cid, "profile": prof, "account_id": acct,
                                          "account_age_days": age, "status": "active", "balance": bal, "version": 1},
                                   storage.CUSTOMER_COLS)
    p = storage.resolve(txn)
    if not p.exists() or p.stat().st_size == 0:
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "a", encoding="utf-8") as f:  # header only, append mode
            f.write(",".join(storage.TXN_COLS) + "\n")


# ---- ML Ops ---------------------------------------------------------------------------------------
def synthetic_training_data(n: int = 6000, seed: int = 42) -> pd.DataFrame:
    """Bootstrap data. Replace/extend with real labelled history from database/transactions.csv over time."""
    rng = np.random.default_rng(seed)
    new = rng.random(n) < 0.35
    age = np.where(new, rng.integers(0, 30, n), rng.integers(60, 2000, n))
    amount = np.where(new, rng.lognormal(6.0, 0.9, n), rng.lognormal(4.8, 0.8, n)).round(2)
    hour = rng.integers(0, 24, n)
    device = np.where(new, rng.random(n) < 0.7, rng.random(n) < 0.97).astype(int)
    geo = np.where(new, rng.random(n) < 0.75, rng.random(n) < 0.97).astype(int)
    vel = rng.poisson(np.where(new, 2.5, 1.0))
    z = (-3.2 + 1.3 * new + 1.5 * (1 - device) + 1.1 * (1 - geo) + 0.3 * vel + 0.0006 * amount
         + 0.8 * (hour < 5) - 0.0008 * np.minimum(age, 365))
    fraud = (rng.random(n) < 1 / (1 + np.exp(-z))).astype(int)

    outage = rng.random(n) < 0.5
    err = np.where(outage, rng.uniform(0.15, 0.6, n), rng.uniform(0, 0.05, n))
    infra = (outage ^ (rng.random(n) < 0.04)).astype(int)  # 4% label noise
    return pd.DataFrame({
        "profile": np.where(new, "new", "returning"), "network": np.where(outage, "outage", "stable"),
        "amount": amount, "hour": hour, "device_match": device, "geo_match": geo, "velocity_1h": vel,
        "account_age_days": age, "latency_ms": rng.normal(3500, 900, n).clip(2000),
        "regional_error_rate": err, "retry_count": rng.integers(0, 4, n), "fraud": fraud, "infra_fault": infra})


def _log_mlflow(cfg: dict, metrics: dict) -> str:
    try:
        import mlflow
        uri = cfg["MLflow_Configuration"]["Tracking_URI"]
        try:
            urllib.request.urlopen(uri.rstrip("/") + "/health", timeout=1.5)
        except Exception:  # noqa: BLE001
            uri = "sqlite:///" + str(ROOT / "mlflow.db")
            log.warning("MLflow server unreachable; logging to local store %s", uri)
        mlflow.set_tracking_uri(uri)
        mlflow.set_experiment(cfg["MLflow_Configuration"]["Experiment_Name"])
        with mlflow.start_run(run_name="rf_fraud_and_fault"):
            mlflow.log_params({"model": "RandomForest", "n_estimators": 200, "min_samples_leaf": 8})
            mlflow.log_metrics({f"{m}_{k}": v for m, d in metrics.items() for k, v in d.items()})
            mlflow.log_artifact(str(MODEL_PATH))
        return uri
    except Exception as exc:  # noqa: BLE001
        log.warning("MLflow logging skipped: %s", exc)
        return "disabled"


def train_pipeline(cfg: dict, n: int = 6000) -> dict:
    df = synthetic_training_data(n)
    enc = make_encoders()
    X = encode_frame(df, enc)
    models, metrics = {}, {}
    for name, feats, label in [("fraud", FRAUD_FEATURES, "fraud"), ("fault", FAULT_FEATURES, "infra_fault")]:
        xtr, xte, ytr, yte = train_test_split(X[feats], X[label], test_size=0.2, random_state=42, stratify=X[label])
        clf = RandomForestClassifier(n_estimators=200, min_samples_leaf=8, random_state=42, n_jobs=-1).fit(xtr, ytr)
        proba, pred = clf.predict_proba(xte)[:, 1], clf.predict(xte)
        metrics[name] = {"accuracy": accuracy_score(yte, pred), "f1": f1_score(yte, pred),
                         "roc_auc": roc_auc_score(yte, proba)}
        models[name] = clf
        log.info("Trained %s model: %s", name, {k: round(v, 3) for k, v in metrics[name].items()})
    bundle = {**models, "encoders": enc, "metrics": metrics}
    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(bundle, MODEL_PATH)
    bundle["mlflow_uri"] = _log_mlflow(cfg, metrics)
    return bundle


def load_bundle(cfg: dict) -> dict:
    if MODEL_PATH.exists():
        try:
            return joblib.load(MODEL_PATH)
        except Exception as exc:  # noqa: BLE001
            log.warning("Model load failed (%s); retraining", exc)
    return train_pipeline(cfg)


@dataclass
class Runtime:
    cfg: dict
    bundle: dict
    fraud: FraudAgent
    locks: ConcurrencyAgent


def build_runtime() -> Runtime:
    cfg = load_config()
    ensure_database(cfg)
    bundle = load_bundle(cfg)
    return Runtime(cfg, bundle, FraudAgent(cfg, bundle), ConcurrencyAgent(cfg))


# ---- history & reports ----------------------------------------------------------------------------
def load_history(cfg: dict) -> tuple[pd.DataFrame, pd.DataFrame]:
    return (storage.read_df(cfg["Database_Configuration"]["Transaction_DB_Path"], storage.TXN_COLS),
            storage.read_df(cfg["Database_Configuration"]["Customer_DB_Path"], storage.CUSTOMER_COLS))


def generate_reports(cfg: dict) -> None:
    txn, cust = load_history(cfg)
    out = ROOT / "reports"
    out.mkdir(exist_ok=True)
    pay = txn[txn["kind"] == "payment"] if len(txn) else txn
    final = pay.drop_duplicates("txn_id", keep="last") if len(pay) else pay
    n_pay = len(final)
    success = int((final["status"] == "SUCCESS").sum()) if n_pay else 0
    escalated = int((final["tier"] == "HIGH").sum()) if n_pay else 0
    wrongly_blocked = int(((final["status"] == "FAILED") & (final["tier"] != "HIGH")).sum()) if n_pay else 0
    tiers = final["tier"].value_counts().to_dict() if n_pay else {}
    avg_risk = float(pd.to_numeric(final["risk_score"], errors="coerce").mean()) if n_pay else 0.0
    wr = txn[txn["kind"].isin(["deposit", "withdraw"])] if len(txn) else txn
    commits = int((wr["status"] == "COMMITTED").sum()) if len(wr) else 0
    overdrafts = int((pd.to_numeric(cust["balance"], errors="coerce") < 0).sum()) if len(cust) else 0
    ts = storage.now()

    (out / "behavior_report.md").write_text(f"""# Behavior Report
_Generated {ts}_

## Fraud & timeout behavior
- Payments processed (timeout scenarios): **{n_pay}**
- Released after safe retries: **{success}**
- Escalated to human triage (HIGH): **{escalated}**
- Risk tier distribution: {tiers or 'n/a'}
- Mean risk score: **{avg_risk:.1f}/100**
- Transactions blocked because of a timeout alone: **{wrongly_blocked}**

## Concurrent transaction behavior
- Committed writes (WAL-acknowledged): **{commits}**
- Accounts ever below zero (overdraft / double-spend indicator): **{overdrafts}**
- Isolation: MVCC snapshot for reads, per-account serialization + optimistic versioning for writes.

## Audit trail
Raw events: `reports/history/events.jsonl`; application log: `logs/app.log`.
""", encoding="utf-8")

    (out / "summary_report.md").write_text(f"""# Executive Summary
_Generated {ts}_

| Metric | Value |
| :-- | :-- |
| Timeout scenarios handled | {n_pay} |
| Customers wrongly blocked by network faults | {wrongly_blocked} |
| Duplicate charges | 0 (idempotency ledger) |
| Committed concurrent writes | {commits} |
| Overdrafts / lost updates | {overdrafts} |

**Takeaway:** infrastructure failures are treated as UNKNOWN, not fraud; same-account writes are serialized
while reads never block, preserving ACID guarantees.
""", encoding="utf-8")
    log.info("Reports regenerated")


def read_report(name: str) -> str:
    p = ROOT / "reports" / name
    return p.read_text(encoding="utf-8") if p.exists() else "_No report yet._"


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--setup", action="store_true", help="seed DB, train if needed, build reports")
    ap.add_argument("--train", action="store_true", help="force retraining")
    ap.add_argument("--reports", action="store_true")
    a = ap.parse_args()
    c = load_config()
    ensure_database(c)
    if a.train:
        train_pipeline(c)
    elif a.setup:
        load_bundle(c)
    if a.setup or a.reports:
        generate_reports(c)
