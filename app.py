from __future__ import annotations

import time
from html import escape
from typing import Dict, List

import pandas as pd
import streamlit as st

from core import (
    ContextualState,
    Decision,
    DeltaKind,
    assess_delta,
    evaluate_policy,
    mock_semantic_reassessment,
    reduce_state,
)
from core.models import AgentEvent, DeltaAssessment, PolicyDecision
from scenarios import build_consequence_delta_scenario, build_semantic_delta_scenario

st.set_page_config(page_title="Agent Horizon", page_icon="◉", layout="wide")

st.markdown(
    """
    <style>
      header[data-testid="stHeader"] {background:rgba(255,255,255,.96);}
      [data-testid="stMainBlockContainer"], .stMainBlockContainer, .block-container {
        width:calc(100vw - 56px) !important; max-width:1500px !important;
        margin:0 auto !important; padding-top:1.25rem !important; padding-bottom:3rem !important;
      }
      .hero-title {font-size:2.75rem;font-weight:850;letter-spacing:-.035em;margin-bottom:.05rem;}
      .hero-sub {color:#667085;font-size:1.02rem;margin-bottom:.8rem;}
      .thesis {border:1px solid #e5e7eb;border-left:5px solid #111827;padding:.9rem 1rem;background:#fbfbfc;border-radius:0 12px 12px 0;}
      .stack {display:flex;align-items:center;gap:8px;flex-wrap:wrap;margin:.9rem 0 1.1rem 0}
      .stack .node {padding:7px 11px;border:1px solid #d0d5dd;border-radius:999px;background:#fff;font-size:.83rem;font-weight:700;}
      .stack .horizon {border-color:#f59e0b;background:#fffbeb;color:#92400e;}
      .stack .arrow {color:#98a2b3;font-size:.9rem;}
      .card {border:1px solid #e5e7eb;border-radius:14px;padding:16px 18px;background:white;margin:.35rem 0;}
      .card h4 {margin:0 0 .35rem 0}.card p {margin:.15rem 0}.muted{color:#667085}.tiny{font-size:.82rem;color:#667085}
      .good{border-left:6px solid #22c55e}.warn{border-left:6px solid #f59e0b;background:#fffbeb}
      .bad{border-left:6px solid #ef4444;background:#fef2f2}.info{border-left:6px solid #3b82f6;background:#eff6ff}
      .noise{border-left:6px solid #9ca3af;background:#f9fafb;opacity:.88}
      .pill{display:inline-block;padding:3px 9px;border-radius:999px;font-size:.76rem;font-weight:750;margin-right:6px}
      .pill-good{background:#dcfce7;color:#166534}.pill-warn{background:#fef3c7;color:#92400e}
      .pill-bad{background:#fee2e2;color:#991b1b}.pill-gray{background:#f2f4f7;color:#475467}
      .big-decision{font-size:1.42rem;font-weight:850;margin-top:.35rem}.fact{font-size:1.14rem;font-weight:750;line-height:1.42}
      .flowstep{border:1px solid #eaecf0;border-radius:12px;padding:12px 14px;background:#fff;min-height:95px}
      .flowstep b{display:block;margin-bottom:4px}.kicker{font-size:.75rem;color:#667085;text-transform:uppercase;letter-spacing:.06em;font-weight:800}
      div[data-testid="stMetricValue"]{font-size:1.45rem} div[data-testid="stDataFrame"]{border-radius:12px;overflow:hidden}
    </style>
    """,
    unsafe_allow_html=True,
)

DECISION_ICONS = {
    Decision.ALLOW: "✅",
    Decision.ALLOW_AUDIT: "🟢",
    Decision.CONSTRAIN: "🟠",
    Decision.REQUIRE_APPROVAL: "🟡",
    Decision.BLOCK: "🔴",
}
SENSITIVITY_LABELS = {0:"Public",1:"Internal",2:"Confidential",3:"Strategic / Highly Sensitive"}

def risk_band(assessment: DeltaAssessment) -> str:
    materiality = max(assessment.score, assessment.impact)
    return "HIGH" if materiality >= .75 else "MEDIUM" if materiality >= .45 else "LOW"

