"""Fraud detection & timeout intervention.

Principle: a network timeout is UNKNOWN, never evidence of fraud. Infrastructure metrics (latency, regional
error rate) are quarantined from the behavioural fraud score and only used to decide whether the timeout is
*explained* by an outage. Retries reuse the same idempotency key so no duplicate charge can occur.
"""
from __future__ import annotations

import threading
import time
import uuid
from datetime import datetime

import numpy as np
import pandas as pd
from sklearn.preprocessing import LabelEncoder

from utils import storage
from utils.logger import get_logger

PROFILES = ["new", "returning"]
NETWORKS = ["outage", "stable"]
FRAUD_FEATURES = ["profile_enc", "amount", "hour", "device_match", "geo_match", "velocity_1h", "account_age_days"]
FAULT_FEATURES = ["network_enc", "latency_ms", "regional_error_rate", "retry_count"]  # infra only
TTL_SECONDS = 24 * 3600
MAX_RETRIES = 3


def make_encoders() -> dict:
    return {"profile": LabelEncoder().fit(PROFILES), "network": LabelEncoder().fit(NETWORKS)}


def encode_frame(df: pd.DataFrame, enc: dict) -> pd.DataFrame:
    out = df.copy()
    out["profile_enc"] = enc["profile"].transform(out["profile"])
    out["network_enc"] = enc["network"].transform(out["network"])
    return out


def tier_for(risk: int) -> tuple[str, str]:
    if risk < 40:
        return "LOW", "Auto-approve"
    if risk < 70:
        return "MEDIUM", "OOB verify"
    return "HIGH", "Human triage"


def scenario_features(profile: str, network: str, rng) -> dict:
    returning = profile == "returning"
    outage = network == "outage"
    return {
        "profile": profile, "network": network,
        # behaviour is independent of the network on purpose
        "amount": 120.0 if returning else 400.0,
        "hour": 14 if returning else 2,
        "device_match": 1, "geo_match": 1,
        "velocity_1h": 1 if returning else 2,
        "account_age_days": 900 if returning else 3,
        # infrastructure context for the timed-out request
        "latency_ms": float(rng.normal(3500, 150)),
        "regional_error_rate": float(rng.uniform(0.25, 0.5) if outage else rng.uniform(0.0, 0.03)),
        "retry_count": 0,
    }


