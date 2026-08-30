from __future__ import annotations

import time
from html import escape
from typing import Dict, List, Tuple

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
      [data-testid="stAppViewContainer"], [data-testid="stMain"], section.main, main { width:100% !important; max-width:none !important; }
      [data-testid="stMainBlockContainer"], .stMainBlockContainer, .block-container {
        box-sizing:border-box !important;
        width:calc(100vw - 48px) !important;
        max-width:calc(100vw - 48px) !important;
        margin-left:24px !important;
        margin-right:24px !important;
        padding-top:1.6rem !important;
        padding-bottom:3rem !important;
        padding-left:0 !important;
        padding-right:0 !important;
      }
      .hero-title {font-size: 2.65rem; font-weight: 800; letter-spacing: -0.03em; margin-bottom: .1rem;}
      .hero-sub {color:#6b7280; font-size:1.02rem; margin-bottom:1.15rem;}
      .thesis {border-left:4px solid #ef4444; padding:.7rem 1rem; background:#fafafa; border-radius:0 10px 10px 0;}
      .card {border:1px solid #e5e7eb; border-radius:14px; padding:16px 18px; background:white; margin:.35rem 0;}
      .card h4 {margin:0 0 .35rem 0;}
      .card p {margin:.15rem 0;}
      .muted {color:#6b7280;}
      .tiny {font-size:.82rem; color:#6b7280;}
      .good {border-left:6px solid #22c55e;}
      .warn {border-left:6px solid #f59e0b; background:#fffbeb;}
      .bad {border-left:6px solid #ef4444; background:#fef2f2;}
      .info {border-left:6px solid #3b82f6; background:#eff6ff;}
      .noise {border-left:6px solid #9ca3af; background:#f9fafb; opacity:.88;}
      .pill {display:inline-block; padding:3px 9px; border-radius:999px; font-size:.78rem; font-weight:700; margin-right:6px;}
      .pill-good {background:#dcfce7; color:#166534;}
      .pill-warn {background:#fef3c7; color:#92400e;}
      .pill-bad {background:#fee2e2; color:#991b1b;}
      .pill-gray {background:#f3f4f6; color:#4b5563;}
      .big-decision {font-size:1.45rem; font-weight:800; margin-top:.3rem;}
      .fact {font-size:1.18rem; font-weight:750; line-height:1.45;}
      .arrow {text-align:center; font-size:1.65rem; color:#6b7280; padding:.5rem 0;}
      div[data-testid="stMetricValue"] { font-size: 1.55rem; }
      div[data-testid="stDataFrame"] { border-radius: 12px; overflow:hidden; }
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

SENSITIVITY_LABELS = {
    0: "Public",
    1: "Internal",
    2: "Confidential",
    3: "Strategic / Highly Sensitive",
}


def risk_band(assessment: DeltaAssessment) -> str:
    materiality = max(assessment.score, assessment.impact)
    if materiality >= 0.75:
        return "HIGH"
    if materiality >= 0.45:
        return "MEDIUM"
    return "LOW"


def state_snapshot(state: ContextualState) -> Dict[str, str]:
    return {
        "Step": str(state.step),
        "Relevant evidence": str(state.relevant_event_count),
        "Ignored noise": str(state.ignored_event_count),
        "Domains": str(len(state.domains)),
        "Source sensitivity": SENSITIVITY_LABELS.get(state.max_sensitivity, str(state.max_sensitivity)),
        "Derived sensitivity": SENSITIVITY_LABELS.get(state.max_derived_sensitivity, "None") if state.max_derived_sensitivity else "None",
        "Derived facts": str(len(state.derived_facts)),
        "External boundary": "Yes" if state.trust_boundary_crossed else "No",
        "Reversible": "Yes" if state.capabilities.get("reversible", True) else "No",
        "Rollback": "Available" if state.capabilities.get("rollback_available", True) else "Removed",
        "Blast radius": str(state.capabilities.get("blast_radius", "low")),
    }


def render_architecture():
    st.markdown(
        """
        **Core pipeline**

        `Agent trajectory → Structured events → Contextual state → Δ detection → Impact assessment → Policy decision`

        **Design principle:** the deterministic fast path maintains compact state and provenance. A semantic slow path is invoked only when the delta is ambiguous or materially novel.
        """
    )


def render_source_cards(state: ContextualState):
    if not state.evidence:
        return
    st.markdown("#### Evidence that actually contributed")
    cols = st.columns(min(3, len(state.evidence)))
    for idx, evidence in enumerate(state.evidence.values()):
        with cols[idx % len(cols)]:
            st.markdown(
                f"""
                <div class="card info">
                  <h4>{escape(evidence.domain)}</h4>
                  <p>{escape(evidence.summary)}</p>
                  <p class="tiny">Source: {escape(evidence.source_id)} · {SENSITIVITY_LABELS.get(evidence.sensitivity, evidence.sensitivity)} · trust {evidence.trust:.2f}</p>
                </div>
                """,
                unsafe_allow_html=True,
            )

    if state.ignored_evidence:
        st.markdown("#### Smokescreen/noise filtered by contribution")
        noise_cols = st.columns(min(2, len(state.ignored_evidence)))
        for idx, evidence in enumerate(state.ignored_evidence.values()):
            with noise_cols[idx % len(noise_cols)]:
                st.markdown(
                    f"""
                    <div class="card noise">
                      <h4>⊘ {escape(evidence.domain)} — ignored</h4>
                      <p>{escape(evidence.summary)}</p>
                      <p class="tiny">Low contextual contribution ({evidence.contribution:.2f})</p>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )


def render_semantic_hero(state: ContextualState, event: AgentEvent, assessment: DeltaAssessment):
    fact = event.derived_fact or (state.derived_facts[-1] if state.derived_facts else "New derived knowledge")
    st.markdown(
        f"""
        <div class="card warn">
          <span class="pill pill-warn">SEMANTIC DELTA: {risk_band(assessment)}</span>
          <span class="pill pill-gray">NEW KNOWLEDGE EMERGED</span>
          <h4 style="margin-top:.65rem;">Before → After</h4>
          <p><b>Before:</b> several individually permitted internal observations.</p>
          <div class="arrow">↓ correlate / infer ↓</div>
          <p class="fact">“{escape(fact)}”</p>
          <p class="muted">This conclusion was not explicit in any single source.</p>
          <p><b>Sensitivity uplift:</b> {SENSITIVITY_LABELS.get(state.max_sensitivity)} → {SENSITIVITY_LABELS.get(state.max_derived_sensitivity)}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_consequence_hero(before: ContextualState, after: ContextualState, assessment: DeltaAssessment):
    st.markdown(
        f"""
        <div class="card warn">
          <span class="pill pill-warn">CONSEQUENCE DELTA: {risk_band(assessment)}</span>
          <span class="pill pill-gray">STATE TRANSITION</span>
          <h4 style="margin-top:.65rem;">Before → After</h4>
          <p><b>Before:</b> rollback available = {before.capabilities.get('rollback_available', True)}, reversible = {before.capabilities.get('reversible', True)}</p>
          <div class="arrow">↓ delete last rollback artifact ↓</div>
          <p class="fact">Rollback removed. Production change becomes effectively irreversible.</p>
          <p class="muted">The API call is authorized; the resulting system consequence crosses a higher-impact boundary.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_external_block(state: ContextualState, decision: PolicyDecision):
    fact = state.derived_facts[-1] if state.derived_facts else "Derived context"
    st.markdown(
        f"""
        <div class="card bad">
          <span class="pill pill-bad">EXTERNAL TRUST BOUNDARY</span>
          <h4 style="margin-top:.65rem;">Requested action: publish externally</h4>
          <p class="fact">“{escape(fact)}”</p>
          <p>Internal derived knowledge would become public.</p>
          <div class="big-decision">🔴 {decision.decision.value}</div>
          <p class="muted">{escape(decision.reason)}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_final_assessment(
    scenario_name: str,
    state: ContextualState,
    assessment: DeltaAssessment,
    decision: PolicyDecision,
):
    cls = "bad" if decision.decision == Decision.BLOCK else "warn" if decision.decision == Decision.REQUIRE_APPROVAL else "info"
    icon = DECISION_ICONS[decision.decision]
    title = "New sensitive knowledge + external boundary" if scenario_name == "Semantic Delta" else "Authorized action + unacceptable state transition"
    st.markdown(
        f"""
        <div class="card {cls}">
          <span class="pill {'pill-bad' if decision.decision == Decision.BLOCK else 'pill-warn'}">FINAL HORIZON ASSESSMENT</span>
          <h3 style="margin:.65rem 0 .25rem 0;">{escape(title)}</h3>
          <p><b>Delta:</b> {assessment.kind.value.title()} · <b>Impact:</b> {risk_band(assessment)} · <b>Decision:</b> {icon} {decision.decision.value}</p>
          <p class="muted">{escape(decision.reason)}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_traditional_vs_horizon(state: ContextualState):
    st.markdown("#### Why this is different from isolated content/action checks")
    left, right = st.columns(2)
    with left:
        st.markdown(
            """
            <div class="card good">
              <h4>Isolated checks</h4>
              <p>✅ Each source read is authorized</p>
              <p>✅ No single source states the inferred launch timing</p>
              <p>✅ No SIT-style pattern is required to detect the risk</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with right:
        st.markdown(
            f"""
            <div class="card bad">
              <h4>Agent Horizon</h4>
              <p>⚠ {len(state.evidence)} independent relevant sources compose into new knowledge</p>
              <p>⚠ Derived sensitivity exceeds the individual source sensitivity</p>
              <p>🔴 External publication turns the semantic delta into a security consequence</p>
            </div>
            """,
            unsafe_allow_html=True,
        )


def render_state_metrics(state: ContextualState):
    snapshot = state_snapshot(state)
    keys = [
        "Step",
        "Relevant evidence",
        "Ignored noise",
        "Domains",
        "Derived facts",
        "External boundary",
        "Reversible",
        "Rollback",
        "Blast radius",
    ]
    cols = st.columns(5)
    for idx, key in enumerate(keys):
        cols[idx % 5].metric(key, snapshot[key])


def run_scenario(events: List[AgentEvent], scenario_name: str, use_slow_path: bool, animate: bool):
    state = ContextualState()
    trace_rows: List[Dict[str, str]] = []
    latest_semantic: DeltaAssessment | None = None
    latest_material: DeltaAssessment | None = None
    final_decision: PolicyDecision | None = None

    live_status = st.empty()
    live_delta = st.empty()
    live_trace = st.empty()
    live_state = st.empty()

    for event in events:
        before, after = reduce_state(state, event)
        assessment = assess_delta(before, after, event)

        if use_slow_path and assessment.slow_path_recommended:
            assessment = mock_semantic_reassessment(assessment)

        if assessment.kind == DeltaKind.SEMANTIC:
            latest_semantic = assessment
            latest_material = assessment
        elif assessment.kind == DeltaKind.CONSEQUENCE:
            latest_material = assessment

        effective_assessment = assessment
        if event.action == "publish_external" and latest_semantic is not None:
            effective_assessment = latest_semantic

        decision = evaluate_policy(after, effective_assessment, event.action)
        final_decision = decision
        state = after

        is_noise = bool(event.evidence) and all(ev.source_id in state.ignored_evidence for ev in event.evidence)
        delta_label = "Filtered noise" if is_noise else effective_assessment.kind.value.title()
        trace_rows.append(
            {
                "Step": event.step,
                "Action": event.action,
                "Signal": delta_label,
                "Decision": decision.decision.value,
                "Description": event.description,
            }
        )

        live_status.info(f"Step {event.step}/{len(events)} — {event.description}")

        with live_delta.container():
            if is_noise:
                st.markdown(
                    f"""
                    <div class="card noise">
                      <span class="pill pill-gray">LOW-CONTRIBUTION EVENT</span>
                      <h4 style="margin-top:.65rem;">⊘ Ignored as smokescreen/noise</h4>
                      <p>{escape(event.description)}</p>
                      <p class="muted">Recorded in the trajectory, but it does not materially contribute to the active contextual state.</p>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            elif event.action == "infer" and effective_assessment.kind == DeltaKind.SEMANTIC:
                render_semantic_hero(state, event, effective_assessment)
            elif event.action == "publish_external" and latest_semantic is not None:
                render_external_block(state, decision)
            elif event.action == "delete_rollback" and effective_assessment.kind == DeltaKind.CONSEQUENCE:
                render_consequence_hero(before, after, effective_assessment)
            else:
                st.markdown(
                    f"""
                    <div class="card good">
                      <span class="pill pill-good">INDIVIDUALLY PERMITTED</span>
                      <h4 style="margin-top:.65rem;">{escape(event.action)}</h4>
                      <p>{escape(event.description)}</p>
                      <p class="muted">No material contextual delta requiring intervention at this step.</p>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

        with live_trace.container():
            st.markdown("#### Live trajectory")
            st.dataframe(pd.DataFrame(trace_rows), width="stretch", hide_index=True, height=min(280, 42 + len(trace_rows) * 35))

        with live_state.container():
            st.markdown("#### Current compact contextual state")
            render_state_metrics(state)

        if animate:
            # Deliberately slower at the two hero transitions for recording/readability.
            if event.action in ("infer", "delete_rollback", "publish_external"):
                time.sleep(2.1)
            elif is_noise:
                time.sleep(0.75)
            else:
                time.sleep(1.0)

    live_status.success("Scenario complete")

    final_assessment = latest_material or DeltaAssessment(
        kind=DeltaKind.NONE,
        score=0.0,
        confidence=1.0,
        impact=0.0,
        stability=1.0,
        reasons=[],
    )
    if scenario_name == "Semantic Delta" and latest_semantic is not None:
        final_assessment = latest_semantic
    assert final_decision is not None

    st.markdown("---")
    render_final_assessment(scenario_name, state, final_assessment, final_decision)

    if scenario_name == "Semantic Delta":
        render_source_cards(state)
        render_traditional_vs_horizon(state)
    else:
        st.markdown(
            """
            <div class="card info">
              <h4>No sensitive content was involved.</h4>
              <p>The policy decision is based on the trajectory's changing capability and reversibility state—not on content classification.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with st.expander("Technical details / debug view", expanded=False):
        st.write("Final state", state_snapshot(state))
        st.write("Assessment reasons")
        for reason in final_assessment.reasons:
            st.write("•", reason)
        st.write("Raw score (demo heuristic)", round(final_assessment.score, 3))
        st.write("Confidence", round(final_assessment.confidence, 3))
        st.write("Stability", round(final_assessment.stability, 3))


st.markdown('<div class="hero-title">Agent Horizon</div>', unsafe_allow_html=True)
st.markdown('<div class="hero-sub">Contextual Security & Privacy for Agentic AI</div>', unsafe_allow_html=True)
st.markdown(
    """
    <div class="thesis">
      <b>Individually permitted agent actions can compose into unsafe outcomes.</b><br/>
      <span class="muted">Agent Horizon evaluates what becomes newly knowable or newly possible as an agent trajectory evolves.</span>
    </div>
    """,
    unsafe_allow_html=True,
)

with st.expander("Architecture", expanded=False):
    render_architecture()

left, right = st.columns([0.85, 2.15], gap="large")
with left:
    scenario_name = st.radio(
        "Demo scenario",
        ["Semantic Delta", "Consequence Delta"],
        help="Semantic Delta is the hero scenario. Consequence Delta proves the model is not content-centric.",
    )
    include_noise = st.checkbox(
        "Include smokescreen/noise events",
        value=True,
        disabled=scenario_name != "Semantic Delta",
    )
    use_slow_path = st.checkbox("Enable mock semantic slow path", value=True)
    animate = st.checkbox("Animate for video recording", value=True)

    st.markdown("---")
    if scenario_name == "Semantic Delta":
        st.markdown(
            """
            **Reviewer takeaway**

            Three internal observations are individually allowed. Their correlation creates a new strategic conclusion that did not exist in any source. Noise is ignored, and external publication is blocked.
            """
        )
    else:
        st.markdown(
            """
            **Reviewer takeaway**

            No sensitive content is involved. Authorized operations compose into an effectively irreversible production state, so the last action requires approval.
            """
        )

with right:
    st.subheader("Scenario")
    if scenario_name == "Semantic Delta":
        events = build_semantic_delta_scenario(include_smokescreen=include_noise)
    else:
        events = build_consequence_delta_scenario()

    preview = pd.DataFrame(
        [
            {
                "Step": e.step,
                "Action": e.action,
                "Tool": e.tool,
                "Description": e.description,
            }
            for e in events
        ]
    )
    st.dataframe(preview, width="stretch", hide_index=True, height=min(315, 42 + len(events) * 35))

    button_label = f"▶ Run {scenario_name}"
    if st.button(button_label, type="primary", width="stretch"):
        run_scenario(events, scenario_name=scenario_name, use_slow_path=use_slow_path, animate=animate)