def state_snapshot(state: ContextualState) -> Dict[str, str]:
    return {
        "Step": str(state.step),
        "Evidence": str(state.relevant_event_count),
        "Noise filtered": str(state.ignored_event_count),
        "Domains": str(len(state.domains)),
        "Derived facts": str(len(state.derived_facts)),
        "External boundary": "Yes" if state.trust_boundary_crossed else "No",
        "Reversible": "Yes" if state.capabilities.get("reversible", True) else "No",
        "Rollback": "Available" if state.capabilities.get("rollback_available", True) else "Removed",
        "Blast radius": str(state.capabilities.get("blast_radius", "low")),
    }

def render_architecture_strip():
    st.markdown(
        """
        <div class="stack">
          <span class="node">MCP / A2A / Tools</span><span class="arrow">→</span>
          <span class="node">Identity + authorization</span><span class="arrow">→</span>
          <span class="node horizon">Agent Horizon</span><span class="arrow">→</span>
          <span class="node">Context state</span><span class="arrow">→</span>
          <span class="node">Semantic / consequence Δ</span><span class="arrow">→</span>
          <span class="node">Policy decision</span>
        </div>
        """, unsafe_allow_html=True
    )

def render_four_stage_model():
    cols = st.columns(4, gap="small")
    items = [
        ("1 · Observe","Authorized action","Capture structured event + provenance."),
        ("2 · Reduce","Compact context","Keep contributing state; discard low-value noise."),
        ("3 · Compare","What changed?","Detect newly knowable or newly possible impact."),
        ("4 · Enforce","Decision","Allow, audit, approval, constrain, or block."),
    ]
    for col, (k,t,b) in zip(cols, items):
        with col:
            st.markdown(f'<div class="flowstep"><span class="kicker">{k}</span><b>{t}</b><span class="muted">{b}</span></div>', unsafe_allow_html=True)

def render_source_cards(state: ContextualState):
    if not state.evidence:
        return
    st.markdown("#### Evidence that actually contributed")
    cols = st.columns(min(3, len(state.evidence)))
    for idx, evidence in enumerate(state.evidence.values()):
        with cols[idx % len(cols)]:
            st.markdown(
                f'<div class="card info"><h4>{escape(evidence.domain)}</h4><p>{escape(evidence.summary)}</p>'
                f'<p class="tiny">Source: {escape(evidence.source_id)} · {SENSITIVITY_LABELS.get(evidence.sensitivity,evidence.sensitivity)} · trust {evidence.trust:.2f}</p></div>',
                unsafe_allow_html=True,
            )
    if state.ignored_evidence:
        st.markdown("#### Smokescreen/noise filtered by contribution")
        cols = st.columns(min(2, len(state.ignored_evidence)))
        for idx, evidence in enumerate(state.ignored_evidence.values()):
            with cols[idx % len(cols)]:
                st.markdown(
                    f'<div class="card noise"><h4>⊘ {escape(evidence.domain)} — ignored</h4><p>{escape(evidence.summary)}</p>'
                    f'<p class="tiny">Low contextual contribution ({evidence.contribution:.2f})</p></div>',
                    unsafe_allow_html=True,
                )

def render_semantic_hero(state: ContextualState, event: AgentEvent, assessment: DeltaAssessment):
    fact = event.derived_fact or (state.derived_facts[-1] if state.derived_facts else "New derived knowledge")
    st.markdown(
        f"""<div class="card warn">
        <span class="pill pill-warn">SEMANTIC DELTA · {risk_band(assessment)}</span><span class="pill pill-gray">NEW KNOWLEDGE</span>
        <h4 style="margin-top:.65rem">Context changed</h4>
        <p><b>Before:</b> individually permitted observations.</p>
        <p class="fact">→ “{escape(fact)}”</p>
        <p class="muted">The conclusion did not exist in any single source.</p>
        <p><b>Sensitivity uplift:</b> {SENSITIVITY_LABELS.get(state.max_sensitivity)} → {SENSITIVITY_LABELS.get(state.max_derived_sensitivity)}</p>
        </div>""", unsafe_allow_html=True
    )

def render_consequence_hero(before: ContextualState, after: ContextualState, assessment: DeltaAssessment):
    st.markdown(
        f"""<div class="card warn">
        <span class="pill pill-warn">CONSEQUENCE DELTA · {risk_band(assessment)}</span><span class="pill pill-gray">NEW CAPABILITY STATE</span>
        <h4 style="margin-top:.65rem">Authorized call, materially different outcome</h4>
        <p><b>Before:</b> rollback={before.capabilities.get('rollback_available',True)}, reversible={before.capabilities.get('reversible',True)}</p>
        <p class="fact">→ Rollback removed; production becomes effectively irreversible.</p>
        <p class="muted">The action is authorized. The trajectory-level consequence is not equivalent.</p>
        </div>""", unsafe_allow_html=True
    )

