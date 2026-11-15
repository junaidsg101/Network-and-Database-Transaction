# AI Agentic Fintech: Fraud Detection & Concurrent Transaction System
## Project Baseline: Network and Database Transaction
Leverages ML Ops, multi-agent AI and distributed-database principles to solve two fintech problems:
1. **Fraud detection & network timeouts** — prevent "discrimination laundering": infrastructure failures are never treated as user fraud.
2. **Concurrent transactions** — Read+Write (MVCC snapshot) and Write+Write (serialized) without blocking or breaking ACID.

## Technology stack
| Category | Technology | Purpose |
| :-- | :-- | :-- |
| Core | Python 3.10+ | Application logic and agent orchestration |
| Data | Pandas, NumPy | Cleaning, transformation, statistics |
| Visualization | Plotly, Matplotlib | Pie, bar, line, histogram, gauge, trace timeline |
| ML | Scikit-learn | Random Forest fraud + fault classifiers with label encoding |
| MLOps | MLflow, Joblib | Tracking and model serialization (falls back to local SQLite store) |
| LLM | OpenAI-compatible (OpenAI / Groq / other) | Agent rationale via custom Base URL + API key (template fallback if unset) |
| UI | Streamlit | Interactive UI (container-deployable; see Deployment) |
| Config | TOML | API keys, paths, MLflow settings |
| Logging | `logging` | Rotating audit trail in `logs/app.log` |

## Project structure
```text
├── UI.py                      # UI only (Streamlit + Plotly/Matplotlib)
├── main.py                    # ML Ops: config, data bootstrap, training, model loading, reports
├── deploy.py                  # Optional helper (check / launch / docker)
├── agentic/
│   ├── agentic_fraud.py       # Fraud detection & timeout intervention (idempotent retries, risk tiers)
│   └── agentic_exclusive.py   # Concurrent transactions & exclusion locks (MVCC, serialization, WAL)
├── database/                  # All writes use append ("a") mode
│   ├── customers.csv
│   ├── transactions.csv
│   └── online.txt             # optional URL of an alternative customers CSV used to seed the DB
├── reports/
│   ├── history/events.jsonl   # raw behavior history
│   ├── behavior_report.md
│   └── summary_report.md
├── utils/{__init__,logger,storage}.py
├── secrets.toml · requirements.txt · README.md
```

## Secrets (`secrets.toml`)
```toml
[LLM_Configuration]
API_Key = "your_actual_api_key_here"
Base_URL = "https://api.your-llm-provider.com/v1"
Model_Name = "llama" # or

[Database_Configuration]
Customer_DB_Path = "database/customers.csv"
Transaction_DB_Path = "database/transactions.csv"

[MLflow_Configuration]
Tracking_URI = "http://localhost:"
Experiment_Name = "fintech_fraud_triage"
```
Env vars `LLM_API_KEY`, `LLM_BASE_URL`, `LLM_MODEL` override the file (use these in production).

## Run & deploy
Packages are used from your existing Python environment (no virtualenv). Install once if needed: `pip install -r requirements.txt`.
```bash
streamlit run UI.py               # or simply:  python UI.py   -> opens http://localhost:
```
On first launch the app seeds `database/`, trains the models and writes the reports automatically.

Optional helper:
```bash
python deploy.py                  # seed, train, smoke-test, launch
python deploy.py --mlflow         # + MLflow server on :5000
python deploy.py --check          # verify only
python deploy.py --target docker  # build + run container (deploy to Render/Railway/Fly/Cloud Run)
```
**Vercel:** Vercel's serverless runtime can't host a long-running Streamlit server. Use the Docker image on a container host or Streamlit Community Cloud.

## How it works
- **Risk tiers:** < 40 auto-approve · 40–69 out-of-band verify · ≥ 70 human triage.
- **Quarantine:** behavioural model scores risk; infrastructure metrics only feed the fault classifier that decides whether a timeout is explained by an outage.
- **Idempotency:** retries reuse one key; the ledger rejects duplicate commits.
- **Locks:** readers use lock-free committed snapshots; same-account writers take a per-account micro-lock with optimistic version checks; commits are fsync'd before acknowledgement.
- **Training data:** the bundled model trains on synthetic bootstrap data — retrain on real labelled history before production use.
