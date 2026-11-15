"""Streamlit UI — presentation only. All logic lives in main.py and agentic/."""
import html
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
TEAL, GREEN, AMBER, RED, INK = "#0f766e", "#16a34a", "#d97706", "#e11d48", "#16323a"

st.set_page_config(page_title="Fintech Agent Console", page_icon="🛡️", layout="centered")
st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Newsreader:wght@500;600&display=swap');
.stApp {{ background:#eef4f5; }}
.block-container {{ max-width: 760px; padding-top: 2.5rem; }}
h1,h2,h3,.serif {{ font-family:'Newsreader',Georgia,serif !important; color:{INK}; }}
.card {{ background:#fff; border:1px solid #d6e3e5; border-radius:14px; padding:16px 20px; margin:10px 0; }}
.card h4 {{ margin:0 0 4px; font-family:'Newsreader',Georgia,serif; font-size:1.25rem; color:{INK}; }}
.sub {{ color:#5b7479; font-size:.85rem; }}
.badge {{ float:right; font-size:.7rem; border:1px solid #cbd9dc; border-radius:99px; padding:2px 10px; color:#5b7479; }}
.badge.pending {{ color:{AMBER}; border-color:#f3d9a4; background:#fffaf0; }}
.badge.success {{ color:{GREEN}; border-color:#b8e6c8; background:#f0fdf4; }}
.badge.failed {{ color:{RED}; border-color:#f6b8c6; background:#fff1f4; }}
.steps {{ display:flex; align-items:center; gap:8px; margin:14px 0 4px; }}
.dot {{ width:26px; height:26px; border-radius:50%; display:grid; place-items:center; font-size:.8rem;
        background:#e6eef0; color:#5b7479; }}
.dot.on {{ background:{TEAL}; color:#fff; }} .dot.done {{ background:#c7f0e6; color:{TEAL}; }}
.line {{ flex:1; height:1px; background:#d6e3e5; }}
.chip {{ display:inline-block; font-size:.72rem; padding:3px 10px; border-radius:8px; margin:2px 4px 2px 0; border:1px solid; }}
.chip.g {{ color:{GREEN}; background:#f0fdf4; border-color:#b8e6c8; }}
.chip.a {{ color:{AMBER}; background:#fffaf0; border-color:#f3d9a4; }}
.chip.r {{ color:{RED}; background:#fff1f4; border-color:#f6b8c6; }}
.big {{ font-family:'Newsreader',Georgia,serif; font-size:2.2rem; font-weight:600; line-height:1.1; }}
.bar {{ height:8px; border-radius:99px; background:#e6eef0; overflow:hidden; margin:8px 0 4px; }}
.bar > div {{ height:100%; border-radius:99px; }}
.alert {{ border-radius:10px; padding:10px 14px; margin-top:10px; font-size:.88rem; border:1px solid; }}
.alert.ok {{ background:#ecfdf5; border-color:#b8e6c8; color:#14532d; }}
.alert.bad {{ background:#fff1f4; border-color:#f6b8c6; color:#881337; }}
.log {{ max-height:190px; overflow:auto; font-family:ui-monospace,Menlo,monospace; font-size:.74rem; line-height:1.7; }}
.log .ok {{ color:{GREEN}; }} .log .warn {{ color:{AMBER}; }} .log .risk {{ color:{RED}; }} .log .info {{ color:#5b7479; }}
.metric {{ background:#fff; border:1px solid #d6e3e5; border-radius:12px; padding:10px 12px; }}
.metric .k {{ font-size:.7rem; color:#5b7479; }} .metric .v {{ font-family:'Newsreader',Georgia,serif; font-size:1.5rem; color:{INK}; }}
</style>""", unsafe_allow_html=True)


@st.cache_resource(show_spinner="Loading models and agents…")
def runtime() -> main.Runtime:
    return main.build_runtime()


rt = runtime()
S = st.session_state
S.setdefault("fraud", None)
S.setdefault("lock", None)
S.setdefault("mode", "Read + Write (MVCC)")


def card(inner: str, cls: str = "") -> None:
    st.markdown(f'<div class="card {cls}">{inner}</div>', unsafe_allow_html=True)


def money(x) -> str:
    return "—" if x is None else f"${x:,.0f}"


def signed(x) -> str:
    return "—" if x is None else f"{'+' if x >= 0 else '−'}${abs(x):,.0f}"


tab1, tab2, tab3 = st.tabs(["Timeout Lifecycle", "Concurrency Lab", "Insights"])

# ===================== Timeout lifecycle =====================
with tab1:
    r = S["fraud"]
    state = r["state"] if r else "INITIATED"
    badge = {"INITIATED": "", "SUCCESS": "success", "FAILED": "failed"}.get(state, "pending")
    s2 = "done" if r else ""
    s3 = ("on" if state == "SUCCESS" else "") if r else ""
    pct = r["progress"] if r else 15
    card(f"""<span class="badge {badge}">{state}</span><h4>Transaction Lifecycle</h4>
    <div class="sub">Timeout = Unknown. Never auto-block. Retry idempotently, then triage.</div>
    <div class="steps"><div class="dot {'done' if r else 'on'}">1</div><span class="sub">Initiated</span><div class="line"></div>
    <div class="dot {s2}">2</div><span class="sub">Pending</span><div class="line"></div>
    <div class="dot {s3}">3</div><span class="sub">Success</span></div><div class="sub">{pct}%</div>""")

    c1, c2 = st.columns(2)
    profile = c1.radio("Customer profile", ["Returning", "New"], horizontal=True, key="profile")
    network = c2.radio("Regional network", ["Outage", "Stable"], horizontal=True, key="network")
    st.markdown("""<span class="chip g">Returning → Low risk → Auto-approve</span>
    <span class="chip a">New + outage → Medium → OOB verify</span>
    <span class="chip r">New + stable → High → Human triage</span>""", unsafe_allow_html=True)

    b1, b2 = st.columns([3, 1])
    if b1.button("Simulate network timeout", type="primary", width="stretch"):
        S["fraud"] = rt.fraud.run_timeout_scenario(profile.lower(), network.lower())
        st.rerun()
    if b2.button("Reset", key="reset_fraud", width="stretch"):
        S["fraud"] = None
        st.rerun()

    if r:
        cls, ico = ("ok", "✅") if r["ok"] else ("bad", "🛡️")
        st.markdown(f'<div class="alert {cls}">{ico} {html.escape(r["message"])}</div>', unsafe_allow_html=True)
        color = GREEN if r["risk"] < 40 else AMBER if r["risk"] < 70 else RED
        card(f"""<h4>Risk score</h4><div class="big" style="color:{color}">{r['risk']} <span class="sub">/ 100</span></div>
        <div class="bar"><div style="width:{r['risk']}%;background:{color}"></div></div>
        <div class="sub">Low &lt;40 auto-approve · 40–69 OOB verify · ≥70 human triage</div>""")
        fig = go.Figure(go.Indicator(mode="gauge+number", value=r["risk"], gauge={
            "axis": {"range": [0, 100]}, "bar": {"color": color},
            "steps": [{"range": [0, 40], "color": "#dcfce7"}, {"range": [40, 70], "color": "#fef3c7"},
                      {"range": [70, 100], "color": "#ffe4e6"}]}))
        fig.update_layout(height=200, margin=dict(l=20, r=20, t=10, b=0), paper_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig, width="stretch")
        card(f"""<h4>Idempotency &amp; retries</h4><code>{r['idem_key']}</code>
        <div class="sub" style="margin-top:6px">Safe retries — {r['retries']} / {r['max_retries']} · key stored 24h; duplicates rejected at the ledger.</div>""")
        card(f"""<h4>Context preservation</h4><div class="big">{r['ttl_remaining']:,} <span class="sub">s remaining</span></div>
        <div class="sub">24h window holds device, location &amp; payload. Auto-reconciles with the bank ledger if unresolved.</div>""")
        lines = "".join(f'<div class="{l["level"]}">{l["ts"]} &nbsp;{html.escape(l["msg"])}</div>' for l in r["logs"])
        card(f'<h4>Agent activity log</h4><div class="log">{lines}</div>')
        st.caption(f"LLM rationale used: {'yes' if r['llm_used'] else 'no (template fallback — add an API key in secrets.toml)'}")

# ===================== Concurrency lab =====================
with tab2:
    card('<span class="badge">Apache Ignite model</span><h4>Concurrency Lab</h4>'
         '<div class="sub">Different accounts run in parallel · same account strictly serialized.</div>')
    S["mode"] = st.radio("Scenario", ["Read + Write (MVCC)", "Write + Write (Serialized)"], horizontal=True,
                         label_visibility="collapsed")
    res, stt = S["lock"], rt.locks.state(ACCOUNT)
    live = res["live"] if res else stt["live"]
    snap = res["snapshot"] if res else stt["snapshot"]
    m = st.columns(4)
    for col, (k, v) in zip(m, [("LIVE BALANCE", money(live)), ("SNAPSHOT READ", money(snap)),
                               ("TXN A", signed(res["txn_a"]) if res else "—"),
                               ("TXN B", signed(res["txn_b"]) if res else "—")]):
        col.markdown(f'<div class="metric"><div class="k">{k}</div><div class="v">{v}</div></div>', unsafe_allow_html=True)
    st.markdown(f'<span class="chip g">{res["lock"] if res else "No lock"}</span>'
                f'<span class="chip g">version v{res["version"] if res else stt["version"]}</span>'
                f'<span class="chip g">{res["isolation"] if res else "Snapshot isolation"}</span>', unsafe_allow_html=True)

    b1, b2 = st.columns([3, 1])
    if b1.button("Run concurrent scenario", type="primary", width="stretch"):
        with st.spinner("Executing…"):
            S["lock"] = (rt.locks.run_read_write(ACCOUNT) if S["mode"].startswith("Read")
                         else rt.locks.run_write_write(ACCOUNT))
        st.rerun()
    if b2.button("Reset", key="reset_lock", width="stretch"):
        rt.locks.reset(ACCOUNT)
        S["lock"] = None
        st.rerun()

    if res:
        st.markdown(f'<div class="alert {"ok" if res["ok"] else "bad"}"><b>ACID invariant {"held" if res["ok"] else "VIOLATED"}</b>'
                    f'<br>{html.escape(res["message"])}</div>', unsafe_allow_html=True)
        steps = "".join(f'<div class="{"ok" if t["level"] == "ok" else "warn" if t["level"] == "warn" else "info"}">'
                        f'{i + 1:02d} &nbsp;[{t["t_ms"]} ms] {html.escape(t["msg"])}</div>' for i, t in enumerate(res["trace"]))
        card(f'<h4>Transaction trace</h4><div class="log">{steps}</div>')
        fig, ax = plt.subplots(figsize=(7, 1.8))
        for i, t in enumerate(res["trace"]):
            ax.scatter(t["t_ms"], 0, color={"ok": GREEN, "warn": AMBER, "err": RED}.get(t["level"], TEAL), s=60, zorder=3)
            ax.annotate(str(i + 1), (t["t_ms"], 0), textcoords="offset points", xytext=(0, 9), ha="center", fontsize=8)
        ax.axhline(0, color="#cbd9dc", zorder=1)
        ax.set(yticks=[], xlabel="ms since scenario start")
        ax.spines[["left", "right", "top"]].set_visible(False)
        fig.patch.set_alpha(0)
        st.pyplot(fig)
    else:
        card('<h4>Transaction trace</h4><div class="sub">Run a scenario to see the transaction trace.</div>')
    card('<h4>Isolation model</h4><div class="sub">Reads &amp; async fraud checks use snapshot isolation — never block writers.<br>'
         'Same-account writes use serialized isolation via a per-account queue.<br>WAL durability: no commit reported until safely written to disk.</div>')
    card('<h4>Guarantees</h4><div class="sub">100% ACID · zero double-spend · zero overdraft from race conditions.<br>'
         'Balance update and fraud check run concurrently, non-blocking.</div>')

# ===================== Insights =====================
with tab3:
    txn, cust = main.load_history(rt.cfg)
    pay = txn[txn["kind"] == "payment"].drop_duplicates("txn_id", keep="last") if len(txn) else txn
    if len(pay) and pay["risk_score"].notna().any():
        pay = pay.dropna(subset=["risk_score"])
        c1, c2 = st.columns(2)
        c1.plotly_chart(px.pie(pay, names="tier", title="Decision tiers", hole=.5,
                               color="tier", color_discrete_map={"LOW": GREEN, "MEDIUM": AMBER, "HIGH": RED}),
                        width="stretch")
        c2.plotly_chart(px.histogram(pay, x="risk_score", nbins=10, title="Risk score distribution",
                                     color_discrete_sequence=[TEAL]), width="stretch")
        st.plotly_chart(px.bar(pay.groupby(["network", "tier"]).size().reset_index(name="n"), x="network", y="n",
                               color="tier", title="Outcomes by network state",
                               color_discrete_map={"LOW": GREEN, "MEDIUM": AMBER, "HIGH": RED}), width="stretch")
    else:
        st.info("Run a timeout scenario to populate fraud charts.")
    acct = cust[cust["account_id"] == ACCOUNT] if len(cust) else cust
    if len(acct) > 1:
        st.plotly_chart(px.line(acct.reset_index(), x="index", y="balance", markers=True, title=f"{ACCOUNT} balance history",
                                color_discrete_sequence=[TEAL]), width="stretch")
    mtr = rt.bundle.get("metrics", {})
    if mtr:
        st.caption("Model metrics (hold-out): " + " · ".join(
            f"{n}: acc {v['accuracy']:.2f}, AUC {v['roc_auc']:.2f}" for n, v in mtr.items()))
    if st.button("Regenerate reports"):
        main.generate_reports(rt.cfg)
    with st.expander("Summary report"):
        st.markdown(main.read_report("summary_report.md"))
    with st.expander("Behavior report"):
        st.markdown(main.read_report("behavior_report.md"))
