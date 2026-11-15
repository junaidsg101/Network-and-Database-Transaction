
import argparse
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PY = sys.executable
IMAGE = "fintech-agent"

DOCKERFILE = """FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN python main.py --setup
EXPOSE 8501
CMD ["streamlit", "run", "UI.py", "--server.port=8501", "--server.address=0.0.0.0", "--server.headless=true"]
"""


def run(cmd, **kw):
    print("→", " ".join(map(str, cmd)))
    subprocess.run(cmd, check=True, cwd=ROOT, **kw)


def step(msg):
    print(f"\n=== {msg} ===")


def preflight(install):
    step("Environment")
    if sys.version_info < (3, 10):
        sys.exit("Python 3.10+ is required.")
    if install:
        run([PY, "-m", "pip", "install", "-q", "-r", "requirements.txt"])
    missing = []
    for mod in ("streamlit", "pandas", "numpy", "plotly", "matplotlib", "sklearn", "joblib"):
        try:
            __import__(mod)
        except ImportError:
            missing.append(mod)
    if missing:
        sys.exit(f"Missing packages: {', '.join(missing)}. Run: python deploy.py --install")
    print("Using", PY)


def bootstrap():
    step("Seed database, train models, build reports")
    run([PY, "main.py", "--setup"])


def check():
    step("Smoke test")
    code = ("import main; rt = main.build_runtime(); r = rt.fraud.run_timeout_scenario('new','stable'); "
            "w = rt.locks.run_write_write('account_4471'); rt.locks.reset('account_4471'); "
            "assert r['tier']=='HIGH' and w['ok'], 'smoke test failed'; print('OK: agents + models healthy')")
    run([PY, "-c", code])


def launch(port, with_mlflow):
    if with_mlflow:
        step("MLflow server on :5000")
        subprocess.Popen([PY, "-m", "mlflow", "server", "--host", "127.0.0.1", "--port", "5000",
                          "--backend-store-uri", f"sqlite:///{ROOT / 'mlflow.db'}"], cwd=ROOT)
    step(f"Launching UI on http://localhost:{port}")
    run([PY, "-m", "streamlit", "run", "UI.py", "--server.port", str(port), "--server.address", "localhost"])


def docker(port):
    step("Docker build & run")
    (ROOT / "Dockerfile").write_text(DOCKERFILE, encoding="utf-8")
    (ROOT / ".dockerignore").write_text(".venv\nsecrets.toml\nlogs\nmlruns\nmlflow.db\n__pycache__\n", encoding="utf-8")
    run(["docker", "build", "-t", IMAGE, "."])
    cmd = ["docker", "run", "--rm", "-p", f"{port}:8501"]
    for var in ("LLM_API_KEY", "LLM_BASE_URL", "LLM_MODEL"):
        if os.getenv(var):
            cmd += ["-e", var]
    run(cmd + [IMAGE])


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--target", choices=["local", "docker"], default="local")
    ap.add_argument("--port", type=int, default=8501)
    ap.add_argument("--install", action="store_true")
    ap.add_argument("--mlflow", action="store_true")
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    if a.target == "docker":
        docker(a.port)
    else:
        preflight(a.install)
        bootstrap()
        check()
        if not a.check:
            launch(a.port, a.mlflow)
