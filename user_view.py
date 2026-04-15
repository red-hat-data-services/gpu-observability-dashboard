"""
End-User GPU Dashboard Page
=============================
Personal view for engineers and team leads.
Focus: "My team's GPUs", "Why is my job failing?", "When should I schedule?"

Designed to complement the executive dashboard with user-centric insights.
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

import data_live

PLOTLY_TEMPLATE = "plotly_dark"

CLOUD_COLORS = {
    "AWS": "#FF9900",
    "GCP": "#34A853",
    "IBM Cloud": "#0F62FE",
}

PRIORITY_COLORS = {
    "committed": "#1f77b4",
    "spot": "#2ca02c",
}

DAY_NAMES = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def _metric_card(label, value, delta=None, delta_color="normal"):
    """Render a metric card."""
    st.metric(label=label, value=value, delta=delta, delta_color=delta_color)


def _status_indicator(status, text):
    """Colored status indicator."""
    colors = {"good": "#2ca02c", "warning": "#ff7f0e", "critical": "#d62728", "info": "#1f77b4"}
    color = colors.get(status, "#888888")
    return f'<span style="color:{color}; font-size:1.2em;">●</span> {text}'


# ── Workload card CSS + badge colors ────────────────────────────────

_PRIORITY_BADGE = {
    "high-priority": ("P1", "#3b82f6", "#1e3a5f"),
    "low-priority": ("P2", "#f59e0b", "#5c3d0e"),
}

_STATUS_BADGE = {
    "admitted": ("#2ca02c", "#143d14"),
    "pending": ("#f59e0b", "#5c3d0e"),
    "preempted": ("#d62728", "#4a0e0e"),
    "finished": ("#6b7280", "#2d2d2d"),
}

_CARD_CSS = """
<style>
.wl-board { border-collapse: collapse; width: 100%; }
.wl-board th, .wl-board td { border: 1px solid #333; padding: 8px; vertical-align: top; }
.wl-board th { background: #1a1a2e; font-size: 0.95em; }
.wl-board td { background: #0d1117; min-height: 60px; }
.wl-card {
  display: inline-block; margin: 3px; padding: 6px 10px; border-radius: 6px;
  font-size: 0.82em; line-height: 1.4; min-width: 140px; vertical-align: top;
}
.wl-badge {
  display: inline-block; padding: 1px 6px; border-radius: 3px;
  font-size: 0.75em; font-weight: 600; margin-left: 4px;
}
.wl-gpu { font-weight: 600; }
.wl-name { font-weight: 500; margin-bottom: 2px; }
.wl-meta { color: #9ca3af; font-size: 0.78em; }
.quota-pill {
  display: inline-block; padding: 2px 8px; border-radius: 10px;
  font-size: 0.78em; margin: 2px;
}
</style>
"""


def _workload_card_html(w: dict) -> str:
    """Render a single workload card as HTML."""
    status = w.get("status", "pending")
    bg, border = _STATUS_BADGE.get(status, ("#6b7280", "#2d2d2d"))

    priority = w.get("priority", "")
    p_label, p_color, p_bg = _PRIORITY_BADGE.get(priority, ("", "#888", "#333"))
    priority_badge = (
        f'<span class="wl-badge" style="background:{p_bg};color:{p_color}">{p_label}</span>'
        if p_label else ""
    )

    gpu_count = w.get("gpu_requests", 0)
    name = w.get("name", "unknown")
    # Shorten long Kueue-generated names
    short_name = name
    if len(short_name) > 28:
        short_name = short_name[:25] + "..."

    reason = w.get("pending_reason", "")
    reason_line = f'<div class="wl-meta" title="{reason}">{reason[:50]}{"..." if len(reason)>50 else ""}</div>' if reason else ""

    return (
        f'<div class="wl-card" style="background:{border};border-left:3px solid {bg}">'
        f'  <div class="wl-name">{short_name}{priority_badge}</div>'
        f'  <span class="wl-badge" style="background:{bg};color:#fff">{gpu_count} GPU</span>'
        f'  {reason_line}'
        f'</div>'
    )


def _render_workload_activity():
    """Render the workload activity Kanban board."""
    st.markdown("#### Workload Activity")

    kueue = data_live.fetch_kueue_status()
    workloads = kueue.get("workloads", [])
    cq = kueue.get("cluster_queue", {})
    lqs = kueue.get("local_queues", [])

    # Status header badges
    n_pending = sum(1 for w in workloads if w.get("status") == "pending")
    n_admitted = sum(1 for w in workloads if w.get("status") == "admitted")
    n_finished = sum(1 for w in workloads if w.get("status") in ("finished", "preempted"))

    st.markdown(
        f'**Workload activity:** '
        f'<span style="background:#5c3d0e;color:#f59e0b;padding:2px 10px;border-radius:4px;font-weight:600">Pending {n_pending}</span> '
        f'<span style="background:#143d14;color:#2ca02c;padding:2px 10px;border-radius:4px;font-weight:600">Admitted {n_admitted}</span> '
        f'<span style="background:#2d2d2d;color:#9ca3af;padding:2px 10px;border-radius:4px;font-weight:600">Finished {n_finished}</span>',
        unsafe_allow_html=True,
    )

    # ClusterQueue quota info
    quota_gpu = cq.get("nominal_quota", {}).get("gpu", 0)
    admitted_total = cq.get("admitted_workloads", 0)
    pending_total = cq.get("pending_workloads", 0)

    st.markdown(
        f'<div style="margin:8px 0;padding:6px 12px;background:#1a1a2e;border-radius:6px;font-size:0.88em">'
        f'<b>{cq.get("name", "gpu-cluster-queue")}</b> &nbsp; '
        f'<span class="quota-pill" style="background:#1e3a5f;color:#60a5fa">NVIDIA A10G</span> '
        f'<span class="quota-pill" style="background:#1e3a5f;color:#60a5fa">Quota {admitted_total}/{quota_gpu}</span> '
        f'</div>',
        unsafe_allow_html=True,
    )

    if not workloads and not lqs:
        st.info("No Kueue workloads or queues found. Submit a job with a `kueue.x-k8s.io/queue-name` label to see it here.")
        return

    # Build Kanban: rows = namespaces, columns = Pending / Admitted / Finished
    namespaces = set()
    for w in workloads:
        namespaces.add(w.get("namespace", ""))
    for lq in lqs:
        namespaces.add(lq.get("namespace", ""))
    namespaces = sorted(namespaces)

    # Queue name lookup
    ns_to_queue = {lq["namespace"]: lq["name"] for lq in lqs}

    # Bucket workloads by namespace + status
    buckets: dict[str, dict[str, list]] = {}
    for ns in namespaces:
        buckets[ns] = {"pending": [], "admitted": [], "finished": []}
    for w in workloads:
        ns = w.get("namespace", "")
        status = w.get("status", "pending")
        col = "finished" if status in ("finished", "preempted") else status
        if ns in buckets:
            buckets[ns][col].append(w)

    # Render as HTML table
    rows_html = ""
    for ns in namespaces:
        queue_name = ns_to_queue.get(ns, "")
        pending_cards = "".join(_workload_card_html(w) for w in buckets[ns]["pending"]) or '<span style="color:#555">—</span>'
        admitted_cards = "".join(_workload_card_html(w) for w in buckets[ns]["admitted"]) or '<span style="color:#555">—</span>'
        finished_cards = "".join(_workload_card_html(w) for w in buckets[ns]["finished"]) or '<span style="color:#555">—</span>'

        rows_html += (
            f'<tr>'
            f'  <td><b>{ns}</b><br><span style="color:#9ca3af;font-size:0.82em">{queue_name}</span></td>'
            f'  <td>{pending_cards}</td>'
            f'  <td>{admitted_cards}</td>'
            f'  <td>{finished_cards}</td>'
            f'</tr>'
        )

    table_html = (
        f'{_CARD_CSS}'
        f'<table class="wl-board">'
        f'<thead><tr>'
        f'  <th style="width:18%">Namespace</th>'
        f'  <th style="width:27%">Pending</th>'
        f'  <th style="width:27%">Admitted</th>'
        f'  <th style="width:28%">Finished</th>'
        f'</tr></thead>'
        f'<tbody>{rows_html}</tbody>'
        f'</table>'
    )

    st.markdown(table_html, unsafe_allow_html=True)


def render_user_view(all_gpu_df, timeseries_df, hourly_df):
    """Render the end-user dashboard view."""

    # ── Team Selector ────────────────────────────────────────────────
    teams = sorted(all_gpu_df["team"].unique())

    col_sel, col_spacer = st.columns([1, 3])
    with col_sel:
        my_team = st.selectbox("My Team", teams, index=0, key="user_team")

    team_df = all_gpu_df[all_gpu_df["team"] == my_team]
    team_committed = team_df[team_df["workload_type"] == "committed"]
    team_hourly = hourly_df[hourly_df["team"] == my_team]

    # Team-level aggregates
    total_gpus = int(team_df["total_gpus"].sum())
    allocated_gpus = int(team_df["allocated_gpus"].sum())
    avg_used = round(float(team_df["used_pct"].mean()), 1)
    avg_util = round(float(team_df["utilization_pct"].mean()), 1)
    waste_gap = round(avg_used - avg_util, 1)

    st.markdown("---")

    # ══════════════════════════════════════════════════════════════════
    # SECTION 1: MY TEAM AT A GLANCE
    # ══════════════════════════════════════════════════════════════════

    st.markdown("#### My Team at a Glance")

    m1, m2, m3, m4, m5 = st.columns(5)
    with m1:
        _metric_card("Total GPUs", total_gpus)
    with m2:
        _metric_card("Allocated", allocated_gpus)
    with m3:
        _metric_card("Used %", f"{avg_used}%")
    with m4:
        _metric_card("Utilization %", f"{avg_util}%")
    with m5:
        delta_color = "inverse" if waste_gap > 20 else "normal"
        _metric_card("Waste Gap", f"{waste_gap}%", delta=f"{waste_gap}% idle" if waste_gap > 15 else None, delta_color=delta_color)

    # Status bar
    if waste_gap > 30:
        st.error(f"High waste detected: {waste_gap}% of allocated GPUs are idle. Consider reducing allocation or optimizing workloads.")
    elif waste_gap > 15:
        st.warning(f"Moderate waste: {waste_gap}% gap between allocation and utilization.")
    else:
        st.success(f"Good efficiency: only {waste_gap}% waste gap.")

    st.markdown("")

    # ══════════════════════════════════════════════════════════════════
    # SECTION 2: WORKLOAD ACTIVITY BOARD
    # ══════════════════════════════════════════════════════════════════

    st.markdown("---")
    _render_workload_activity()

    # ══════════════════════════════════════════════════════════════════
    # SECTION 3: GPU ALLOCATION BREAKDOWN
    # ══════════════════════════════════════════════════════════════════

    col_left, col_right = st.columns(2)

    with col_left:
        st.markdown("#### GPU Allocation by Type")

        gpu_agg = team_df.groupby(["gpu_type", "workload_type"]).agg(
            total_gpus=("total_gpus", "sum"),
            utilization_pct=("utilization_pct", "mean"),
        ).reset_index()

        if not gpu_agg.empty:
            fig = px.bar(
                gpu_agg, x="gpu_type", y="total_gpus", color="workload_type",
                color_discrete_map=PRIORITY_COLORS,
                title=f"<b>{my_team}</b> — GPUs by Type & Workload",
                labels={"total_gpus": "GPU Count", "gpu_type": "GPU Type", "workload_type": "Workload"},
                template=PLOTLY_TEMPLATE, barmode="stack",
            )
            fig.update_layout(height=350, margin=dict(l=40, r=20, t=50, b=40),
                              legend=dict(orientation="h", y=1.12, x=0.5, xanchor="center"))
            st.plotly_chart(fig, use_container_width=True)

    with col_right:
        st.markdown("#### Cloud Distribution")

        cloud_agg = team_df.groupby("cloud").agg(
            total_gpus=("total_gpus", "sum"),
            avg_util=("utilization_pct", "mean"),
        ).reset_index()

        if not cloud_agg.empty:
            fig = px.pie(
                cloud_agg, values="total_gpus", names="cloud",
                color="cloud", color_discrete_map=CLOUD_COLORS,
                title=f"<b>{my_team}</b> — GPU Distribution",
                template=PLOTLY_TEMPLATE, hole=0.4,
            )
            fig.update_traces(textinfo="value+percent", textfont_size=12)
            fig.update_layout(height=350, margin=dict(l=20, r=20, t=50, b=20))
            st.plotly_chart(fig, use_container_width=True)

    # ══════════════════════════════════════════════════════════════════
    # SECTION 3: SCHEDULING ADVISOR
    # ══════════════════════════════════════════════════════════════════

    st.markdown("---")
    st.markdown("#### When Should I Schedule My Job?")
    st.caption("GPU availability by hour and day — darker = busier, lighter = best time to schedule")

    # GPU type filter for scheduling
    gpu_types = sorted(team_hourly["gpu_type"].unique())
    sel_gpu = st.selectbox("GPU Type", ["All"] + gpu_types, index=0, key="sched_gpu")

    hourly_filtered = team_hourly.copy()
    if sel_gpu != "All":
        hourly_filtered = hourly_filtered[hourly_filtered["gpu_type"] == sel_gpu]

    # Build heatmap
    pivot = hourly_filtered.pivot_table(
        index="day_of_week", columns="hour",
        values="utilization_pct", aggfunc="mean",
    )

    if not pivot.empty:
        # Find best scheduling windows
        flat = hourly_filtered.groupby(["day_of_week", "hour"])["utilization_pct"].mean().reset_index()
        best = flat.nsmallest(5, "utilization_pct")
        worst = flat.nlargest(3, "utilization_pct")

        col_heat, col_reco = st.columns([3, 1])

        with col_heat:
            fig = go.Figure(data=go.Heatmap(
                z=pivot.values,
                x=[f"{h:02d}:00" for h in range(24)],
                y=[DAY_NAMES[i] for i in pivot.index],
                colorscale=[
                    [0, "#0d1117"],      # Very low — dark (available)
                    [0.3, "#1a3a2a"],    # Low — dark green
                    [0.5, "#2d6a4f"],    # Medium — green
                    [0.7, "#d4a017"],    # High — yellow
                    [1.0, "#d62728"],    # Very high — red (busy)
                ],
                hovertemplate="<b>%{y} %{x}</b><br>Utilization: %{z:.1f}%<extra></extra>",
                colorbar=dict(title="Util %"),
            ))
            fig.update_layout(
                title=f"<b>GPU Load Heatmap</b> — {sel_gpu if sel_gpu != 'All' else 'All GPUs'}",
                xaxis_title="Hour of Day",
                template=PLOTLY_TEMPLATE, height=350,
                margin=dict(l=60, r=20, t=50, b=40),
                xaxis=dict(tickmode="linear", tick0=0, dtick=2),
            )
            st.plotly_chart(fig, use_container_width=True)

        with col_reco:
            st.markdown("**Best times:**")
            for _, row in best.iterrows():
                d = DAY_NAMES[int(row["day_of_week"])]
                h = int(row["hour"])
                u = row["utilization_pct"]
                st.markdown(f'<span style="color:#2ca02c">●</span> {d} {h:02d}:00 ({u:.0f}%)', unsafe_allow_html=True)

            st.markdown("")
            st.markdown("**Avoid:**")
            for _, row in worst.iterrows():
                d = DAY_NAMES[int(row["day_of_week"])]
                h = int(row["hour"])
                u = row["utilization_pct"]
                st.markdown(f'<span style="color:#d62728">●</span> {d} {h:02d}:00 ({u:.0f}%)', unsafe_allow_html=True)

    # ══════════════════════════════════════════════════════════════════
    # SECTION 4: EFFICIENCY DETAILS TABLE
    # ══════════════════════════════════════════════════════════════════

    st.markdown("---")
    st.markdown("#### Allocation Details")

    detail = team_df.groupby(["gpu_type", "cloud", "workload_type"]).agg(
        total_gpus=("total_gpus", "sum"),
        allocated_gpus=("allocated_gpus", "sum"),
        used_pct=("used_pct", "mean"),
        utilization_pct=("utilization_pct", "mean"),
    ).reset_index()
    detail["waste_gap"] = (detail["used_pct"] - detail["utilization_pct"]).round(1)
    detail = detail.round(1)
    detail["total_gpus"] = detail["total_gpus"].astype(int)
    detail["allocated_gpus"] = detail["allocated_gpus"].astype(int)
    detail = detail.sort_values("waste_gap", ascending=False)

    # Color-code the waste column
    def highlight_waste(val):
        if val > 30:
            return "color: #d62728; font-weight: bold"
        elif val > 15:
            return "color: #ff7f0e"
        return "color: #2ca02c"

    styled = detail.style.map(highlight_waste, subset=["waste_gap"])
    st.dataframe(
        detail,
        use_container_width=True,
        hide_index=True,
        column_config={
            "gpu_type": "GPU Type",
            "cloud": "Cloud",
            "workload_type": "Workload",
            "total_gpus": st.column_config.NumberColumn("Total", format="%d"),
            "allocated_gpus": st.column_config.NumberColumn("Allocated", format="%d"),
            "used_pct": st.column_config.ProgressColumn("Used %", min_value=0, max_value=100, format="%.1f%%"),
            "utilization_pct": st.column_config.ProgressColumn("Util %", min_value=0, max_value=100, format="%.1f%%"),
            "waste_gap": st.column_config.NumberColumn("Waste %", format="%.1f%%"),
        },
    )

    # ══════════════════════════════════════════════════════════════════
    # SECTION 5: COMPARE WITH OTHER TEAMS
    # ══════════════════════════════════════════════════════════════════

    st.markdown("---")
    st.markdown("#### How Does My Team Compare?")

    team_compare = all_gpu_df.groupby("team").agg(
        total_gpus=("total_gpus", "sum"),
        avg_used=("used_pct", "mean"),
        avg_util=("utilization_pct", "mean"),
    ).reset_index()
    team_compare["waste_gap"] = (team_compare["avg_used"] - team_compare["avg_util"]).round(1)
    team_compare = team_compare.round(1)

    fig = go.Figure()

    colors = ["#1f77b4" if t != my_team else "#ff7f0e" for t in team_compare["team"]]

    fig.add_trace(go.Bar(
        x=team_compare["team"], y=team_compare["avg_util"],
        name="Utilization %", marker_color=colors,
        text=[f"{v:.0f}%" for v in team_compare["avg_util"]],
        textposition="outside",
    ))
    fig.add_trace(go.Scatter(
        x=team_compare["team"], y=team_compare["avg_used"],
        name="Used % (allocation)", mode="markers+lines",
        marker=dict(size=12, color="white", line=dict(width=2, color="steelblue")),
        line=dict(dash="dash", color="steelblue"),
    ))

    fig.update_layout(
        title="<b>Team Utilization Comparison</b> — your team highlighted",
        yaxis_title="Percentage %",
        template=PLOTLY_TEMPLATE, height=350,
        margin=dict(l=40, r=20, t=50, b=40),
        legend=dict(orientation="h", y=1.12, x=0.5, xanchor="center"),
        showlegend=True,
    )
    st.plotly_chart(fig, use_container_width=True)
