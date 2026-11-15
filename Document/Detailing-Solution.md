# Agentic FinTech: Fraud Detection & Concurrent Transactions

## 1. Core Idea & Purpose
- Two problems share one root cause: **hasty wrong decisions under uncertainty**
- Solution: **AI agents** that observe, assess risk, act, and log every step
- Two core values:
  - Innocent users must not be punished for network failures
  - Zero compromise on money accuracy

## 2. Problem 1: Network Timeouts & "Discrimination Laundering"
- **Timeout = Unknown**, not failure and not fraud
- Many systems auto-block on timeout, which hits weak-infrastructure regions hardest
- This is **discrimination laundering**: unfair outcomes disguised as technical decisions
- Fix: **separate infrastructure data** (latency, regional fault rate, retries) from the **fraud score**
- Fraud score uses behavior only: amount, time, device, location, account age

## 3. Problem 2: Concurrent Transactions & Locking
- Risks: **lost updates**, **double spending**, wrong balances
- Locking the whole database is too slow
- **MVCC (snapshot reads)**: readers never wait and never block writers
- **Per-account queue and lock**: same-account writers run in order, different accounts run in parallel
- Same principle as **Apache Ignite**
- **ACID** guarantees: atomicity, consistency, isolation, durability
- Goal: no double spending, no negative balances from race conditions

## 4. Agentic Approach
- Agent = goal, observation, decision, action, logging
- Two current agents: **Fraud Agent** and **Concurrency Agent**
- Separate files in the "agentic" folder, so new agents can be added easily
- Decisions use ML models, policy, and an optional **LLM**
- **No irreversible money decision alone**: high risk goes to a human

## 5. Fraud Agent Workflow
- Assigns a **transaction ID** and an **idempotency key** to prevent duplicate charges
- On timeout, the transaction is set to **pending/unknown**, the user is **not blocked**, and context is saved for **24 hours (86,400 s)**
- Two models:
  - **Behavior model**: fraud probability
  - **Fault classifier**: probability that the timeout was a regional fault
- Regional fault likely: timeout treated as neutral
- No explanation for the timeout: small penalty, higher for new users and lower for old users
- Final **risk score (0–100)**:
  - **Below 40**: low risk, auto-approve
  - **40–69**: medium risk, step-up verification (e.g., code to registered device)
  - **70 and above**: high risk, human review and compliance
- High risk freezes **only that transaction**, not the account
- **3 safe retries** with the same key and **no duplicates**
- Approval completes **once**; the idempotency check runs first and context is cleared afterward
- Decision reason comes from the LLM or a fallback **template**

## 6. Concurrency Agent Workflow
- Per account: **balance, version number, snapshot**
- **Read + write**: the writer takes a short row lock (2 s timeout), the reader gets the snapshot instantly, and the new snapshot is published after the disk write
- **Two writers**:
  - The first writer commits and the version increases
  - The second detects a **stale version**, aborts, re-reads, and retries
  - No lost updates
- Overdrafts are rejected
- **WAL (write-ahead logging)**: confirm only after the data reaches disk
- Post-check: **final balance = initial balance + applied changes**, and the balance is not negative
- The UI shows an **ACID preserved** message and a **reset** button

## 7. ML & MLOps
- Two **Random Forest** models: fraud behavior and network fault
- **Label encoding** for categorical features
- Trained on **synthetic data**:
  - Fraud model: ~83% accuracy, AUC ~0.87
  - Fault model: ~96% accuracy, AUC ~0.96
- Retraining on real labeled data is required before real use
- **Joblib** saves the models; **MLflow** tracks parameters, metrics, and files
- If MLflow is unavailable, it falls back to a local **SQLite** store
- **main.py** orchestrates config, data, training, loading, and reports

## 8. Database & Audit
- **CSV files**: customers and transactions
- **Append-only** writes: history is never edited, and the latest line is the current state
- Forced disk flush after every write
- A **history file** records raw behavior and agent decisions
- Optional online customer file as a data source