def render_external_block(state: ContextualState, decision: PolicyDecision):
    fact = state.derived_facts[-1] if state.derived_facts else "Derived context"
    st.markdown(
        f"""<div class="card bad">
        <span class="pill pill-bad">EXTERNAL TRUST BOUNDARY</span>
        <h4 style="margin-top:.65rem">Requested action: publish externally</h4>
        <p class="fact">“{escape(fact)}”</p>
        <p>Derived internal knowledge would cross the enterprise boundary.</p>
        <div class="big-decision">🔴 {decision.decision.value}</div><p class="muted">{escape(decision.reason)}</p>
        </div>""", unsafe_allow_html=True
    )

def render_final_assessment(scenario_name: str, state: ContextualState, assessment: DeltaAssessment, decision: PolicyDecision):
    cls = "bad" if decision.decision == Decision.BLOCK else "warn" if decision.decision == Decision.REQUIRE_APPROVAL else "info"
    title = "New sensitive knowledge + external boundary" if scenario_name == "Semantic Delta" else "Authorized action + unacceptable state transition"
    st.markdown(
        f"""<div class="card {cls}">
        <span class="pill {'pill-bad' if decision.decision == Decision.BLOCK else 'pill-warn'}">FINAL HORIZON ASSESSMENT</span>
        <h3 style="margin:.65rem 0 .25rem">{escape(title)}</h3>
        <p><b>Delta:</b> {assessment.kind.value.title()} · <b>Impact:</b> {risk_band(assessment)} ·
        <b>Decision:</b> {DECISION_ICONS[decision.decision]} {decision.decision.value}</p>
        <p class="muted">{escape(decision.reason)}</p></div>""", unsafe_allow_html=True
    )

def render_difference(state: ContextualState):
    st.markdown("#### Why this layer exists")
    a,b = st.columns(2)
    with a:
        st.markdown("""<div class="card good"><h4>Identity / authorization / isolated guardrails</h4>
        <p>✅ Actor is authenticated</p><p>✅ Each source read is permitted</p><p>✅ Each tool call can be valid in isolation</p>
        </div>""", unsafe_allow_html=True)
    with b:
        st.markdown(f"""<div class="card bad"><h4>Agent Horizon</h4>
        <p>⚠ {len(state.evidence)} relevant observations compose into new context</p>
        <p>⚠ Evaluates the trajectory, not only the current call</p>
        <p>🔴 Intervenes when newly knowable / possible impact crosses policy</p></div>""", unsafe_allow_html=True)

def render_state_metrics(state: ContextualState):
    snapshot = state_snapshot(state)
    keys = list(snapshot.keys())
    cols = st.columns(5)
    for idx,key in enumerate(keys):
        cols[idx % 5].metric(key, snapshot[key])

