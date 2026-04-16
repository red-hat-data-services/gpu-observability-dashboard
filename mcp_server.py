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

from mcp.server.fastmcp import FastMCP

import gpu_tools
import data_live

# ---------------------------------------------------------------------------
# MCP Server
# ---------------------------------------------------------------------------

mcp = FastMCP(
    "gpu-observability",
    instructions=(
        "GPU infrastructure observability tools for the mid-chatbot cluster. "
        "Query real GPU allocation, utilization, Kueue queue status, workload health, "
        "and GPU temperatures from live DCGM metrics and Kubernetes API."
    ),
)


@mcp.tool()
def get_gpu_inventory(cloud: str | None = None, gpu_type: str | None = None) -> str:
    """Get real GPU inventory from cluster nodes and DCGM metrics."""
    result = gpu_tools.get_gpu_inventory(cloud=cloud, gpu_type=gpu_type)
    return json.dumps(result, indent=2)


@mcp.tool()
def get_team_efficiency(team: str, gpu_type: str | None = None, workload_type: str | None = None) -> str:
    """Get Used%, Utilization%, and waste gap for a team."""
    result = gpu_tools.get_team_efficiency(team=team, gpu_type=gpu_type, workload_type=workload_type)
    return json.dumps(result, indent=2)


@mcp.tool()
def get_waste_analysis(min_waste_pct: float = 25.0) -> str:
    """Find GPU allocations with high waste."""
    result = gpu_tools.get_waste_analysis(min_waste_pct=min_waste_pct)
    return json.dumps(result, indent=2)


@mcp.tool()
def get_peak_hours(team: str | None = None, gpu_type: str | None = None) -> str:
    """Find hours/days with highest GPU usage and best scheduling times."""
    result = gpu_tools.get_peak_hours(team=team, gpu_type=gpu_type)
    return json.dumps(result, indent=2)


@mcp.tool()
def get_weekend_usage(team: str | None = None, gpu_type: str | None = None) -> str:
    """Get Saturday/Sunday GPU utilization."""
    result = gpu_tools.get_weekend_usage(team=team, gpu_type=gpu_type)
    return json.dumps(result, indent=2)


@mcp.tool()
def get_trend(metric: str = "utilization_pct", workload_type: str | None = None) -> str:
    """Get 30-day utilization or allocation trend."""
    result = gpu_tools.get_trend(metric=metric, workload_type=workload_type)
    return json.dumps(result, indent=2, default=str)


@mcp.tool()
def get_cloud_distribution(team: str | None = None, gpu_type: str | None = None) -> str:
    """Get GPU distribution across cloud providers."""
    result = gpu_tools.get_cloud_distribution(team=team, gpu_type=gpu_type)
    return json.dumps(result, indent=2)


@mcp.tool()
def get_queue_status() -> str:
    """Get current Kueue queue status — pending workloads, admitted workloads, queue depth."""
    result = gpu_tools.get_queue_status()
    return json.dumps(result, indent=2)


@mcp.tool()
def get_workload_status(namespace: str | None = None) -> str:
    """Get status of Kueue workloads — running, pending, preempted."""
    result = gpu_tools.get_workload_status(namespace=namespace)
    return json.dumps(result, indent=2)


@mcp.tool()
def get_gpu_health(node: str | None = None) -> str:
    """Get real-time GPU health — temperature, power, memory, utilization per GPU."""
    result = gpu_tools.get_gpu_health(node=node)
    return json.dumps(result, indent=2)


def main():
    port = int(os.environ.get("MCP_PORT", "8330"))

    # Load live data and init tools
    print("Fetching live GPU data from cluster...")
    all_gpu_df = data_live.fetch_gpu_inventory()
    timeseries_df = data_live.fetch_timeseries()
    hourly_df = data_live.fetch_hourly_patterns()
    gpu_tools.init(all_gpu_df, timeseries_df, hourly_df)
    print(f"Data ready: {len(all_gpu_df)} inventory rows, {len(timeseries_df)} timeseries, {len(hourly_df)} hourly")

    print(f"Starting GPU Observability MCP server on port {port}...")
    os.environ["FASTMCP_PORT"] = str(port)
    mcp.run(transport="streamable-http")


if __name__ == "__main__":
    main()
