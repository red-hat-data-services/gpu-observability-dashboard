"""
GPU Observability MCP Server
=============================
Exposes GPU data query tools via MCP (streamable HTTP).
LlamaStack connects to this server and executes tools during agentic loops.

Usage:
    python mcp_server.py                    # default port 8330
    MCP_PORT=9000 python mcp_server.py      # custom port
"""

import json
import os
import sys

from mcp.server.fastmcp import FastMCP

# Import data generation from the dashboard app
# We replicate the generate functions here so the MCP server
# can run standalone without Streamlit.
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

import gpu_tools

# ---------------------------------------------------------------------------
# Data generation (copied from app.py to avoid Streamlit dependency)
# ---------------------------------------------------------------------------

def generate_all_gpu_data() -> pd.DataFrame:
    np.random.seed(42)
    clouds = ["AWS", "GCP", "IBM Cloud"]
    gpu_types = ["L4", "T4", "A100-40GB", "A100-80GB", "H100", "H200", "B200"]
    teams = ["ML Platform", "AI Research", "Data Science", "Engineering", "Customer Analytics"]
    workload_types = ["committed", "on-demand", "spot"]
    gpu_weights = {"L4": 1.0, "T4": 1.0, "A100-40GB": 0.8, "A100-80GB": 0.7, "H100": 0.5, "H200": 0.3, "B200": 0.2}

    data = []
    for cloud in clouds:
        for gpu_type in gpu_types:
            if np.random.random() > gpu_weights[gpu_type]:
                continue
            for team in teams:
                for workload_type in workload_types:
                    if gpu_type in ["L4", "T4"]:
                        num_gpus = np.random.randint(4, 16)
                    elif gpu_type in ["A100-40GB", "A100-80GB"]:
                        num_gpus = np.random.randint(2, 12)
                    elif gpu_type == "H100":
                        num_gpus = np.random.randint(1, 8)
                    elif gpu_type == "H200":
                        num_gpus = np.random.randint(1, 6)
                    else:
                        num_gpus = np.random.randint(1, 4)

                    if workload_type == "committed":
                        allocated = int(num_gpus * np.random.uniform(0.6, 0.85))
                        utilization = np.random.uniform(30, 75)
                    elif workload_type == "on-demand":
                        allocated = int(num_gpus * np.random.uniform(0.95, 1.0))
                        utilization = np.random.uniform(40, 80)
                    else:
                        allocated = int(num_gpus * np.random.uniform(0.95, 1.0))
                        utilization = np.random.uniform(50, 85)

                    used_pct = (allocated / num_gpus) * 100
                    data.append({
                        "cloud": cloud, "gpu_type": gpu_type, "team": team,
                        "workload_type": workload_type, "total_gpus": num_gpus,
                        "allocated_gpus": allocated, "used_pct": used_pct,
                        "utilization_pct": utilization, "idle_pct": 100 - used_pct,
                    })
    return pd.DataFrame(data)


def generate_30day_timeseries() -> pd.DataFrame:
    np.random.seed(45)
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)
    dates = pd.date_range(start=start_date, end=end_date, freq="D")
    workload_types = ["committed", "on-demand", "spot"]

    data = []
    for date in dates:
        day_of_week = date.dayofweek
        weekend_factor = 0.6 if day_of_week >= 5 else 1.0
        for workload_type in workload_types:
            if workload_type == "committed":
                used_pct = np.random.uniform(60, 75) * weekend_factor
                utilization_pct = np.random.uniform(35, 55) * weekend_factor
            elif workload_type == "on-demand":
                used_pct = np.random.uniform(95, 100)
                utilization_pct = np.random.uniform(45, 65) * weekend_factor
            else:
                used_pct = np.random.uniform(95, 100)
                utilization_pct = np.random.uniform(50, 70) * weekend_factor
            data.append({
                "date": date, "workload_type": workload_type,
                "used_pct": used_pct, "utilization_pct": utilization_pct,
                "day_of_week": day_of_week,
            })
    return pd.DataFrame(data)


def generate_hourly_usage_patterns() -> pd.DataFrame:
    np.random.seed(100)
    teams = ["ML Platform", "AI Research", "Data Science", "Engineering", "Customer Analytics"]
    gpu_types = ["L4", "T4", "A100-40GB", "A100-80GB", "H100", "H200", "B200"]

    data = []
    for day_of_week in range(7):
        for hour in range(24):
            for team in teams:
                for gpu_type in gpu_types:
                    is_work_hours = 9 <= hour <= 17
                    is_weekday = day_of_week < 5
                    if is_weekday and is_work_hours:
                        base_gpu_hours = np.random.uniform(80, 150)
                        base_utilization = np.random.uniform(50, 75)
                    elif is_weekday:
                        base_gpu_hours = np.random.uniform(40, 80)
                        base_utilization = np.random.uniform(30, 50)
                    else:
                        base_gpu_hours = np.random.uniform(20, 60)
                        base_utilization = np.random.uniform(20, 40)
                    team_factor = 1.0 + (hash(team) % 30) / 100
                    data.append({
                        "team": team, "gpu_type": gpu_type,
                        "day_of_week": day_of_week, "hour": hour,
                        "gpu_hours": base_gpu_hours * team_factor,
                        "utilization_pct": min(85, base_utilization * team_factor),
                    })
    return pd.DataFrame(data)


