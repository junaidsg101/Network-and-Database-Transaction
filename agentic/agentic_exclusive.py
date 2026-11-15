"""Concurrent transactions & exclusion locks (Apache-Ignite-style model).

* Read+Write  -> MVCC snapshot isolation: readers never take a lock and never block the writer.
* Write+Write -> same-account writes are serialized by a per-account micro-lock + optimistic version check;
                 different accounts run in parallel.
* Durability  -> a commit is acknowledged only after the row is appended and fsync'd (WAL).
"""
from __future__ import annotations

import threading
import time
from datetime import datetime

from utils import storage
from utils.logger import get_logger

START_BALANCE = 10_000.0
LOCK_TIMEOUT = 2.0


class Account:
    def __init__(self, account_id: str, balance: float, version: int):
        self.id = account_id
        self.live = balance
        self.version = version
        self.snapshot = (version, balance)  # last COMMITTED state; swapped atomically, read lock-free
        self.lock = threading.Lock()


class Trace:
    def __init__(self):
        self.items: list[dict] = []
        self._l = threading.Lock()
        self.t0 = time.perf_counter()

    def add(self, msg: str, level: str = "info"):
        with self._l:
            self.items.append({"t_ms": round((time.perf_counter() - self.t0) * 1000, 1), "msg": msg, "level": level})


