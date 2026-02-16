"""
Executive GPU Dashboard
=======================
Leadership-ready organizational view of GPU capacity and efficiency.

Focus: Committed GPUs only
Scope: Cross-cluster, multi-cloud aggregation
Audience: Directors, FinOps, Platform Leadership

In production, data would come from Prometheus/Thanos metrics.
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta

# ============================================================================
# PAGE CONFIG
# ============================================================================

st.set_page_config(
    page_title="Executive GPU Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Dark theme for Plotly
PLOTLY_TEMPLATE = "plotly_dark"

# Consistent cloud colors
CLOUD_COLORS = {
    "AWS": "#FF9900",      # Orange
    "GCP": "#34A853",      # Green
    "IBM Cloud": "#0F62FE" # Blue
}

# ============================================================================
# DATA SIMULATION
# ============================================================================

@st.cache_data
def generate_all_gpu_data():
    """
    Simulate GPU data across all workload types (committed, on-demand, spot).
    In production: Query Prometheus for GPU metrics with workload_type labels.
    """
    np.random.seed(42)
    
    clouds = ["AWS", "GCP", "IBM Cloud"]
    gpu_types = ["L4", "T4", "A100-40GB", "A100-80GB", "H100", "H200", "B200"]
    teams = ["ML Platform", "AI Research", "Data Science", "Engineering", "Customer Analytics"]
    workload_types = ["committed", "on-demand", "spot"]
    
    # GPU type availability weights (some GPUs rarer than others)
    gpu_weights = {
        "L4": 1.0,
        "T4": 1.0,
        "A100-40GB": 0.8,
        "A100-80GB": 0.7,
        "H100": 0.5,
        "H200": 0.3,
        "B200": 0.2
    }
    
    data = []
    
    for cloud in clouds:
        for gpu_type in gpu_types:
            # Skip some GPU types in some clouds for realism
            if np.random.random() > gpu_weights[gpu_type]:
                continue
                
            for team in teams:
                for workload_type in workload_types:
                    # Smaller numbers, more realistic
                    if gpu_type in ["L4", "T4"]:
                        num_gpus = np.random.randint(4, 16)
                    elif gpu_type in ["A100-40GB", "A100-80GB"]:
                        num_gpus = np.random.randint(2, 12)
                    elif gpu_type == "H100":
                        num_gpus = np.random.randint(1, 8)
                    elif gpu_type == "H200":
                        num_gpus = np.random.randint(1, 6)
                    else:  # B200
                        num_gpus = np.random.randint(1, 4)
                    
                    # Allocation based on workload type
                    if workload_type == "committed":
                        # Committed: 60-85% used (NOT 100%)
                        allocated = int(num_gpus * np.random.uniform(0.6, 0.85))
                        utilization = np.random.uniform(30, 75)
                    elif workload_type == "on-demand":
                        # On-demand: 95-100% used
                        allocated = int(num_gpus * np.random.uniform(0.95, 1.0))
                        utilization = np.random.uniform(40, 80)
                    else:  # spot
                        # Spot: 95-100% used
                        allocated = int(num_gpus * np.random.uniform(0.95, 1.0))
                        utilization = np.random.uniform(50, 85)
                    
                    used_pct = (allocated / num_gpus) * 100
                    idle_pct = 100 - used_pct
                    
                    data.append({
                        "cloud": cloud,
                        "gpu_type": gpu_type,
                        "team": team,
                        "workload_type": workload_type,
                        "total_gpus": num_gpus,
                        "allocated_gpus": allocated,
                        "used_pct": used_pct,
                        "utilization_pct": utilization,
                        "idle_pct": idle_pct
                    })
    
    return pd.DataFrame(data)


@st.cache_data
def generate_30day_timeseries():
    """
    Simulate 30 days of daily organizational metrics by workload type.
    In production: Query Prometheus range queries for historical data.
    """
    np.random.seed(45)
    
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)
    
    dates = pd.date_range(start=start_date, end=end_date, freq='D')
    workload_types = ["committed", "on-demand", "spot"]
    
    data = []
    for date in dates:
        day_of_week = date.dayofweek  # 0=Monday, 6=Sunday
        weekend_factor = 0.6 if day_of_week >= 5 else 1.0
        
        for workload_type in workload_types:
            if workload_type == "committed":
                # Committed: 60-75% used
                used_pct = np.random.uniform(60, 75) * weekend_factor
                utilization_pct = np.random.uniform(35, 55) * weekend_factor
            elif workload_type == "on-demand":
                # On-demand: ~100% used
                used_pct = np.random.uniform(95, 100)
                utilization_pct = np.random.uniform(45, 65) * weekend_factor
            else:  # spot
                # Spot: ~100% used
                used_pct = np.random.uniform(95, 100)
                utilization_pct = np.random.uniform(50, 70) * weekend_factor
            
            data.append({
                "date": date,
                "workload_type": workload_type,
                "used_pct": used_pct,
                "utilization_pct": utilization_pct,
                "day_of_week": day_of_week
            })
    
    return pd.DataFrame(data)


@st.cache_data
def generate_hourly_usage_patterns():
    """
    Simulate hourly usage patterns by team and GPU type.
    In production: Query Prometheus for hourly GPU metrics.
    """
    np.random.seed(100)
    
    teams = ["ML Platform", "AI Research", "Data Science", "Engineering", "Customer Analytics"]
    gpu_types = ["L4", "T4", "A100-40GB", "A100-80GB", "H100", "H200", "B200"]
    
    data = []
    
    for day_of_week in range(7):  # 0=Monday, 6=Sunday
        for hour in range(24):
            for team in teams:
                for gpu_type in gpu_types:
                    # Simulate hourly patterns
                    # Work hours (9-17) have higher usage
                    is_work_hours = 9 <= hour <= 17
                    is_weekday = day_of_week < 5
                    
                    # Base GPU hours and utilization
                    if is_weekday and is_work_hours:
                        base_gpu_hours = np.random.uniform(80, 150)
                        base_utilization = np.random.uniform(50, 75)
                    elif is_weekday:
                        base_gpu_hours = np.random.uniform(40, 80)
                        base_utilization = np.random.uniform(30, 50)
                    else:  # weekend
                        base_gpu_hours = np.random.uniform(20, 60)
                        base_utilization = np.random.uniform(20, 40)
                    
                    # Add team-specific variance
                    team_factor = 1.0 + (hash(team) % 30) / 100
                    gpu_hours = base_gpu_hours * team_factor
                    utilization = base_utilization * team_factor
                    
                    data.append({
                        "team": team,
                        "gpu_type": gpu_type,
                        "day_of_week": day_of_week,
                        "hour": hour,
                        "gpu_hours": gpu_hours,
                        "utilization_pct": min(85, utilization)
                    })
    
    return pd.DataFrame(data)


# ============================================================================
# VISUALIZATION FUNCTIONS
# ============================================================================

def plot_committed_inventory_by_type_and_cloud(df):
    """
    Graph 1: Committed GPU Inventory by Type and Cloud
    Grouped vertical bar chart
    """
    agg = df.groupby(["gpu_type", "cloud"])["total_gpus"].sum().reset_index()
    
    # Define GPU type order (low-end to high-end)
    gpu_order = ["L4", "T4", "A100-40GB", "A100-80GB", "H100", "H200", "B200"]
    
    # Filter to only existing GPU types and set order
    existing_gpus = [g for g in gpu_order if g in agg["gpu_type"].unique()]
    agg["gpu_type"] = pd.Categorical(agg["gpu_type"], categories=existing_gpus, ordered=True)
    agg = agg.sort_values("gpu_type")
    
    # Calculate totals per GPU type for annotation
    totals = agg.groupby("gpu_type")["total_gpus"].sum().reset_index()
    totals_dict = dict(zip(totals["gpu_type"], totals["total_gpus"]))
    
    fig = px.bar(
        agg,
        x="gpu_type",
        y="total_gpus",
        color="cloud",
        title="<b>Committed GPU Inventory by Type and Cloud</b>",
        labels={"total_gpus": "GPU Count", "gpu_type": "GPU Type"},
        template=PLOTLY_TEMPLATE,
        color_discrete_map=CLOUD_COLORS,
        text="total_gpus",
        barmode="group"
    )
    
    fig.update_traces(textposition="outside", textfont_size=11)
    
    # Add total annotations above each group - positioned better
    max_y = agg["total_gpus"].max()
    for gpu_type, total in totals_dict.items():
        fig.add_annotation(
            x=gpu_type,
            y=max_y * 1.15,
            text=f"<b>Σ {total}</b>",
            showarrow=False,
            font=dict(size=13, color="lightgray"),
            xanchor="center"
        )
    
    fig.update_layout(
        height=500,
        title_font_size=16,
        xaxis_title="GPU Type",
        yaxis_title="GPU Count",
        xaxis=dict(categoryorder="array", categoryarray=existing_gpus),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            title="Cloud Provider"
        )
    )
    
    return fig


def plot_30day_used_vs_utilization_trend(df):
    """
    Graph 2: 30-Day Organizational Used vs Utilization Trend (Committed Only)
    Dual line chart
    """
    # Filter for committed only
    committed = df[df["workload_type"] == "committed"]
    
    fig = go.Figure()
    
    # Used % line (solid)
    fig.add_trace(go.Scatter(
        x=committed["date"],
        y=committed["used_pct"],
        mode="lines",
        name="Used %",
        line=dict(color="steelblue", width=3),
        hovertemplate="Used: %{y:.1f}%<extra></extra>"
    ))
    
    # Utilization % line (dashed)
    fig.add_trace(go.Scatter(
        x=committed["date"],
        y=committed["utilization_pct"],
        mode="lines",
        name="Utilization %",
        line=dict(color="lightblue", width=3, dash="dash"),
        hovertemplate="Utilization: %{y:.1f}%<extra></extra>"
    ))
    
    fig.update_layout(
        title="<b>30-Day Efficiency Trend (Committed)</b>",
        xaxis_title="Date",
        yaxis_title="Percentage (%)",
        template=PLOTLY_TEMPLATE,
        height=500,
        title_font_size=16,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ),
        hovermode="x unified"
    )
    
    return fig


def plot_used_trend_by_team_all_gpus(all_df, timeseries_df):
    """
    Used % Trend by Team - Committed Only, All GPU Types
    Separate line per team + average line
    """
    teams = sorted(all_df["team"].unique())
    dates = sorted(timeseries_df["date"].unique())
    
    fig = go.Figure()
    
    all_team_data = []
    
    # Create a line for each team
    for idx, team in enumerate(teams):
        np.random.seed(70 + idx)
        
        # Get team's average used % (committed only, all GPU types)
        team_avg_used = all_df[
            (all_df["team"] == team) & 
            (all_df["workload_type"] == "committed")
        ]["used_pct"].mean()
        
        # Generate team-specific trend
        team_used = []
        for date in dates:
            day_of_week = pd.Timestamp(date).dayofweek
            weekend_factor = 0.85 if day_of_week >= 5 else 1.0
            used = team_avg_used * weekend_factor + np.random.normal(0, 3)
            team_used.append(max(50, min(90, used)))
        
        all_team_data.append(team_used)
        
        fig.add_trace(go.Scatter(
            x=dates,
            y=team_used,
            mode="lines",
            name=team,
            line=dict(width=2),
            hovertemplate=f"{team}: %{{y:.1f}}%<extra></extra>"
        ))
    
    # Add average line (thick, dashed, white)
    avg_data = np.mean(all_team_data, axis=0)
    fig.add_trace(go.Scatter(
        x=dates,
        y=avg_data,
        mode="lines",
        name="⬤ Average",
        line=dict(color="white", width=4, dash="dash"),
        hovertemplate="Average: %{y:.1f}%<extra></extra>"
    ))
    
    fig.update_layout(
        title="<b>Used % by Team - All GPU Types (Committed Only)</b>",
        xaxis_title="Date",
        yaxis_title="Used %",
        template=PLOTLY_TEMPLATE,
        height=450,
        title_font_size=18,
        hovermode="x unified",
        legend=dict(
            orientation="v",
            yanchor="middle",
            y=0.5,
            xanchor="left",
            x=1.02
        )
    )
    
    return fig


def plot_used_by_team_per_gpu_type(all_df, timeseries_df, gpu_type):
    """
    Used % by Team for specific GPU Type (Committed Only)
    One line per team + average line
    """
    teams = sorted(all_df["team"].unique())
    dates = sorted(timeseries_df["date"].unique())
    
    fig = go.Figure()
    
    all_team_data = []
    
    # Create a line for each team
    for idx, team in enumerate(teams):
        np.random.seed(100 + idx + hash(gpu_type) % 100)
        
        # Get team's used % for this GPU type (committed only)
        team_gpu_data = all_df[
            (all_df["team"] == team) & 
            (all_df["gpu_type"] == gpu_type) &
            (all_df["workload_type"] == "committed")
        ]
        
        if team_gpu_data.empty:
            continue
        
        team_avg_used = team_gpu_data["used_pct"].mean()
        
        # Generate team-specific trend
        team_used = []
        for date in dates:
            day_of_week = pd.Timestamp(date).dayofweek
            weekend_factor = 0.85 if day_of_week >= 5 else 1.0
            used = team_avg_used * weekend_factor + np.random.normal(0, 3)
            team_used.append(max(50, min(90, used)))
        
        all_team_data.append(team_used)
        
        fig.add_trace(go.Scatter(
            x=dates,
            y=team_used,
            mode="lines",
            name=team,
            line=dict(width=1.5),
            hovertemplate=f"{team}: %{{y:.1f}}%<extra></extra>"
        ))
    
    # Add average line
    if all_team_data:
        avg_data = np.mean(all_team_data, axis=0)
        fig.add_trace(go.Scatter(
            x=dates,
            y=avg_data,
            mode="lines",
            name="⬤ Average",
            line=dict(color="white", width=3, dash="dash"),
            hovertemplate="Average: %{y:.1f}%<extra></extra>"
        ))
    
    fig.update_layout(
        title=f"<b>{gpu_type} - Used % by Team</b>",
        xaxis_title="Date",
        yaxis_title="Used %",
        template=PLOTLY_TEMPLATE,
        height=350,
        title_font_size=16,
        hovermode="x unified",
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        )
    )
    
    return fig


def plot_utilization_trend_by_team_all_gpus(all_df, timeseries_df):
    """
    Utilization % Trend by Team - ALL GPU Types aggregated
    Committed, On-Demand, Spot combined
    """
    teams = sorted(all_df["team"].unique())
    dates = sorted(timeseries_df["date"].unique())
    
    fig = go.Figure()
    
    all_team_data = []
    
    # Create a line for each team
    for idx, team in enumerate(teams):
        np.random.seed(80 + idx)
        
        # Get team's average utilization across all workload types
        team_avg_util = all_df[all_df["team"] == team]["utilization_pct"].mean()
        
        # Generate team-specific trend
        team_util = []
        for date in dates:
            day_of_week = pd.Timestamp(date).dayofweek
            weekend_factor = 0.6 if day_of_week >= 5 else 1.0
            util = team_avg_util * weekend_factor + np.random.normal(0, 4)
            team_util.append(max(25, min(80, util)))
        
        all_team_data.append(team_util)
        
        fig.add_trace(go.Scatter(
            x=dates,
            y=team_util,
            mode="lines",
            name=team,
            line=dict(width=2),
            hovertemplate=f"{team}: %{{y:.1f}}%<extra></extra>"
        ))
    
    # Add average line (thick, dashed, white)
    avg_data = np.mean(all_team_data, axis=0)
    fig.add_trace(go.Scatter(
        x=dates,
        y=avg_data,
        mode="lines",
        name="⬤ Average",
        line=dict(color="white", width=4, dash="dash"),
        hovertemplate="Average: %{y:.1f}%<extra></extra>"
    ))
    
    fig.update_layout(
        title="<b>Utilization % by Team - All GPU Types</b>",
        xaxis_title="Date",
        yaxis_title="Utilization %",
        template=PLOTLY_TEMPLATE,
        height=450,
        title_font_size=18,
        hovermode="x unified",
        legend=dict(
            orientation="v",
            yanchor="middle",
            y=0.5,
            xanchor="left",
            x=1.02
        )
    )
    
    return fig


def plot_utilization_by_team_per_gpu_type(all_df, timeseries_df, gpu_type):
    """
    Utilization % by Team for specific GPU Type
    One line per team + average line
    """
    teams = sorted(all_df["team"].unique())
    dates = sorted(timeseries_df["date"].unique())
    
    fig = go.Figure()
    
    all_team_data = []
    
    # Create a line for each team
    for idx, team in enumerate(teams):
        np.random.seed(90 + idx + hash(gpu_type) % 100)
        
        # Get team's utilization for this GPU type
        team_gpu_data = all_df[
            (all_df["team"] == team) & 
            (all_df["gpu_type"] == gpu_type)
        ]
        
        if team_gpu_data.empty:
            continue
        
        team_avg_util = team_gpu_data["utilization_pct"].mean()
        
        # Generate team-specific trend
        team_util = []
        for date in dates:
            day_of_week = pd.Timestamp(date).dayofweek
            weekend_factor = 0.6 if day_of_week >= 5 else 1.0
            util = team_avg_util * weekend_factor + np.random.normal(0, 5)
            team_util.append(max(20, min(85, util)))
        
        all_team_data.append(team_util)
        
        fig.add_trace(go.Scatter(
            x=dates,
            y=team_util,
            mode="lines",
            name=team,
            line=dict(width=1.5),
            hovertemplate=f"{team}: %{{y:.1f}}%<extra></extra>"
        ))
    
    # Add average line
    if all_team_data:
        avg_data = np.mean(all_team_data, axis=0)
        fig.add_trace(go.Scatter(
            x=dates,
            y=avg_data,
            mode="lines",
            name="⬤ Average",
            line=dict(color="white", width=3, dash="dash"),
            hovertemplate="Average: %{y:.1f}%<extra></extra>"
        ))
    
    fig.update_layout(
        title=f"<b>{gpu_type} - Utilization % by Team</b>",
        xaxis_title="Date",
        yaxis_title="Utilization %",
        template=PLOTLY_TEMPLATE,
        height=350,
        title_font_size=16,
        hovermode="x unified",
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        )
    )
    
    return fig


def plot_team_utilization_by_gpu_type(all_df):
    """
    Heatmap: Team × GPU Type Utilization
    Shows which teams are inefficient with which GPU types
    """
    # Aggregate utilization by team and GPU type
    pivot = all_df.pivot_table(
        index="team",
        columns="gpu_type",
        values="utilization_pct",
        aggfunc="mean"
    )
    
    # Define GPU order
    gpu_order = ["L4", "T4", "A100-40GB", "A100-80GB", "H100", "H200", "B200"]
    existing_gpus = [g for g in gpu_order if g in pivot.columns]
    pivot = pivot[existing_gpus]
    
    fig = go.Figure(data=go.Heatmap(
        z=pivot.values,
        x=pivot.columns,
        y=pivot.index,
        colorscale="RdYlGn",  # Red = low (wasteful), Green = high (efficient)
        text=pivot.values.round(1),
        texttemplate="%{text}%",
        textfont={"size": 11},
        hovertemplate="<b>%{y}</b><br>%{x}: %{z:.1f}%<extra></extra>",
        colorbar=dict(title="Utilization %")
    ))
    
    fig.update_layout(
        title="<b>Team Efficiency by GPU Type</b>",
        xaxis_title="GPU Type",
        yaxis_title="Team",
        template=PLOTLY_TEMPLATE,
        height=450,
        title_font_size=18
    )
    
    return fig


def plot_team_gpu_waste_analysis(all_df):
    """
    Bar chart: Shows which teams have lowest utilization by GPU type
    Helps identify wasteful allocation
    """
    # Get teams with utilization by GPU type
    agg = all_df.groupby(["team", "gpu_type"]).agg({
        "utilization_pct": "mean",
        "total_gpus": "sum"
    }).reset_index()
    
    # Find lowest utilization per GPU type
    fig = px.bar(
        agg,
        x="gpu_type",
        y="utilization_pct",
        color="team",
        title="<b>Utilization by GPU Type per Team</b>",
        labels={"utilization_pct": "Avg Utilization %", "gpu_type": "GPU Type"},
        template=PLOTLY_TEMPLATE,
        barmode="group"
    )
    
    fig.update_layout(
        height=450,
        title_font_size=18,
        xaxis_tickangle=45
    )
    
    return fig


def plot_team_gpu_breakdown_table(all_df):
    """
    Detailed table: Team × GPU Type × Workload Type × Cloud
    Shows WHO uses WHAT, HOW MUCH, and WHERE
    """
    # Aggregate GPU hours (simulate 30-day total)
    # GPU hours = total_gpus × allocated % × 24 hours × 30 days
    all_df_copy = all_df.copy()
    all_df_copy["gpu_hours_30d"] = (
        all_df_copy["total_gpus"] * 
        (all_df_copy["used_pct"] / 100) * 
        24 * 30
    )
    
    summary = all_df_copy.groupby(["team", "gpu_type", "workload_type", "cloud"]).agg({
        "gpu_hours_30d": "sum",
        "utilization_pct": "mean",
        "total_gpus": "sum"
    }).reset_index()
    
    summary.columns = ["Team", "GPU Type", "Workload Type", "Cloud", "GPU Hours (30d)", "Avg Utilization %", "Total GPUs"]
    summary["GPU Hours (30d)"] = summary["GPU Hours (30d)"].round(0).astype(int)
    summary["Avg Utilization %"] = summary["Avg Utilization %"].round(1)
    
    # Sort by GPU hours descending
    summary = summary.sort_values("GPU Hours (30d)", ascending=False)
    
    return summary


def plot_sankey_team_gpu_flow(all_df):
    """
    Sankey diagram: Team → GPU Type → Workload Type → Cloud
    Shows flow of GPU usage
    """
    # Calculate GPU hours
    all_df_copy = all_df.copy()
    all_df_copy["gpu_hours"] = (
        all_df_copy["total_gpus"] * 
        (all_df_copy["used_pct"] / 100) * 
        24 * 30
    )
    
    # Aggregate
    agg = all_df_copy.groupby(["team", "gpu_type", "workload_type", "cloud"])["gpu_hours"].sum().reset_index()
    
    # Build Sankey
    labels = []
    label_dict = {}
    
    # Add all unique values
    for col in ["team", "gpu_type", "workload_type", "cloud"]:
        for val in agg[col].unique():
            if val not in label_dict:
                label_dict[val] = len(labels)
                labels.append(val)
    
    # Create links
    source = []
    target = []
    value = []
    
    # Team → GPU Type
    for _, row in agg.groupby(["team", "gpu_type"])["gpu_hours"].sum().reset_index().iterrows():
        source.append(label_dict[row["team"]])
        target.append(label_dict[row["gpu_type"]])
        value.append(row["gpu_hours"])
    
    # GPU Type → Workload Type
    for _, row in agg.groupby(["gpu_type", "workload_type"])["gpu_hours"].sum().reset_index().iterrows():
        source.append(label_dict[row["gpu_type"]])
        target.append(label_dict[row["workload_type"]])
        value.append(row["gpu_hours"])
    
    # Workload Type → Cloud
    for _, row in agg.groupby(["workload_type", "cloud"])["gpu_hours"].sum().reset_index().iterrows():
        source.append(label_dict[row["workload_type"]])
        target.append(label_dict[row["cloud"]])
        value.append(row["gpu_hours"])
    
    fig = go.Figure(data=[go.Sankey(
        node=dict(
            pad=15,
            thickness=20,
            line=dict(color="white", width=0.5),
            label=labels
        ),
        link=dict(
            source=source,
            target=target,
            value=value
        )
    )])
    
    fig.update_layout(
        title="<b>GPU Usage Flow: Team → GPU Type → Workload → Cloud</b>",
        template=PLOTLY_TEMPLATE,
        height=600,
        title_font_size=18
    )
    
    return fig


def plot_gpu_hours_by_team_stacked(all_df):
    """
    Stacked bar: GPU Hours by Team
    Split by GPU Type and Workload Type
    """
    # Calculate GPU hours
    all_df_copy = all_df.copy()
    all_df_copy["gpu_hours"] = (
        all_df_copy["total_gpus"] * 
        (all_df_copy["used_pct"] / 100) * 
        24 * 30
    )
    
    # Create combined label for stacking
    all_df_copy["gpu_workload"] = all_df_copy["gpu_type"] + " (" + all_df_copy["workload_type"] + ")"
    
    agg = all_df_copy.groupby(["team", "gpu_workload"])["gpu_hours"].sum().reset_index()
    
    fig = px.bar(
        agg,
        x="team",
        y="gpu_hours",
        color="gpu_workload",
        title="<b>GPU Hours by Team (30-Day Total)</b>",
        labels={"gpu_hours": "GPU Hours", "team": "Team"},
        template=PLOTLY_TEMPLATE,
        text="gpu_hours"
    )
    
    fig.update_traces(textposition="inside", texttemplate="%{text:.0f}")
    fig.update_layout(
        height=450,
        title_font_size=18,
        xaxis_tickangle=45,
        legend=dict(
            orientation="v",
            yanchor="top",
            y=1,
            xanchor="left",
            x=1.02,
            title="GPU (Workload)"
        )
    )
    
    return fig


def plot_team_cloud_workload_heatmap(all_df):
    """
    Heatmap: Team × Cloud, colored by workload type distribution
    """
    # Calculate GPU hours by team and cloud
    all_df_copy = all_df.copy()
    all_df_copy["gpu_hours"] = (
        all_df_copy["total_gpus"] * 
        (all_df_copy["used_pct"] / 100) * 
        24 * 30
    )
    
    pivot = all_df_copy.pivot_table(
        index="team",
        columns="cloud",
        values="gpu_hours",
        aggfunc="sum",
        fill_value=0
    )
    
    fig = px.imshow(
        pivot,
        title="<b>Team × Cloud GPU Hours (30-Day Total)</b>",
        labels=dict(x="Cloud", y="Team", color="GPU Hours"),
        template=PLOTLY_TEMPLATE,
        color_continuous_scale="Blues",
        aspect="auto",
        text_auto=".0f"
    )
    
    fig.update_layout(height=400, title_font_size=18)
    
    return fig


def plot_daily_team_gpu_usage(all_df, timeseries_df, gpu_type, cloud):
    """
    Small chart: Daily GPU hours by team for specific GPU type and cloud
    Shows which team uses the most each day
    """
    # Filter by GPU type and cloud
    filtered = all_df[
        (all_df["gpu_type"] == gpu_type) &
        (all_df["cloud"] == cloud)
    ]
    
    if filtered.empty:
        return None
    
    dates = sorted(timeseries_df["date"].unique())
    teams = sorted(filtered["team"].unique())
    
    fig = go.Figure()
    
    # For each team, generate daily GPU hours
    for team in teams:
        np.random.seed(hash(team + gpu_type + cloud) % 1000)
        
        team_data = filtered[filtered["team"] == team]
        
        if team_data.empty:
            continue
        
        # Calculate average GPU hours for this team
        avg_gpu_hours = (
            team_data["total_gpus"].sum() * 
            (team_data["used_pct"].mean() / 100) * 
            24
        )
        
        # Generate daily pattern
        daily_hours = []
        for date in dates:
            day_of_week = pd.Timestamp(date).dayofweek
            weekend_factor = 0.5 if day_of_week >= 5 else 1.0
            hours = avg_gpu_hours * weekend_factor + np.random.normal(0, avg_gpu_hours * 0.1)
            daily_hours.append(max(0, hours))
        
        fig.add_trace(go.Scatter(
            x=dates,
            y=daily_hours,
            mode="lines",
            name=team,
            stackgroup="one",
            hovertemplate=f"{team}: %{{y:.0f}} hrs<extra></extra>"
        ))
    
    fig.update_layout(
        title=f"<b>{gpu_type}</b><br><sub>{cloud}</sub>",
        xaxis_title="",
        yaxis_title="GPU Hours",
        template=PLOTLY_TEMPLATE,
        height=300,
        title_font_size=14,
        hovermode="x unified",
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=-0.3,
            xanchor="center",
            x=0.5,
            font=dict(size=9)
        ),
        margin=dict(t=60, b=80)
    )
    
    return fig


def plot_team_efficiency_scatter(committed_df):
    """
    Graph 3: Team Efficiency - Allocated vs Utilization
    Bubble/Scatter chart
    """
    # Aggregate by team (30-day average simulation)
    agg = committed_df.groupby("team").agg({
        "used_pct": "mean",
        "utilization_pct": "mean",
        "total_gpus": "sum",
        "idle_pct": "mean"
    }).reset_index()
    
    fig = px.scatter(
        agg,
        x="used_pct",
        y="utilization_pct",
        size="total_gpus",
        color="idle_pct",
        hover_data=["team"],
        title="<b>Team Efficiency: Allocated vs Utilization (30-Day Average)</b>",
        labels={
            "used_pct": "Allocated % (Used)",
            "utilization_pct": "Avg Utilization %",
            "idle_pct": "Idle %",
            "total_gpus": "Total GPUs"
        },
        template=PLOTLY_TEMPLATE,
        color_continuous_scale=["green", "yellow", "red"],
        size_max=60
    )
    
    # Add team labels
    for _, row in agg.iterrows():
        fig.add_annotation(
            x=row["used_pct"],
            y=row["utilization_pct"],
            text=row["team"],
            showarrow=False,
            yshift=10,
            font=dict(size=10, color="white")
        )
    
    fig.update_layout(
        height=500,
        title_font_size=16,
        coloraxis_colorbar=dict(title="Idle %")
    )
    
    return fig


def plot_used_vs_utilization_by_workload(df):
    """
    Graph: Used vs Utilization by Workload Type (30-Day Average)
    Grouped vertical bar chart with color families per workload type
    """
    # Aggregate by workload type
    agg = df.groupby("workload_type").agg({
        "used_pct": "mean",
        "utilization_pct": "mean"
    }).reset_index()
    
    # Order workloads
    workload_order = ["committed", "on-demand", "spot"]
    agg["workload_type"] = pd.Categorical(agg["workload_type"], categories=workload_order, ordered=True)
    agg = agg.sort_values("workload_type")
    
    # Create figure with grouped bars
    fig = go.Figure()
    
    # Committed - Blue family
    committed_data = agg[agg["workload_type"] == "committed"]
    if not committed_data.empty:
        fig.add_trace(go.Bar(
            x=["Committed"],
            y=committed_data["used_pct"].values,
            name="Used % (Committed)",
            marker_color="#1f77b4",  # Dark blue
            text=[f"{v:.1f}%" for v in committed_data["used_pct"].values],
            textposition="outside",
            offsetgroup=0,
            width=0.35
        ))
        fig.add_trace(go.Bar(
            x=["Committed"],
            y=committed_data["utilization_pct"].values,
            name="Utilization % (Committed)",
            marker_color="#7fb3d5",  # Light blue
            text=[f"{v:.1f}%" for v in committed_data["utilization_pct"].values],
            textposition="outside",
            offsetgroup=1,
            width=0.35
        ))
    
    # On-Demand - Orange family
    on_demand_data = agg[agg["workload_type"] == "on-demand"]
    if not on_demand_data.empty:
        fig.add_trace(go.Bar(
            x=["On-Demand"],
            y=on_demand_data["used_pct"].values,
            name="Used % (On-Demand)",
            marker_color="#ff7f0e",  # Dark orange
            text=[f"{v:.1f}%" for v in on_demand_data["used_pct"].values],
            textposition="outside",
            offsetgroup=0,
            width=0.35,
            showlegend=False
        ))
        fig.add_trace(go.Bar(
            x=["On-Demand"],
            y=on_demand_data["utilization_pct"].values,
            name="Utilization % (On-Demand)",
            marker_color="#ffb366",  # Light orange
            text=[f"{v:.1f}%" for v in on_demand_data["utilization_pct"].values],
            textposition="outside",
            offsetgroup=1,
            width=0.35,
            showlegend=False
        ))
    
    # Spot - Green family
    spot_data = agg[agg["workload_type"] == "spot"]
    if not spot_data.empty:
        fig.add_trace(go.Bar(
            x=["Spot"],
            y=spot_data["used_pct"].values,
            name="Used % (Spot)",
            marker_color="#2ca02c",  # Dark green
            text=[f"{v:.1f}%" for v in spot_data["used_pct"].values],
            textposition="outside",
            offsetgroup=0,
            width=0.35,
            showlegend=False
        ))
        fig.add_trace(go.Bar(
            x=["Spot"],
            y=spot_data["utilization_pct"].values,
            name="Utilization % (Spot)",
            marker_color="#8fce8f",  # Light green
            text=[f"{v:.1f}%" for v in spot_data["utilization_pct"].values],
            textposition="outside",
            offsetgroup=1,
            width=0.35,
            showlegend=False
        ))
    
    fig.update_layout(
        title="<b>Used vs Utilization by Workload Type (30-Day Average)</b>",
        xaxis_title="Workload Type",
        yaxis_title="Percentage (%)",
        template=PLOTLY_TEMPLATE,
        height=450,
        title_font_size=16,
        barmode="group",
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        )
    )
    
    return fig


def plot_metrics_by_weekday_heatmap(timeseries_df):
    """
    Graph 4: Metrics × Weekday Heatmap (Committed only)
    Shows Used %, Utilization %, Idle % across the week
    """
    # Filter for committed only
    committed = timeseries_df[timeseries_df["workload_type"] == "committed"]
    
    # Aggregate by day of week
    agg = committed.groupby("day_of_week").agg({
        "used_pct": "mean",
        "utilization_pct": "mean"
    }).reset_index()
    
    # Calculate idle from used (not utilization)
    agg["idle_pct"] = 100 - agg["used_pct"]
    
    day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    
    # Reshape for heatmap
    pivot_data = []
    for metric, label in [("used_pct", "Used %"), ("utilization_pct", "Utilization %"), ("idle_pct", "Idle %")]:
        row = [agg[agg["day_of_week"] == i][metric].values[0] for i in range(7)]
        pivot_data.append(row)
    
    fig = go.Figure(data=go.Heatmap(
        z=pivot_data,
        x=day_names,
        y=["Used %", "Utilization %", "Idle %"],
        colorscale="RdYlGn",
        text=[[f"{val:.1f}%" for val in row] for row in pivot_data],
        texttemplate="%{text}",
        textfont={"size": 12},
        hovertemplate="<b>%{y}</b><br>%{x}: %{z:.1f}%<extra></extra>",
        colorbar=dict(title="Value (%)")
    ))
    
    fig.update_layout(
        title="<b>Metrics × Weekday Pattern</b>",
        xaxis_title="Day of Week",
        template=PLOTLY_TEMPLATE,
        height=400,
        title_font_size=16
    )
    
    return fig


def plot_dynamic_usage_heatmap(hourly_df, selected_teams, selected_gpu_types, metric):
    """
    Dynamic heatmap: Hour × Day of Week
    Aggregates based on team and GPU type selection
    """
    # Filter data based on selections
    filtered = hourly_df[
        (hourly_df["team"].isin(selected_teams)) &
        (hourly_df["gpu_type"].isin(selected_gpu_types))
    ]
    
    # Select metric column
    metric_col = "gpu_hours" if metric == "GPU Hours" else "utilization_pct"
    
    # Aggregate to hour × day_of_week
    pivot = filtered.pivot_table(
        index="day_of_week",
        columns="hour",
        values=metric_col,
        aggfunc="mean"
    )
    
    # Day names
    day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    pivot.index = [day_names[i] for i in pivot.index]
    
    # Generate dynamic title
    if len(selected_teams) == 1:
        team_label = selected_teams[0]
    elif len(selected_teams) == len(hourly_df["team"].unique()):
        team_label = "All Teams"
    else:
        team_label = f"{len(selected_teams)} Teams"
    
    if len(selected_gpu_types) == 1:
        gpu_label = selected_gpu_types[0]
    elif len(selected_gpu_types) == len(hourly_df["gpu_type"].unique()):
        gpu_label = "All GPU Types"
    else:
        gpu_label = f"{len(selected_gpu_types)} GPU Types"
    
    # Final title
    if team_label == "All Teams" and gpu_label == "All GPU Types":
        title = f"<b>Organizational Usage Pattern (All Teams, All GPU Types)</b>"
    elif team_label != "All Teams" and gpu_label != "All GPU Types":
        title = f"<b>Team {team_label} – {gpu_label} Usage Pattern</b>"
    elif team_label == "All Teams":
        title = f"<b>All Teams – {gpu_label} Usage Pattern</b>"
    else:
        title = f"<b>{team_label} – All GPU Types Usage Pattern</b>"
    
    # Create heatmap
    fig = go.Figure(data=go.Heatmap(
        z=pivot.values,
        x=list(range(24)),
        y=pivot.index,
        colorscale=[[0, "#001f3f"], [0.5, "#4682b4"], [1, "#7FFF00"]],  # Dark blue → Light blue → Green
        hovertemplate="<b>%{y}</b><br>Hour %{x}: %{z:.1f}<extra></extra>",
        colorbar=dict(title=metric)
    ))
    
    fig.update_layout(
        title=title,
        xaxis_title="Hour of Day",
        yaxis_title="Day of Week",
        template=PLOTLY_TEMPLATE,
        height=500,
        title_font_size=18,
        xaxis=dict(
            tickmode="linear",
            tick0=0,
            dtick=2
        )
    )
    
    return fig


def plot_3d_surface_usage_pattern(hourly_df, selected_teams, selected_gpu_types, metric):
    """
    OPTION 1: 3D Surface Plot - Hour × Day × Metric
    Interactive surface showing peaks and valleys of usage
    """
    # Filter data
    filtered = hourly_df[
        (hourly_df["team"].isin(selected_teams)) &
        (hourly_df["gpu_type"].isin(selected_gpu_types))
    ]
    
    # Select metric
    metric_col = "gpu_hours" if metric == "GPU Hours" else "utilization_pct"
    
    # Aggregate to hour × day
    pivot = filtered.pivot_table(
        index="day_of_week",
        columns="hour",
        values=metric_col,
        aggfunc="mean"
    )
    
    day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    
    # Create 3D surface
    fig = go.Figure(data=[go.Surface(
        z=pivot.values,
        x=list(range(24)),
        y=list(range(7)),
        colorscale=[[0, "#001f3f"], [0.5, "#4682b4"], [1, "#7FFF00"]],
        hovertemplate="<b>%{text}</b><br>Hour: %{x}<br>" + metric + ": %{z:.1f}<extra></extra>",
        text=[[day_names[i] for _ in range(24)] for i in range(7)],
        colorbar=dict(title=metric)
    )])
    
    fig.update_layout(
        title=f"<b>3D Surface: {metric} Pattern</b>",
        scene=dict(
            xaxis_title="Hour of Day",
            yaxis=dict(
                title="Day of Week",
                tickmode="array",
                tickvals=list(range(7)),
                ticktext=day_names
            ),
            zaxis_title=metric
        ),
        template=PLOTLY_TEMPLATE,
        height=600,
        title_font_size=18
    )
    
    return fig


def plot_3d_scatter_bubbles(hourly_df, selected_teams, selected_gpu_types):
    """
    OPTION 2: 3D Scatter with Bubbles
    Each point = hour × day × team, size = GPU hours, color = team
    """
    # Filter data
    filtered = hourly_df[
        (hourly_df["team"].isin(selected_teams)) &
        (hourly_df["gpu_type"].isin(selected_gpu_types))
    ]
    
    # Sample data (too many points otherwise)
    sampled = filtered.groupby(["team", "day_of_week", "hour"]).agg({
        "gpu_hours": "mean",
        "utilization_pct": "mean"
    }).reset_index()
    
    day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    sampled["day_name"] = sampled["day_of_week"].apply(lambda x: day_names[x])
    
    fig = px.scatter_3d(
        sampled,
        x="hour",
        y="day_of_week",
        z="utilization_pct",
        size="gpu_hours",
        color="team",
        hover_data=["day_name"],
        title="<b>3D Scatter: Hour × Day × Utilization</b>",
        labels={
            "hour": "Hour of Day",
            "day_of_week": "Day of Week",
            "utilization_pct": "Utilization %",
            "gpu_hours": "GPU Hours"
        },
        template=PLOTLY_TEMPLATE,
        size_max=15
    )
    
    fig.update_layout(
        height=600,
        title_font_size=18,
        scene=dict(
            xaxis_title="Hour of Day",
            yaxis=dict(
                title="Day of Week",
                tickmode="array",
                tickvals=list(range(7)),
                ticktext=day_names
            ),
            zaxis_title="Utilization %"
        )
    )
    
    return fig


def plot_3d_surfaces_per_team(hourly_df, selected_teams, selected_gpu_types, metric):
    """
    OPTION 3: Multiple 3D Surfaces (one per team)
    Each team is a separate surface layer
    """
    # Filter by GPU type
    filtered = hourly_df[
        (hourly_df["team"].isin(selected_teams)) &
        (hourly_df["gpu_type"].isin(selected_gpu_types))
    ]
    
    metric_col = "gpu_hours" if metric == "GPU Hours" else "utilization_pct"
    
    fig = go.Figure()
    
    # Create a surface for each team
    for idx, team in enumerate(selected_teams):
        team_data = filtered[filtered["team"] == team]
        
        pivot = team_data.pivot_table(
            index="day_of_week",
            columns="hour",
            values=metric_col,
            aggfunc="mean"
        )
        
        if pivot.empty:
            continue
        
        # Add team surface with slight offset
        fig.add_trace(go.Surface(
            z=pivot.values + (idx * 5),  # Slight offset per team
            x=list(range(24)),
            y=list(range(7)),
            name=team,
            showscale=(idx == 0),
            colorscale=[[0, "#001f3f"], [0.5, "#4682b4"], [1, "#7FFF00"]],
            opacity=0.8,
            hovertemplate=f"<b>{team}</b><br>Hour: %{{x}}<br>Day: %{{y}}<br>" + metric + ": %{z:.1f}<extra></extra>"
        ))
    
    day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    
    fig.update_layout(
        title=f"<b>3D Multi-Surface: {metric} by Team</b>",
        scene=dict(
            xaxis_title="Hour of Day",
            yaxis=dict(
                title="Day of Week",
                tickmode="array",
                tickvals=list(range(7)),
                ticktext=day_names
            ),
            zaxis_title=metric
        ),
        template=PLOTLY_TEMPLATE,
        height=600,
        title_font_size=18
    )
    
    return fig


def plot_team_by_weekday_heatmap(filtered_df, timeseries_df):
    """
    Graph 5: Team × Weekday Heatmap
    Shows which teams work on weekends
    """
    # Get teams from filtered data
    teams = sorted(filtered_df["team"].unique())
    day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    
    # Get baseline pattern from timeseries
    baseline = timeseries_df.groupby("day_of_week")["utilization_pct"].mean().to_dict()
    
    # Create team × weekday data with consistent random seed per team
    pivot_data = []
    for idx, team in enumerate(teams):
        np.random.seed(50 + idx)  # Consistent pattern per team
        team_pattern = []
        for day in range(7):
            # Add team-specific variance to baseline
            team_util = baseline[day] + np.random.normal(0, 8)
            team_util = max(10, min(80, team_util))  # Keep in reasonable range
            team_pattern.append(team_util)
        pivot_data.append(team_pattern)
    
    fig = go.Figure(data=go.Heatmap(
        z=pivot_data,
        x=day_names,
        y=teams,
        colorscale="YlOrRd",
        text=[[f"{val:.1f}%" for val in row] for row in pivot_data],
        texttemplate="%{text}",
        textfont={"size": 10},
        hovertemplate="<b>%{y}</b><br>%{x}: %{z:.1f}%<extra></extra>",
        colorbar=dict(title="Utilization %")
    ))
    
    fig.update_layout(
        title="<b>Team × Weekday Utilization Pattern</b>",
        xaxis_title="Day of Week",
        yaxis_title="Team",
        template=PLOTLY_TEMPLATE,
        height=400,
        title_font_size=16
    )
    
    return fig


# ============================================================================
# MAIN APP
# ============================================================================

def main():
    st.title("📊 Executive GPU Dashboard")
    st.markdown("**Leadership View** | Committed GPU Capacity & Efficiency")
    
    st.markdown("---")
    
    # Load data
    all_gpu_df = generate_all_gpu_data()
    timeseries_df = generate_30day_timeseries()
    hourly_patterns_df = generate_hourly_usage_patterns()
    
    # Separate committed for Section 1
    committed_df = all_gpu_df[all_gpu_df["workload_type"] == "committed"]
    
    # ========================================================================
    # GLOBAL FILTERS
    # ========================================================================
    
    st.markdown("### 🔍 Filters")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        selected_clouds = st.multiselect(
            "Cloud Provider",
            options=sorted(all_gpu_df["cloud"].unique()),
            default=sorted(all_gpu_df["cloud"].unique())
        )
    
    with col2:
        selected_gpu_types = st.multiselect(
            "GPU Type",
            options=sorted(all_gpu_df["gpu_type"].unique()),
            default=sorted(all_gpu_df["gpu_type"].unique())
        )
    
    with col3:
        selected_teams = st.multiselect(
            "Team",
            options=sorted(all_gpu_df["team"].unique()),
            default=sorted(all_gpu_df["team"].unique())
        )
    
    # Apply filters to all data
    filtered_all_df = all_gpu_df[
        (all_gpu_df["cloud"].isin(selected_clouds)) &
        (all_gpu_df["gpu_type"].isin(selected_gpu_types)) &
        (all_gpu_df["team"].isin(selected_teams))
    ]
    
    # Filtered committed only for Section 1
    filtered_committed_df = filtered_all_df[filtered_all_df["workload_type"] == "committed"]
    
    st.markdown("---")
    
    # ========================================================================
    # SECTION 1: CROSS CLUSTERS OVERVIEW
    # ========================================================================
    
    st.header("🌐 Cross Clusters Overview")
    st.markdown("*Committed GPUs only - Organizational capacity and efficiency*")
    
    st.markdown("")
    
    # Three graphs in one row
    col1, col2, col3 = st.columns(3)
    
    with col1:
        # Graph 1: Committed GPU Inventory
        st.plotly_chart(
            plot_committed_inventory_by_type_and_cloud(filtered_committed_df),
            use_container_width=True
        )
    
    with col2:
        # Graph 2: 30-Day Trend
        st.plotly_chart(
            plot_30day_used_vs_utilization_trend(timeseries_df),
            use_container_width=True
        )
    
    with col3:
        # Graph 3: Team Efficiency
        st.plotly_chart(
            plot_team_efficiency_scatter(filtered_committed_df),
            use_container_width=True
        )
    
    st.markdown("---")
    
    # ========================================================================
    # SECTION 2: WHO USES WHAT - DETAILED BREAKDOWN
    # ========================================================================
    
    st.header("👥 Who Uses What")
    st.markdown("*Detailed breakdown: Team × GPU Type × Workload Type × Cloud*")
    
    st.markdown("")
    
    # Detailed table with filters
    st.subheader("📋 Complete Usage Breakdown")
    
    # Table-specific filters
    with st.expander("🔍 Table Filters", expanded=False):
        col1, col2, col3, col4 = st.columns(4)
        
        # Get full breakdown table first
        full_breakdown_table = plot_team_gpu_breakdown_table(filtered_all_df)
        
        with col1:
            table_teams = st.multiselect(
                "Filter by Team",
                options=sorted(full_breakdown_table["Team"].unique()),
                default=sorted(full_breakdown_table["Team"].unique()),
                key="table_team_filter"
            )
        
        with col2:
            table_gpu_types = st.multiselect(
                "Filter by GPU Type",
                options=sorted(full_breakdown_table["GPU Type"].unique()),
                default=sorted(full_breakdown_table["GPU Type"].unique()),
                key="table_gpu_filter"
            )
        
        with col3:
            table_workload_types = st.multiselect(
                "Filter by Workload",
                options=sorted(full_breakdown_table["Workload Type"].unique()),
                default=sorted(full_breakdown_table["Workload Type"].unique()),
                key="table_workload_filter"
            )
        
        with col4:
            table_clouds = st.multiselect(
                "Filter by Cloud",
                options=sorted(full_breakdown_table["Cloud"].unique()),
                default=sorted(full_breakdown_table["Cloud"].unique()),
                key="table_cloud_filter"
            )
    
    # Apply table filters
    filtered_breakdown = full_breakdown_table[
        (full_breakdown_table["Team"].isin(table_teams)) &
        (full_breakdown_table["GPU Type"].isin(table_gpu_types)) &
        (full_breakdown_table["Workload Type"].isin(table_workload_types)) &
        (full_breakdown_table["Cloud"].isin(table_clouds))
    ]
    
    # Display count
    st.caption(f"📊 Showing {len(filtered_breakdown)} of {len(full_breakdown_table)} entries")
    
    # Display table
    st.dataframe(
        filtered_breakdown,
        use_container_width=True,
        hide_index=True,
        height=400
    )
    
    st.markdown("")
    
    # Daily team usage with Tabs per Cloud
    st.subheader("📈 Daily GPU Usage by Team")
    st.markdown("*30-day stacked area charts - Which teams drive GPU usage in each cloud*")
    
    st.markdown("")
    
    gpu_types = sorted(filtered_all_df["gpu_type"].unique())
    clouds = sorted(filtered_all_df["cloud"].unique())
    
    # Create tabs for each cloud
    cloud_tabs = st.tabs(clouds)
    
    for cloud_idx, cloud in enumerate(clouds):
        with cloud_tabs[cloud_idx]:
            st.markdown("")
            
            # Display GPU types in grid (3 per row)
            num_gpu_types = len(gpu_types)
            for i in range(0, num_gpu_types, 3):
                cols = st.columns(3)
                
                for col_idx in range(3):
                    gpu_idx = i + col_idx
                    if gpu_idx < num_gpu_types:
                        gpu_type = gpu_types[gpu_idx]
                        with cols[col_idx]:
                            chart = plot_daily_team_gpu_usage(
                                filtered_all_df,
                                timeseries_df,
                                gpu_type,
                                cloud
                            )
                            if chart:
                                st.plotly_chart(chart, use_container_width=True)
                
                st.markdown("")
    
    st.markdown("---")
    st.markdown("")
    
    # Sankey flow diagram
    st.subheader("🌊 GPU Usage Flow")
    st.markdown("*Follow the flow: Team → GPU Type → Workload Type → Cloud*")
    st.plotly_chart(
        plot_sankey_team_gpu_flow(filtered_all_df),
        use_container_width=True
    )
    
    st.markdown("")
    
    # GPU Hours breakdown
    col1, col2 = st.columns(2)
    
    with col1:
        st.plotly_chart(
            plot_gpu_hours_by_team_stacked(filtered_all_df),
            use_container_width=True
        )
    
    with col2:
        st.plotly_chart(
            plot_team_cloud_workload_heatmap(filtered_all_df),
            use_container_width=True
        )
    
    st.markdown("---")
    
    # ========================================================================
    # SECTION 3: CAPACITY CONSUMPTION & EFFICIENCY
    # ========================================================================
    
    st.header("⚡ Capacity Consumption & Efficiency")
    st.markdown("*30-day trends and team efficiency analysis*")
    
    st.markdown("")
    
    # Team Efficiency - Tabs for All + Each GPU Type
    st.subheader("🔬 Team Efficiency Analysis")
    st.markdown("*30-day trends - Compare teams across all GPUs or drill down by type*")
    
    st.markdown("")
    
    # Get unique GPU types from filtered data
    gpu_types = sorted(filtered_all_df["gpu_type"].unique())
    
    # Create tabs: "All GPU Types" + individual GPU types
    tab_labels = ["📊 All GPU Types"] + gpu_types
    tabs = st.tabs(tab_labels)
    
    # Tab 0: All GPU Types
    with tabs[0]:
        st.markdown("")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**Used % (Committed Only)**")
            st.plotly_chart(
                plot_used_trend_by_team_all_gpus(filtered_all_df, timeseries_df),
                use_container_width=True
            )
        
        with col2:
            st.markdown("**Utilization % (All Workload Types)**")
            st.plotly_chart(
                plot_utilization_trend_by_team_all_gpus(filtered_all_df, timeseries_df),
                use_container_width=True
            )
    
    # Tabs 1+: Individual GPU Types
    for idx, gpu_type in enumerate(gpu_types):
        with tabs[idx + 1]:
            st.markdown("")
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("**Used % by Team (Committed)**")
                st.plotly_chart(
                    plot_used_by_team_per_gpu_type(
                        filtered_all_df, 
                        timeseries_df, 
                        gpu_type
                    ),
                    use_container_width=True
                )
            
            with col2:
                st.markdown("**Utilization % by Team (All Workloads)**")
                st.plotly_chart(
                    plot_utilization_by_team_per_gpu_type(
                        filtered_all_df, 
                        timeseries_df, 
                        gpu_type
                    ),
                    use_container_width=True
                )
    
    st.markdown("---")
    
    # ========================================================================
    # SECTION 4: USAGE PATTERNS & TIME ANALYSIS
    # ========================================================================
    
    st.header("🕐 Usage Patterns & Time Analysis")
    st.markdown("*Behavioral patterns - When and how teams use GPUs*")
    
    st.markdown("")
    
    # Pattern filters - inherit from global but allow override
    with st.container():
        st.markdown("##### 🎛️ Pattern Filters")
        st.caption("⚙️ Inherits from global filters above - refine selection below")
        
        col1, col2, col3, col4 = st.columns([3, 3, 2, 1])
        
        with col1:
            # Start from globally filtered teams
            available_teams = sorted(filtered_all_df["team"].unique())
            pattern_selected_teams = st.multiselect(
                "Focus Teams",
                options=available_teams,
                default=available_teams,
                key="pattern_teams",
                help="Refine team selection from global filters"
            )
        
        with col2:
            # Start from globally filtered GPU types
            available_gpu_types = sorted(filtered_all_df["gpu_type"].unique())
            pattern_selected_gpu_types = st.multiselect(
                "Focus GPU Types",
                options=available_gpu_types,
                default=available_gpu_types,
                key="pattern_gpus",
                help="Refine GPU type selection from global filters"
            )
        
        with col3:
            pattern_metric = st.selectbox(
                "Metric",
                options=["GPU Hours", "Utilization %"],
                index=0,
                key="pattern_metric"
            )
        
        with col4:
            st.markdown("")
            st.markdown("")
            if st.button("↻ Reset", key="reset_pattern_filters"):
                st.rerun()
    
    st.markdown("")
    
    # Usage info
    if pattern_selected_teams and pattern_selected_gpu_types:
        team_count = len(pattern_selected_teams)
        total_teams = len(available_teams)
        gpu_count = len(pattern_selected_gpu_types)
        total_gpus = len(available_gpu_types)
        
        st.info(f"📊 **Viewing:** {team_count}/{total_teams} teams · {gpu_count}/{total_gpus} GPU types · Metric: {pattern_metric}")
    
    st.markdown("")
    
    # Display heatmaps based on filters
    if pattern_selected_teams and pattern_selected_gpu_types:
        
        # Main heatmap: Hour × Day
        st.subheader("📊 Hourly Usage Pattern")
        st.plotly_chart(
            plot_dynamic_usage_heatmap(
                hourly_patterns_df,
                pattern_selected_teams,
                pattern_selected_gpu_types,
                pattern_metric
            ),
            use_container_width=True
        )
        
        st.markdown("")
        st.markdown("---")
        st.markdown("")
        
        # Secondary heatmaps: Weekday patterns
        st.subheader("📅 Weekly Summary Patterns")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**Metrics × Weekday**")
            st.plotly_chart(
                plot_metrics_by_weekday_heatmap(timeseries_df),
                use_container_width=True
            )
        
        with col2:
            # Filter committed data for team heatmap
            pattern_filtered_committed = filtered_all_df[
                (filtered_all_df["workload_type"] == "committed") &
                (filtered_all_df["team"].isin(pattern_selected_teams))
            ]
            
            st.markdown("**Team × Weekday**")
            st.plotly_chart(
                plot_team_by_weekday_heatmap(pattern_filtered_committed, timeseries_df),
                use_container_width=True
            )
    else:
        st.warning("⚠️ Please select at least one team and one GPU type")
    
    st.markdown("---")
    
    # Footer
    st.caption("""
    📊 **Executive GPU Dashboard** | Source: Prometheus/Thanos (simulated)  
    Focus: Capacity · Efficiency · Ownership · Time Patterns
    """)


if __name__ == "__main__":
    main()