def run_scenario(events: List[AgentEvent], scenario_name: str, use_slow_path: bool, animate: bool):
    state = ContextualState()
    trace_rows: List[Dict[str, str]] = []
    latest_semantic = None
    latest_material = None
    final_decision = None
    live_status, live_delta, live_trace, live_state = st.empty(), st.empty(), st.empty(), st.empty()

    for event in events:
        before, after = reduce_state(state, event)
        assessment = assess_delta(before, after, event)
        if use_slow_path and assessment.slow_path_recommended:
            assessment = mock_semantic_reassessment(assessment)
        if assessment.kind == DeltaKind.SEMANTIC:
            latest_semantic = latest_material = assessment
        elif assessment.kind == DeltaKind.CONSEQUENCE:
            latest_material = assessment

        effective = latest_semantic if event.action == "publish_external" and latest_semantic is not None else assessment
        decision = evaluate_policy(after, effective, event.action)
        final_decision, state = decision, after
        is_noise = bool(event.evidence) and all(ev.source_id in state.ignored_evidence for ev in event.evidence)
        trace_rows.append({
            "Step":event.step, "Action":event.action,
            "Signal":"Filtered noise" if is_noise else effective.kind.value.title(),
            "Decision":decision.decision.value, "Description":event.description
        })

        live_status.info(f"Step {event.step}/{len(events)} — {event.description}")
        with live_delta.container():
            if is_noise:
                st.markdown(f'<div class="card noise"><span class="pill pill-gray">LOW-CONTRIBUTION EVENT</span><h4 style="margin-top:.65rem">⊘ Filtered from active context</h4><p>{escape(event.description)}</p></div>', unsafe_allow_html=True)
            elif event.action == "infer" and effective.kind == DeltaKind.SEMANTIC:
                render_semantic_hero(state,event,effective)
            elif event.action == "publish_external" and latest_semantic is not None:
                render_external_block(state,decision)
            elif event.action == "delete_rollback" and effective.kind == DeltaKind.CONSEQUENCE:
                render_consequence_hero(before,after,effective)
            else:
                st.markdown(f'<div class="card good"><span class="pill pill-good">INDIVIDUALLY PERMITTED</span><h4 style="margin-top:.65rem">{escape(event.action)}</h4><p>{escape(event.description)}</p><p class="muted">No material trajectory delta yet.</p></div>', unsafe_allow_html=True)

        with live_trace.container():
            st.markdown("#### Live trajectory")
            st.dataframe(pd.DataFrame(trace_rows), width="stretch", hide_index=True, height=min(275, 42+len(trace_rows)*35))
        with live_state.container():
            st.markdown("#### Compact contextual state")
            render_state_metrics(state)

        if animate:
            time.sleep(1.75 if event.action in ("infer","delete_rollback","publish_external") else .65 if is_noise else .85)

    live_status.success("Scenario complete")
    final_assessment = latest_semantic if scenario_name == "Semantic Delta" and latest_semantic is not None else latest_material
    if final_assessment is None:
        final_assessment = DeltaAssessment(kind=DeltaKind.NONE,score=0.0,confidence=1.0,impact=0.0,stability=1.0,reasons=[])
    assert final_decision is not None
    st.markdown("---")
    render_final_assessment(scenario_name,state,final_assessment,final_decision)
    if scenario_name == "Semantic Delta":
        render_source_cards(state)
        render_difference(state)
    else:
        st.markdown('<div class="card info"><h4>No sensitive content was involved.</h4><p>The decision comes from changing capability and reversibility state—not content classification.</p></div>', unsafe_allow_html=True)

    with st.expander("Technical details / debug view", expanded=False):
        st.write("Final state", state_snapshot(state))
        st.write("Assessment reasons")
        for r in final_assessment.reasons:
            st.write("•",r)
        st.write("Raw score",round(final_assessment.score,3))
        st.write("Confidence",round(final_assessment.confidence,3))
        st.write("Stability",round(final_assessment.stability,3))

st.markdown('<div class="hero-title">Agent Horizon</div>', unsafe_allow_html=True)
st.markdown('<div class="hero-sub">Trajectory-aware contextual security for agentic AI</div>', unsafe_allow_html=True)
st.markdown("""<div class="thesis"><b>Identity tells us who may act. Authorization tells us whether one action is permitted.</b><br/>
<span class="muted">Agent Horizon asks what the trajectory has made <b>newly knowable</b> or <b>newly possible</b>—and evaluates that contextual impact before the next boundary is crossed.</span></div>""", unsafe_allow_html=True)
render_architecture_strip()
render_four_stage_model()

left,right = st.columns([.78,2.22], gap="large")
with left:
    scenario_name = st.radio("Demo scenario",["Semantic Delta","Consequence Delta"])
    include_noise = st.checkbox("Include smokescreen/noise", value=True, disabled=scenario_name!="Semantic Delta")
    use_slow_path = st.checkbox("Enable semantic slow path", value=True)
    animate = st.checkbox("Animate for recording", value=True)
    st.markdown("---")
    if scenario_name=="Semantic Delta":
        st.markdown("**Reviewer takeaway**\n\nPermitted reads compose into a new strategic inference. Low-value noise is ignored; external publication is blocked.")
    else:
        st.markdown("**Reviewer takeaway**\n\nNo sensitive content. Authorized operations compose into an effectively irreversible production state; approval is required.")

with right:
    st.subheader("Trajectory preview")
    events = build_semantic_delta_scenario(include_smokescreen=include_noise) if scenario_name=="Semantic Delta" else build_consequence_delta_scenario()
    preview = pd.DataFrame([{"Step":e.step,"Action":e.action,"Tool":e.tool,"Description":e.description} for e in events])
    st.dataframe(preview,width="stretch",hide_index=True,height=min(305,42+len(events)*35))
    if st.button(f"▶ Run {scenario_name}",type="primary",width="stretch"):
        run_scenario(events,scenario_name,use_slow_path,animate)