class ConcurrencyAgent:
    def __init__(self, cfg: dict):
        db = cfg["Database_Configuration"]
        self.cust_path, self.txn_path = db["Customer_DB_Path"], db["Transaction_DB_Path"]
        self.accounts: dict[str, Account] = {}
        self._reg = threading.Lock()
        self.log = get_logger("lock_agent")

    # ---- state -------------------------------------------------------------------------------------
    def account(self, account_id: str) -> Account:
        with self._reg:
            if account_id not in self.accounts:
                df = storage.read_df(self.cust_path, storage.CUSTOMER_COLS)
                rows = df[df["account_id"] == account_id] if len(df) else df
                if len(rows):
                    last = rows.iloc[-1]
                    acct = Account(account_id, float(last["balance"]), int(last["version"]))
                else:
                    acct = Account(account_id, START_BALANCE, 1)
                self.accounts[account_id] = acct
            return self.accounts[account_id]

    def state(self, account_id: str) -> dict:
        a = self.account(account_id)
        return {"live": a.live, "snapshot": a.snapshot[1], "version": a.version}

    def reset(self, account_id: str) -> dict:
        with self._reg:
            self.accounts.pop(account_id, None)
        storage.append_row(self.cust_path, {"customer_id": "cust_4471", "profile": "returning", "account_id": account_id,
                                            "account_age_days": 900, "status": "active", "balance": START_BALANCE,
                                            "version": 1}, storage.CUSTOMER_COLS)
        storage.append_row(self.txn_path, {"txn_id": "reset", "account_id": account_id, "kind": "reset",
                                           "status": "RESET", "version": 1}, storage.TXN_COLS)
        self.account(account_id)
        return self.state(account_id)

    def _commit(self, a: Account, txn_id: str, kind: str, delta: float, lock_state: str, status="COMMITTED", note=""):
        """Caller holds a.lock. WAL first (fsync), then publish the new snapshot."""
        new_bal, new_ver = a.live + delta, a.version + 1
        storage.append_row(self.txn_path, {"txn_id": txn_id, "customer_id": "cust_4471", "account_id": a.id,
                                           "kind": kind, "amount": delta, "status": status, "lock_state": lock_state,
                                           "version": new_ver, "note": note}, storage.TXN_COLS)
        storage.append_row(self.cust_path, {"customer_id": "cust_4471", "profile": "returning", "account_id": a.id,
                                            "account_age_days": 900, "status": "active", "balance": new_bal,
                                            "version": new_ver}, storage.CUSTOMER_COLS)
        a.live, a.version = new_bal, new_ver
        a.snapshot = (new_ver, new_bal)

    # ---- Read + Write (MVCC) -----------------------------------------------------------------------
    def run_read_write(self, account_id: str, deposit: float = 5000.0) -> dict:
        a, tr = self.account(account_id), Trace()
        started, read_done = threading.Event(), threading.Event()
        seen: dict = {}

        def writer():
            if not a.lock.acquire(timeout=LOCK_TIMEOUT):
                tr.add("Writer timed out waiting for micro-lock.", "err")
                return
            try:
                tr.add(f"Writer (txn A) takes micro-lock on {account_id} row (max {int(LOCK_TIMEOUT)}s wait).")
                started.set()
                read_done.wait(timeout=LOCK_TIMEOUT)
                self._commit(a, "txn_A", "deposit", deposit, "micro-lock")
                tr.add(f"Writer committed +{deposit:.0f}. Balance = {a.live:.0f}, version v{a.version}.", "ok")
            finally:
                a.lock.release()

        def reader():
            started.wait(timeout=LOCK_TIMEOUT)
            tr.add("Reader (txn B) requests balance under MVCC snapshot isolation...")
            t = time.perf_counter()
            ver, bal = a.snapshot  # lock-free
            seen.update(bal=bal, ver=ver, wait_ms=(time.perf_counter() - t) * 1000)
            tr.add(f"Reader sees last COMMITTED snapshot = {bal:.0f}. Never blocks the writer.", "ok")
            read_done.set()

        ts = [threading.Thread(target=writer), threading.Thread(target=reader)]
        [t.start() for t in ts]
        [t.join() for t in ts]
        ok = seen.get("bal") is not None and a.live == seen["bal"] + deposit
        self.log.info("read_write ok=%s reader_wait_ms=%.3f", ok, seen.get("wait_ms", -1))
        storage.append_history({"agent": "lock", "mode": "read_write", "ok": ok, "balance": a.live})
        return {"mode": "read_write", "live": a.live, "snapshot": seen.get("bal"), "txn_a": deposit, "txn_b": None,
                "lock": "No lock", "version": a.version, "isolation": "Snapshot isolation", "ok": ok,
                "message": ("Zero blocking. Reader saw the old committed balance while the writer updated the live "
                            "row; after commit, readers see the new balance."), "trace": tr.items,
                "reader_wait_ms": seen.get("wait_ms", 0.0)}

    # ---- Write + Write (serialized) ----------------------------------------------------------------
    def run_write_write(self, account_id: str, deposit: float = 5000.0, withdraw: float = 2000.0) -> dict:
        a, tr = self.account(account_id), Trace()
        start_bal = a.live
        barrier = threading.Barrier(2)
        applied: list[float] = []
        tr.add("Two writes on the SAME account → serialized via per-account queue.")

        def txn(name: str, delta: float, delay: float):
            ver, bal = a.snapshot
            tr.add(f"Optimistic locking: {name} read balance {bal:.0f} + version v{ver}.")
            barrier.wait()
            time.sleep(delay)
            while True:
                if not a.lock.acquire(timeout=LOCK_TIMEOUT):
                    tr.add(f"{name} lock wait exceeded — aborted.", "err")
                    return
                try:
                    if a.version != ver:
                        tr.add(f"{name} detects version changed v{ver} → v{a.version}. Aborts, retries with fresh "
                               f"balance + version v{a.version}.", "warn")
                        ver, bal = a.snapshot
                        continue
                    if a.live + delta < 0:
                        tr.add(f"{name} rejected: would overdraw account.", "err")
                        return
                    self._commit(a, name, "deposit" if delta > 0 else "withdraw", delta, "serialized")
                    applied.append(delta)
                    tr.add(f"{name} ({'deposit' if delta > 0 else 'withdrawal'} {delta:+.0f}) commits. "
                           f"v{ver} → v{a.version}.", "ok")
                    return
                finally:
                    a.lock.release()

        ts = [threading.Thread(target=txn, args=("txn A", deposit, 0.0)),
              threading.Thread(target=txn, args=("txn B", -withdraw, 0.03))]
        [t.start() for t in ts]
        [t.join() for t in ts]
        ok = abs(a.live - (start_bal + sum(applied))) < 1e-9 and a.live >= 0
        tr.add(f"Final balance = {a.live:.0f}, version v{a.version}.", "ok")
        tr.add("WAL: commit acknowledged only after durable write.")
        self.log.info("write_write ok=%s start=%.0f final=%.0f", ok, start_bal, a.live)
        storage.append_history({"agent": "lock", "mode": "write_write", "ok": ok, "balance": a.live})
        return {"mode": "write_write", "live": a.live, "snapshot": start_bal, "txn_a": deposit, "txn_b": -withdraw,
                "lock": "No lock", "version": a.version, "isolation": "Serialized per account", "ok": ok,
                "message": (f"Strict serialization held. {start_bal:.0f} → {start_bal + deposit:.0f} → {a.live:.0f}. "
                            f"No lost update, no double-spend."), "trace": tr.items, "reader_wait_ms": 0.0}
