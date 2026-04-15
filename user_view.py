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

PLOTLY_TEMPLATE = "plotly_dark"

CLOUD_COLORS = {
    "AWS": "#FF9900",
    "GCP": "#34A853",
    "IBM Cloud": "#0F62FE",
}

PRIORITY_COLORS = {
    "committed": "#1f77b4",
    "on-demand": "#ff7f0e",
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
    # SECTION 2: GPU ALLOCATION BREAKDOWN
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

    styled = detail.style.applymap(highlight_waste, subset=["waste_gap"])
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