class FraudAgent:
    def __init__(self, cfg: dict, bundle: dict):
        self.cfg, self.bundle = cfg, bundle
        db = cfg["Database_Configuration"]
        self.txn_path, self.cust_path = db["Transaction_DB_Path"], db["Customer_DB_Path"]
        self.log = get_logger("fraud_agent")
        self._ledger_lock = threading.Lock()
        self.context_cache: dict[str, float] = {}  # idempotency key -> expiry epoch
        self.rng = np.random.default_rng()

    # ---- scoring -----------------------------------------------------------------------------------
    def score(self, profile: str, network: str) -> dict:
        f = scenario_features(profile, network, self.rng)
        df = encode_frame(pd.DataFrame([f]), self.bundle["encoders"])
        p_fraud = float(self.bundle["fraud"].predict_proba(df[FRAUD_FEATURES])[0, 1])
        p_infra = float(self.bundle["fault"].predict_proba(df[FAULT_FEATURES])[0, 1])
        # an unexplained timeout is a weak signal; an outage-explained timeout is neutral
        weight = 35 if profile == "new" else 10
        penalty = round(weight * (1 - p_infra))
        risk = int(min(100, round(100 * p_fraud + penalty)))
        self.log.info("ML prediction profile=%s network=%s p_fraud=%.3f p_infra=%.3f penalty=%d risk=%d",
                      profile, network, p_fraud, p_infra, penalty, risk)
        return {"risk": risk, "p_fraud": p_fraud, "p_infra": p_infra, "penalty": penalty}

    # ---- idempotent commit -------------------------------------------------------------------------
    def commit_once(self, txn: dict) -> bool:
        with self._ledger_lock:
            df = storage.read_df(self.txn_path, storage.TXN_COLS)
            if len(df) and ((df["idempotency_key"] == txn["idempotency_key"]) & (df["status"] == "SUCCESS")).any():
                return False
            storage.append_row(self.txn_path, {**txn, "status": "SUCCESS"}, storage.TXN_COLS)
            return True

    # ---- optional LLM rationale --------------------------------------------------------------------
    def explain(self, ctx: dict) -> tuple[str, bool]:
        llm = self.cfg.get("LLM_Configuration", {})
        key = llm.get("API_Key", "")
        fallback = (f"Timeout explained by regional {ctx['network']} (P(infra)={ctx['p_infra']:.2f}); behavioural "
                    f"risk {ctx['risk']}/100 → {ctx['action']}.")
        if not key or key.startswith("your_") or "your-llm-provider" in llm.get("Base_URL", ""):
            return fallback, False
        try:
            from openai import OpenAI
            client = OpenAI(api_key=key, base_url=llm["Base_URL"], timeout=8)
            r = client.chat.completions.create(
                model=llm["Model_Name"], max_tokens=90,
                messages=[{"role": "system", "content": "You are a fintech fraud triage analyst. One short sentence. "
                           "Never treat network timeouts as fraud."},
                          {"role": "user", "content": str(ctx)}])
            return r.choices[0].message.content.strip(), True
        except Exception as exc:  # noqa: BLE001
            self.log.warning("LLM call failed, using template rationale: %s", exc)
            return fallback, False

    # ---- the lifecycle -----------------------------------------------------------------------------
    def run_timeout_scenario(self, profile: str, network: str, amount: float = 250.0) -> dict:
        t0 = time.time()
        logs: list[dict] = []

        def L(level: str, msg: str):
            logs.append({"ts": datetime.now().strftime("%I:%M:%S %p"), "level": level, "msg": msg})
            self.log.info("[%s] %s", level, msg)

        txn_id = f"txn_{int(self.rng.integers(1000, 9999))}"
        cust_id = "cust_4471" if profile == "returning" else f"cust_new_{int(self.rng.integers(100, 999))}"
        key = "idem_" + "-".join(uuid.uuid4().hex[:4] for _ in range(3))
        base = {"txn_id": txn_id, "customer_id": cust_id, "account_id": f"account_{cust_id[-4:]}", "kind": "payment",
                "amount": amount, "idempotency_key": key, "network": network, "lock_state": "none"}

        storage.append_row(self.txn_path, {**base, "status": "INITIATED"}, storage.TXN_COLS)
        L("info", f"{txn_id} INITIATED with idempotency key {key}.")
        L("warn", "API gateway: no ACK within 3000ms → network timeout.")
        storage.append_row(self.txn_path, {**base, "status": "PENDING", "note": "timeout=UNKNOWN"}, storage.TXN_COLS)
        self.context_cache[key] = time.time() + TTL_SECONDS
        L("ok", "Timeout = UNKNOWN. Transaction held PENDING — user NOT auto-blocked.")

        L("info", "Context engine: device fingerprint, geo, amount, time-of-day, history…")
        s = self.score(profile, network)
        tier, action = tier_for(s["risk"])
        L("risk" if tier == "HIGH" else "ok", f"Risk score {s['risk']}/100 → {tier} risk.")
        L("info", f"Infrastructure metrics quarantined from the score. Fault classifier P(infra)={s['p_infra']:.2f}.")

        retries = 0
        for i in range(1, MAX_RETRIES + 1):
            L("info", f"Safe retry {i}/{MAX_RETRIES} using SAME idempotency key…")
            retries = i
            if i < MAX_RETRIES:
                L("warn", f"Retry {i} timed out again. No duplicate created.")

        explanation, llm_used = self.explain({**s, "network": network, "profile": profile, "action": action})
        L("info", f"Agent rationale: {explanation}")

        row = {**base, "risk_score": s["risk"], "tier": tier}
        if tier == "HIGH":
            state, ok = "FAILED", False
            storage.append_row(self.txn_path, {**row, "status": "FAILED", "note": "escalated: human triage"},
                               storage.TXN_COLS)
            L("risk", "Escalated to human agent + compliance. Only this transaction is frozen; account stays open.")
            msg = (f"Transaction FAILED — escalated to human triage. Only this transaction is frozen — the account "
                   f"stays open. Risk score {s['risk']}/100.")
        else:
            if tier == "MEDIUM":
                L("info", "Out-of-band verification sent to the customer's registered device… verified.")
            committed = self.commit_once({**row, "note": "oob_verified" if tier == "MEDIUM" else "auto_approved"})
            replay = self.commit_once({**row})
            L("ok", f"Committed once (new={committed}). Replay of same key rejected by ledger (duplicate-safe={not replay}).")
            self.context_cache.pop(key, None)
            state, ok = "SUCCESS", True
            msg = (f"Transaction SUCCESS — released. Idempotency key {key} committed once. No duplicate charge. "
                   f"Context cache cleared after reconciliation.")

        storage.append_history({"agent": "fraud", "txn_id": txn_id, "profile": profile, "network": network,
                                "risk": s["risk"], "tier": tier, "state": state, "llm_used": llm_used})
        remaining = TTL_SECONDS - int(time.time() - t0) if ok else max(0, int(self.context_cache[key] - time.time()))
        return {"txn_id": txn_id, "idem_key": key, "state": state, "progress": 100, "risk": s["risk"], "tier": tier,
                "action": action, "retries": retries, "max_retries": MAX_RETRIES, "ttl_remaining": remaining,
                "message": msg, "ok": ok, "logs": logs, "p_fraud": s["p_fraud"], "p_infra": s["p_infra"],
                "explanation": explanation, "llm_used": llm_used, "profile": profile, "network": network}