## 9. User Interface (Streamlit)
- Single file, display only, with no business logic
- Auto-creates the database, models, and reports on first run
- **Tab 1**: choose customer type and network state, view the 3-stage timeline, risk score, retries, idempotency key, gauge, and agent log
- **Tab 2**: balance cards, scenario selection, step-by-step trace, timeline
- **Tab 3**: aggregate stats, **Plotly** charts (pie, histogram, bar), balance history, both reports

## 10. Logging, Reports & Audit
- **Rotating log files** with a size limit and limited backups
- Logs agent decisions, ML predictions, errors, and warnings
- **Behavior report**: timeouts handled, approvals, human reviews, average risk, and **wrongly blocked users due to network only (must be 0)**
- **Concurrency report**: confirmed changes and negative-balance count
- **Summary report**: a short table for management

## 11. Configuration & Security
- **TOML** config file: LLM key, server URL, model name, DB paths, MLflow URI and experiment name
- Works with any **OpenAI-compatible provider** (OpenAI, Grok, etc.)
- Never publish real keys
- **Environment variables** override config keys
- The app still runs without a key, using **template reasons**

## 12. Running & Deployment
- **Local**: run the Streamlit UI file or run it with Python; no virtual environment needed
- A **deployment script** installs packages, trains models, runs a smoke test, and can start MLflow
- **Docker**: deploys to Render, Railway, Fly.io, or Google Cloud Run
- **Streamlit Community Cloud** is an easy alternative
- **Not for Vercel**: it needs a persistent server
- Use environment variables for keys, run **a single instance**, and add persistent storage

## 13. Proposed Additional Agents (design suggestions only)
- **Supervisor/Coordinator**: routes events, enforces policy, escalates to humans
- **Reconciliation Agent**: matches 24-hour pending transactions against bank records and completes or cancels them
- **Customer Communication Agent**: blame-free updates ("your money is safe, don't pay again") and verification messages
- **Human Review Assistant**: summarizes cases and shows evidence; the human decides
- **Fairness & Compliance Agent**: monitors for regional or network-based bias, raises alarms, and generates reports
- **Model Monitoring Agent**: detects drift and performance drops, and triggers retraining that needs human approval
- **Lock Performance Agent**: finds contended accounts and deadlocks, and tunes timeouts and queues
- **Chaos/Testing Agent**: injects outages and bursts of hundreds of transactions to stress-test the system
- **Safety rules**: money movement only by explicitly authorized agents, limited permissions, **idempotent** actions, full logging, and a human in the loop for risk, money, or uncertainty

## 14. End-to-End Example
- **Fraud flow**:
  - A new user on a healthy network gets a timeout and the transaction is set to pending with context saved
  - The behavior model gives medium risk, and the fault model finds no regional fault
  - The penalty pushes the score to 80 or above, so after 3 retries the one transaction is frozen and sent to a human
  - The account stays open, and everything is logged and counted in the next report
- **Concurrency flow**:
  - A deposit and a withdrawal run at the same time and are queued
  - The deposit moves the balance from version 1 to 2
  - The withdrawal sees its data is stale, aborts, re-reads, and finishes at version 3
  - Readers never wait, and the system confirms **ACID preserved**

## 15. Limitations & Cautions
- Models trained on **synthetic data** are for demonstration only
- Real use needs retraining, validation, and **fairness testing**
- **External verification is simulated** and must be connected to real messaging
- A high-risk flag means **hold for review**, not proven fraud
- **CSV storage** suits a single machine or instance; scale needs **PostgreSQL** or **Apache Ignite**
- It is an educational prototype; real use needs a security review, legal compliance, payment standards, access controls, and full testing

## 16. Future Path & Conclusion
- **Strength**: modular design, where each agent, model, and data part is independent
- **Roadmap**:
  - Move to a robust database
  - Retrain on real data
  - Add Reconciliation, Fairness, and Monitoring agents
  - Add a Supervisor agent to coordinate everything
- **Core message**:
  - When uncertain, don't punish: wait safely, retry, and involve a human
  - Under concurrency, never trade accuracy for speed