# ---------------------------------------------------------------------------
# MCP Server
# ---------------------------------------------------------------------------

mcp = FastMCP(
    "gpu-observability",
    instructions=(
        "GPU infrastructure observability tools. Query GPU allocation, utilization, "
        "waste, peak hours, trends, and cloud distribution across the organization."
    ),
)


@mcp.tool()
def get_gpu_inventory(cloud: str | None = None, gpu_type: str | None = None) -> str:
    """Get total GPU count by type and cloud provider.
    Use to answer questions like 'how many H100s do we have?' or 'what GPUs are in AWS?'
    """
    result = gpu_tools.get_gpu_inventory(cloud=cloud, gpu_type=gpu_type)
    return json.dumps(result, indent=2)


@mcp.tool()
def get_team_efficiency(team: str, gpu_type: str | None = None, workload_type: str | None = None) -> str:
    """Get Used%, Utilization%, and waste gap for a specific team.
    Use to answer questions like 'how efficient is ML Platform?' or 'is Engineering wasting GPUs?'
    """
    result = gpu_tools.get_team_efficiency(team=team, gpu_type=gpu_type, workload_type=workload_type)
    return json.dumps(result, indent=2)


@mcp.tool()
def get_waste_analysis(min_waste_pct: float = 25.0) -> str:
    """Find teams and GPU type combinations with high waste (allocated but underutilized).
    Use to answer 'who is wasting GPUs?' or 'where is the biggest inefficiency?'
    """
    result = gpu_tools.get_waste_analysis(min_waste_pct=min_waste_pct)
    return json.dumps(result, indent=2)


@mcp.tool()
def get_peak_hours(team: str | None = None, gpu_type: str | None = None) -> str:
    """Find hours and days with highest GPU usage, and the best times to schedule jobs.
    Use to answer 'when are peak hours?' or 'when should I run my batch job?'
    """
    result = gpu_tools.get_peak_hours(team=team, gpu_type=gpu_type)
    return json.dumps(result, indent=2)


@mcp.tool()
def get_weekend_usage(team: str | None = None, gpu_type: str | None = None) -> str:
    """Get Saturday and Sunday GPU utilization by team.
    Use to answer 'are GPUs idle on weekends?' or 'which teams work weekends?'
    """
    result = gpu_tools.get_weekend_usage(team=team, gpu_type=gpu_type)
    return json.dumps(result, indent=2)


@mcp.tool()
def get_trend(metric: str = "utilization_pct", workload_type: str | None = None) -> str:
    """Get 30-day trend for utilization or allocation.
    Use to answer 'is utilization going up?' or 'how has usage changed?'
    Args:
        metric: 'used_pct' or 'utilization_pct'
        workload_type: 'committed', 'on-demand', or 'spot'
    """
    result = gpu_tools.get_trend(metric=metric, workload_type=workload_type)
    return json.dumps(result, indent=2, default=str)


@mcp.tool()
def get_cloud_distribution(team: str | None = None, gpu_type: str | None = None) -> str:
    """Get GPU distribution across cloud providers.
    Use to answer 'where are our A100s?' or 'how many GPUs in GCP?'
    """
    result = gpu_tools.get_cloud_distribution(team=team, gpu_type=gpu_type)
    return json.dumps(result, indent=2)


def main():
    port = int(os.environ.get("MCP_PORT", "8330"))

    # Generate data and init tools
    print(f"Generating GPU data...")
    all_gpu_df = generate_all_gpu_data()
    timeseries_df = generate_30day_timeseries()
    hourly_df = generate_hourly_usage_patterns()
    gpu_tools.init(all_gpu_df, timeseries_df, hourly_df)
    print(f"Data ready: {len(all_gpu_df)} allocation records, {len(timeseries_df)} timeseries records, {len(hourly_df)} hourly records")

    print(f"Starting GPU Observability MCP server on port {port}...")
    # Override the default host/port via env for FastMCP
    os.environ["FASTMCP_PORT"] = str(port)
    mcp.run(transport="streamable-http")


if __name__ == "__main__":
    main()
