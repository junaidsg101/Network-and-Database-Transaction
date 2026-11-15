"""Streamlit UI — presentation only. All logic lives in main.py and agentic/.

Run:  streamlit run UI.py     or     python UI.py
"""
import html
import io
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from streamlit.runtime import exists as _streamlit_running

# `python UI.py` -> relaunch itself through Streamlit (same as `streamlit run UI.py`)
if __name__ == "__main__" and not _streamlit_running():
    from streamlit.web import cli as _stcli
    sys.argv = ["streamlit", "run", str(Path(__file__).resolve()), "--server.address", "localhost", *sys.argv[1:]]
    sys.exit(_stcli.main())

import main  # noqa: E402  (first run seeds the DB and trains the models automatically)

ACCOUNT = "account_4471"
TEAL, TEAL_D, GREEN, AMBER, RED, INK, MUTED, LINE = "#0f766e", "#0b5f58", "#15803d", "#b45309", "#be123c", "#16323a", "#52696e", "#d3e1e3"
TIER_COLOR = {"LOW": GREEN, "MEDIUM": AMBER, "HIGH": RED}

st.set_page_config(page_title="Fintech Agent Console", page_icon="🛡️", layout="wide", initial_sidebar_state="collapsed")

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Newsreader:wght@500;600&display=swap');
.stApp { background:#eef4f5; color:{INK}; }
.stApp p, .stApp label, .stApp span, .stApp li { color:{INK}; }
[data-testid="stAppDeployButton"], .stAppDeployButton { display:none; }
[data-testid="stHeader"] { background:rgba(238,244,245,.9); }
.block-container { max-width:1320px; padding:3.4rem 2rem 3rem; }
h1,h2,h3,.serif { font-family:'Newsreader',Georgia,serif !important; color:{INK}; }

/* tabs */
[data-testid="stTab"] { padding:.55rem 1.2rem; }
[data-testid="stTab"] p { font-size:1.05rem; }
[data-testid="stTab"][aria-selected="true"] p { color:{TEAL}; font-weight:600; }
[data-testid="stTab"] .react-aria-SelectionIndicator, [data-baseweb="tab-highlight"] { background-color:{TEAL} !important; height:3px; }

/* buttons */
[data-testid="stBaseButton-primary"], [data-testid="stBaseButton-secondary"] { min-height:3rem; font-size:1rem; border-radius:10px; }
[data-testid="stBaseButton-primary"] { background:{TEAL}; border-color:{TEAL}; font-weight:600; }
[data-testid="stBaseButton-primary"]:hover { background:{TEAL_D}; border-color:{TEAL_D}; }
[data-testid="stBaseButton-primary"], [data-testid="stBaseButton-primary"] * { color:#fff !important; }
[data-testid="stBaseButton-secondary"] { background:#fff; border-color:{LINE}; }
[data-testid="stBaseButton-secondary"]:hover { border-color:{TEAL}; color:{TEAL}; }

/* segmented controls */
button[data-variant="segmented_control"] { min-height:2.7rem; padding:0 1.4rem; background:#fff; border:1px solid {LINE}; }
button[data-variant="segmented_control"] p { font-size:1rem; }
button[data-variant="segmented_control"][aria-checked="true"] { background:{TEAL} !important; border-color:{TEAL} !important; }
button[data-variant="segmented_control"][aria-checked="true"] p, button[data-variant="segmented_control"][aria-checked="true"] * { color:#fff !important; font-weight:600; }
button[data-variant="segmented_control"][aria-checked="false"]:hover { border-color:{TEAL}; }

/* cards */
.card { background:#fff; border:1px solid {LINE}; border-radius:14px; padding:16px 20px; margin:0 0 14px; }
.card.slim { padding:12px 20px; margin:6px 0 12px; }
.card h4 { margin:0 0 6px; font-family:'Newsreader',Georgia,serif; font-size:1.3rem; color:{INK}; }
.hero { background:linear-gradient(135deg,#0f766e 0%,#115e59 100%); border-radius:14px; padding:14px 22px; margin-bottom:4px; display:flex; align-items:center; justify-content:space-between; gap:18px; flex-wrap:wrap; }
.stApp .hero h1, .stApp .hero h1 * { color:#fff !important; margin:0; padding:0 !important; font-size:1.55rem; line-height:1.25; }
.hero p { color:#d5f0ec !important; margin:2px 0 0; font-size:.92rem; }
.pill { display:inline-block; font-size:.78rem; padding:3px 11px; border-radius:99px; margin-left:6px; background:rgba(255,255,255,.16); color:#fff !important; }
.sub { color:{MUTED}; font-size:.92rem; line-height:1.5; }
.step-h { font-family:'Newsreader',Georgia,serif; font-size:1.15rem; font-weight:600; margin:0 0 6px; color:{INK}; }
.num { display:inline-grid; place-items:center; width:24px; height:24px; border-radius:50%; background:{TEAL}; color:#fff !important; font-size:.8rem; margin-right:8px; font-family:sans-serif; }
.badge { float:right; font-size:.78rem; border:1px solid {LINE}; border-radius:99px; padding:3px 12px; color:{MUTED}; }
.badge.pending { color:{AMBER}; border-color:#f3d9a4; background:#fffaf0; }
.badge.success { color:{GREEN}; border-color:#b8e6c8; background:#f0fdf4; }
.badge.failed { color:{RED}; border-color:#f6b8c6; background:#fff1f4; }
.steps { display:flex; align-items:center; gap:12px; margin:8px 0 0; }
.dot { width:30px; height:30px; border-radius:50%; display:grid; place-items:center; font-size:.9rem; background:#e3ecee; color:{MUTED} !important; flex:none; }
.dot.on { background:{TEAL}; color:#fff !important; } .dot.done { background:#c7f0e6; color:{TEAL} !important; }
.dot.ok { background:{GREEN}; color:#fff !important; } .dot.fail { background:{RED}; color:#fff !important; }
.slabel { font-size:.95rem; color:{INK}; font-weight:500; white-space:nowrap; }
.line { flex:1; height:2px; background:{LINE}; border-radius:2px; } .line.done { background:{TEAL}; }
.chip { display:inline-block; font-size:.85rem; padding:4px 12px; border-radius:8px; margin:2px 6px 2px 0; border:1px solid; }
.chip.g { color:{GREEN}; background:#f0fdf4; border-color:#b8e6c8; }
.chip.a { color:{AMBER}; background:#fffaf0; border-color:#f3d9a4; }
.chip.r { color:{RED}; background:#fff1f4; border-color:#f6b8c6; }
.chip.t { color:{TEAL}; background:#ecfdfa; border-color:#b7e4dd; }
.kpi { background:#fff; border:1px solid {LINE}; border-radius:14px; padding:14px 18px; height:100%; margin-bottom:14px; }
.kpi .k { font-size:.82rem; color:{MUTED}; margin-bottom:2px; }
.kpi .v { font-family:'Newsreader',Georgia,serif; font-size:2.1rem; font-weight:600; line-height:1.15; color:{INK}; }
.kpi .s { font-size:.85rem; color:{MUTED}; }
.alert { border-radius:12px; padding:12px 16px; margin:0 0 14px; font-size:1rem; line-height:1.5; border:1px solid; }
.alert.ok { background:#ecfdf5; border-color:#b8e6c8; color:#14532d !important; }
.alert.bad { background:#fff1f4; border-color:#f6b8c6; color:#881337 !important; }
.alert * { color:inherit !important; }
.log { max-height:300px; overflow:auto; font-family:ui-monospace,Menlo,Consolas,monospace; font-size:.85rem; line-height:1.75; }
.log .ok { color:{GREEN}; } .log .warn { color:{AMBER}; } .log .risk, .log .err { color:{RED}; } .log .info { color:{MUTED}; }
.empty { text-align:center; padding:46px 20px; }
.empty .big { font-size:2.4rem; }
code { font-size:.9rem; background:#eef4f5; padding:3px 8px; border-radius:6px; color:{INK}; }
</style>
"""
for _k, _v in {"{INK}": INK, "{TEAL_D}": TEAL_D, "{TEAL}": TEAL, "{GREEN}": GREEN, "{AMBER}": AMBER, "{RED}": RED,
               "{MUTED}": MUTED, "{LINE}": LINE}.items():
    CSS = CSS.replace(_k, _v)
st.markdown(CSS, unsafe_allow_html=True)


@st.cache_resource(show_spinner="Loading models and agents… first run trains them (a few seconds).")
def runtime() -> main.Runtime:
    return main.build_runtime()


rt = runtime()
S = st.session_state
S.setdefault("fraud", None)
S.setdefault("lock", None)
S.setdefault("profile", "Returning")
S.setdefault("network", "Outage")
S.setdefault("mode", "Read + Write")


def keep_selected(key: str, fallback: str) -> None:
    """Segmented controls can be un-clicked; always keep one option selected."""
    if S.get(key) is None:
        S[key] = S.get("_last_" + key, fallback)


# ---- small HTML helpers ----------------------------------------------------------------------------
def card(inner: str) -> None:
    st.markdown(f'<div class="card">{inner}</div>', unsafe_allow_html=True)


def kpi(label: str, value: str, sub: str = "", color: str = INK) -> str:
    return (f'<div class="kpi"><div class="k">{label}</div><div class="v" style="color:{color}">{value}</div>'
            f'<div class="s">{sub}</div></div>')


def money(x) -> str:
    return "—" if x is None else f"${x:,.0f}"


def signed(x) -> str:
    return "—" if x is None else f"{'+' if x >= 0 else '−'}${abs(x):,.0f}"


def stepper(r) -> str:
    if not r:
        d = ["on", "", ""]
        l = ["", ""]
        third = "Success"
    else:
        d = ["done", "done", "ok" if r["ok"] else "fail"]
        l = ["done", "done"]
        third = "Success" if r["ok"] else "Escalated"
    sym = ["1", "2", "✓" if r and r["ok"] else "!" if r else "3"]
    names = ["Initiated", "Pending (timeout held)", third]
    out = ""
    for i in range(3):
        out += f'<div class="dot {d[i]}">{sym[i]}</div><span class="slabel">{names[i]}</span>'
        if i < 2:
            out += f'<div class="line {l[i]}"></div>'
    return f'<div class="steps">{out}</div>'


# ---- header ----------------------------------------------------------------------------------------
llm = rt.cfg.get("LLM_Configuration", {})
llm_on = bool(llm.get("API_Key")) and not llm["API_Key"].startswith("your_")
mtr = rt.bundle.get("metrics", {})
pills = "".join(f'<span class="pill">{t}</span>' for t in [
    "AI agent: LLM connected" if llm_on else "AI agent: template mode (no API key)",
    f"Fraud model AUC {mtr['fraud']['roc_auc']:.2f}" if mtr else "Models loaded",
    "Append-only database"])
st.markdown(f'<div class="hero"><div><h1>🛡️ Fintech Agent Console</h1>'
            f'<p>Fraud triage that never blames customers for network failures · transactions that never double-spend</p></div>'
            f'<div>{pills}</div></div>', unsafe_allow_html=True)

tab1, tab2, tab3 = st.tabs(["Timeout Lifecycle", "Concurrency Lab", "Insights"])

# =============================== Timeout lifecycle ===================================================
with tab1:
    r = S["fraud"]
    state = r["state"] if r else "INITIATED"
    badge = {"INITIATED": "", "SUCCESS": "success", "FAILED": "failed"}[state]
    st.markdown(f'<div class="card slim"><span class="badge {badge}">{state}</span><b style="font-family:Newsreader,Georgia,serif;font-size:1.2rem">Transaction lifecycle</b>'
                f' <span class="sub">&nbsp;A timeout means <b>unknown</b>, not fraud. Never auto-block; retry safely, then triage.</span>'
                f'{stepper(r)}</div>', unsafe_allow_html=True)

    left, right = st.columns([5, 7], gap="large")
    with left:
        st.markdown('<div class="step-h"><span class="num">1</span>Choose a scenario</div>', unsafe_allow_html=True)
        profile = st.segmented_control("Customer profile", ["Returning", "New"], key="profile", on_change=keep_selected, args=("profile", "Returning"),
                                       help="Returning customers have history; new customers do not.") or "Returning"
        S["_last_profile"] = profile
        network = st.segmented_control("Regional network", ["Outage", "Stable"], key="network", on_change=keep_selected, args=("network", "Outage"),
                                       help="Outage = the region really is failing, so the timeout is explained.") or "Outage"
        S["_last_network"] = network
        if profile == "Returning":
            cls, txt = "g", "Low risk → auto-approve"
        elif network == "Outage":
            cls, txt = "a", "Medium risk → out-of-band verification"
        else:
            cls, txt = "r", "High risk → human triage"
        st.markdown(f'<div style="margin:8px 0 0"><span class="sub">Expected route&nbsp;&nbsp;</span><span class="chip {cls}">{txt}</span></div>',
                    unsafe_allow_html=True)

        st.markdown('<div class="step-h" style="margin-top:12px"><span class="num">2</span>Run it</div>', unsafe_allow_html=True)
        b1, b2 = st.columns([3, 1])
        if b1.button("▶ Simulate network timeout", type="primary", width="stretch"):
            with st.spinner("Agent is working…"):
                S["fraud"] = rt.fraud.run_timeout_scenario(profile.lower(), network.lower())
            st.rerun()
        if b2.button("Reset", key="reset_fraud", width="stretch"):
            S["fraud"] = None
            st.rerun()
        with st.expander("How routing works"):
            st.markdown("- **Below 40** → auto-approve\n- **40 – 69** → out-of-band verification\n- **70 and above** → human triage\n\n"
                        "Infrastructure metrics are kept out of the fraud score, so an outage can't make a customer look guilty.")

    with right:
        st.markdown('<div class="step-h"><span class="num">3</span>Read the result</div>', unsafe_allow_html=True)
        if not r:
            card('<div class="empty"><div class="big">🧭</div><h4>No result yet</h4>'
                 '<div class="sub">Pick a profile and network on the left, then press <b>Simulate network timeout</b>.<br>'
                 'The risk score, retries and agent log will appear here.</div></div>')
        else:
            st.markdown(f'<div class="alert {"ok" if r["ok"] else "bad"}">{"✅" if r["ok"] else "🛡️"} {html.escape(r["message"])}</div>',
                        unsafe_allow_html=True)
            color = TIER_COLOR[r["tier"]]
            k1, k2, k3 = st.columns(3)
            k1.markdown(kpi("Risk score", f'{r["risk"]}<span style="font-size:1rem;color:{MUTED}"> / 100</span>',
                            f'{r["tier"].title()} · {r["action"]}', color), unsafe_allow_html=True)
            k2.markdown(kpi("Safe retries", f'{r["retries"]} / {r["max_retries"]}', "same key, no duplicates"), unsafe_allow_html=True)
            k3.markdown(kpi("Context kept", f'{r["ttl_remaining"]:,}s', "24h window for reconciliation"), unsafe_allow_html=True)

            g1, g2 = st.columns([1, 1])
            with g1:
                fig = go.Figure(go.Indicator(mode="gauge+number", value=r["risk"], number={"font": {"size": 34, "color": INK}},
                                             gauge={"axis": {"range": [0, 100]}, "bar": {"color": color},
                                                    "steps": [{"range": [0, 40], "color": "#dcfce7"},
                                                              {"range": [40, 70], "color": "#fef3c7"},
                                                              {"range": [70, 100], "color": "#ffe4e6"}]}))
                fig.update_layout(height=210, margin=dict(l=24, r=24, t=18, b=0), paper_bgcolor="rgba(0,0,0,0)")
                st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})
            with g2:
                card(f'<h4>Idempotency key</h4><code>{r["idem_key"]}</code>'
                     f'<div class="sub" style="margin-top:10px">Retries reuse this key, so the ledger rejects any duplicate charge.</div>'
                     f'<div class="sub" style="margin-top:10px"><b>Agent rationale:</b> {html.escape(r["explanation"])}</div>'
                     f'<div class="sub" style="margin-top:6px">{"LLM-written" if r["llm_used"] else "Template (add an API key in secrets.toml for LLM text)"}</div>')

            lines = "".join(f'<div class="{l["level"]}">{l["ts"]} &nbsp;{html.escape(l["msg"])}</div>' for l in r["logs"])
            card(f'<h4>Agent activity log</h4><div class="log">{lines}</div>')

# =============================== Concurrency lab =====================================================
with tab2:
    res, stt = S["lock"], rt.locks.state(ACCOUNT)
    st.markdown('<div class="card slim"><span class="badge">Apache Ignite model</span><b style="font-family:Newsreader,Georgia,serif;font-size:1.2rem">Concurrency lab</b>'
                '<span class="sub">&nbsp;&nbsp;Different accounts run in parallel. The same account is strictly serialized, and readers never wait for writers.</span></div>',
                unsafe_allow_html=True)

    live = res["live"] if res else stt["live"]
    snap = res["snapshot"] if res else stt["snapshot"]
    cols = st.columns(4)
    for col, (k, v, sub) in zip(cols, [
            ("Live balance", money(live), "latest value, including commits"),
            ("Snapshot read", money(snap), "what a reader sees"),
            ("Txn A", signed(res["txn_a"]) if res else "—", "deposit"),
            ("Txn B", signed(res["txn_b"]) if res else "—", "withdrawal" if res and res["txn_b"] else "—")]):
        col.markdown(kpi(k, v, sub), unsafe_allow_html=True)
    st.markdown(f'<span class="chip t">🔓 {res["lock"] if res else "No lock"}</span>'
                f'<span class="chip t">version v{res["version"] if res else stt["version"]}</span>'
                f'<span class="chip t">{res["isolation"] if res else "Snapshot isolation"}</span>', unsafe_allow_html=True)
    st.write("")

    left, right = st.columns([5, 7], gap="large")
    with left:
        st.markdown('<div class="step-h"><span class="num">1</span>Choose a scenario</div>', unsafe_allow_html=True)
        mode = st.segmented_control("Scenario", ["Read + Write", "Write + Write"], key="mode", on_change=keep_selected, args=("mode", "Read + Write"),
                                    label_visibility="collapsed") or "Read + Write"
        S["_last_mode"] = mode
        st.markdown(f'<div class="sub" style="margin:8px 0">' + (
            "A writer deposits <b>$5,000</b> while a reader checks the balance. The reader must never wait and must see only committed money."
            if mode == "Read + Write" else
            "A <b>+$5,000</b> deposit and a <b>−$2,000</b> withdrawal hit the same account together. They must apply one at a time with no lost update.")
            + "</div>", unsafe_allow_html=True)
        st.markdown('<div class="step-h" style="margin-top:12px"><span class="num">2</span>Run it</div>', unsafe_allow_html=True)
        b1, b2 = st.columns([3, 1])
        if b1.button("▶ Run concurrent scenario", type="primary", width="stretch"):
            with st.spinner("Executing…"):
                S["lock"] = (rt.locks.run_read_write(ACCOUNT) if mode == "Read + Write" else rt.locks.run_write_write(ACCOUNT))
            st.rerun()
        if b2.button("Reset", key="reset_lock", width="stretch", help="Set the account back to $10,000, v1"):
            rt.locks.reset(ACCOUNT)
            S["lock"] = None
            st.rerun()
        st.caption("Tip: press Reset between runs to start from $10,000 again.")
        with st.expander("Isolation model & guarantees"):
            st.markdown("- Reads and fraud checks use **snapshot isolation**, so they never block writers.\n"
                        "- Same-account writes are **serialized** through a per-account queue.\n"
                        "- **WAL durability:** nothing is reported committed until it is safely on disk.\n"
                        "- Zero double-spend and zero overdraft from race conditions.")

    with right:
        st.markdown('<div class="step-h"><span class="num">3</span>Read the result</div>', unsafe_allow_html=True)
        if not res:
            card('<div class="empty"><div class="big">🧪</div><h4>No trace yet</h4>'
                 '<div class="sub">Press <b>Run concurrent scenario</b> to see the step-by-step transaction trace.</div></div>')
        else:
            st.markdown(f'<div class="alert {"ok" if res["ok"] else "bad"}"><b>ACID invariant {"held" if res["ok"] else "VIOLATED"}.</b> '
                        f'{html.escape(res["message"])}</div>', unsafe_allow_html=True)
            steps = "".join(f'<div class="{"ok" if t["level"] == "ok" else t["level"]}">{i + 1:02d} &nbsp;[{t["t_ms"]} ms] {html.escape(t["msg"])}</div>'
                            for i, t in enumerate(res["trace"]))
            card(f'<h4>Transaction trace</h4><div class="log">{steps}</div>')
            fig, ax = plt.subplots(figsize=(8, 1.7))
            for i, t in enumerate(res["trace"]):
                ax.scatter(t["t_ms"], 0, color={"ok": GREEN, "warn": AMBER, "err": RED}.get(t["level"], TEAL), s=70, zorder=3)
                ax.annotate(str(i + 1), (t["t_ms"], 0), textcoords="offset points", xytext=(0, 11 if i % 2 == 0 else -17), ha="center", fontsize=9, color=INK)
            ax.axhline(0, color=LINE, zorder=1)
            ax.set(yticks=[], xlabel="milliseconds since the scenario started")
            ax.spines[["left", "right", "top"]].set_visible(False)
            fig.patch.set_alpha(0)
            ax.patch.set_alpha(0)
            buf = io.BytesIO()
            fig.savefig(buf, format="png", transparent=True, dpi=200, bbox_inches="tight")
            plt.close(fig)
            st.image(buf)

# =============================== Insights ============================================================
with tab3:
    if main.read_report("summary_report.md").startswith("_No report"):
        main.generate_reports(rt.cfg)
    txn, cust = main.load_history(rt.cfg)
    pay = txn[txn["kind"] == "payment"].drop_duplicates("txn_id", keep="last") if len(txn) else txn
    pay = pay.dropna(subset=["risk_score"]) if len(pay) else pay
    wr = txn[txn["kind"].isin(["deposit", "withdraw"])] if len(txn) else txn
    commits = int((wr["status"] == "COMMITTED").sum()) if len(wr) else 0
    blocked = int(((pay["status"] == "FAILED") & (pay["tier"] != "HIGH")).sum()) if len(pay) else 0
    k = st.columns(4)
    k[0].markdown(kpi("Timeout scenarios", str(len(pay)), "payments handled"), unsafe_allow_html=True)
    k[1].markdown(kpi("Average risk", f'{pay["risk_score"].astype(float).mean():.0f}' if len(pay) else "—", "out of 100"), unsafe_allow_html=True)
    k[2].markdown(kpi("Wrongly blocked", str(blocked), "by a network fault alone", GREEN if blocked == 0 else RED), unsafe_allow_html=True)
    k[3].markdown(kpi("Committed writes", str(commits), "WAL-acknowledged"), unsafe_allow_html=True)

    if len(pay):
        pay = pay.assign(risk_score=pay["risk_score"].astype(float))
        c1, c2 = st.columns(2, gap="large")
        with c1.container(border=True):
            st.plotly_chart(px.pie(pay, names="tier", title="Decision tiers", hole=.5, color="tier", color_discrete_map=TIER_COLOR)
                            .update_layout(height=320), width="stretch")
        with c2.container(border=True):
            st.plotly_chart(px.histogram(pay, x="risk_score", title="Risk score distribution", color_discrete_sequence=[TEAL])
                            .update_traces(xbins=dict(start=0, end=100, size=10)).update_xaxes(range=[0, 100], title="risk score (0–100)")
                            .update_yaxes(title="transactions", dtick=1).update_layout(height=320, bargap=.08), width="stretch")
        c3, c4 = st.columns(2, gap="large")
        with c3.container(border=True):
            st.plotly_chart(px.bar(pay.groupby(["network", "tier"]).size().reset_index(name="n"), x="network", y="n", color="tier",
                                   title="Outcomes by network state", color_discrete_map=TIER_COLOR)
                            .update_yaxes(title="transactions", dtick=1).update_layout(height=320), width="stretch")
        acct = cust[cust["account_id"] == ACCOUNT] if len(cust) else cust
        with c4.container(border=True):
            if len(acct) > 1:
                st.plotly_chart(px.line(acct.reset_index(drop=True).reset_index(), x="index", y="balance", markers=True,
                                        title=f"{ACCOUNT} balance history", color_discrete_sequence=[TEAL])
                                .update_xaxes(title="commit #").update_yaxes(title="balance ($)").update_layout(height=320), width="stretch")
            else:
                st.info("Run a concurrency scenario to see the balance history.")
    else:
        card('<div class="empty"><div class="big">📈</div><h4>No data yet</h4>'
             '<div class="sub">Run a scenario in the first two tabs and the charts will appear here.</div></div>')

    r1, r2 = st.columns(2, gap="large")
    with r1:
        with st.expander("Summary report", expanded=True):
            st.markdown(main.read_report("summary_report.md"))
    with r2:
        with st.expander("Behavior report"):
            st.markdown(main.read_report("behavior_report.md"))
    if st.button("Regenerate reports"):
        main.generate_reports(rt.cfg)
        st.rerun()
    if mtr:
        st.caption("Model hold-out metrics · " + " · ".join(f"{n}: accuracy {v['accuracy']:.2f}, AUC {v['roc_auc']:.2f}" for n, v in mtr.items()))
