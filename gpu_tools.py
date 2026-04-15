"""
GPU Observability Data Query Tools
===================================
Pandas query functions over the dashboard's DataFrames.
Used by the MCP server to answer natural language questions.
"""

import json
from datetime import datetime

import pandas as pd

# Module-level DataFrames — set via init()
_all_gpu_df: pd.DataFrame | None = None
_timeseries_df: pd.DataFrame | None = None
_hourly_df: pd.DataFrame | None = None

# Constants matching app.py
GPU_TYPES = ["L4", "T4", "A100-40GB", "A100-80GB", "H100", "H200", "B200"]
CLOUDS = ["AWS", "GCP", "IBM Cloud"]
TEAMS = ["ML Platform", "AI Research", "Data Science", "Engineering", "Customer Analytics"]
WORKLOAD_TYPES = ["committed", "on-demand", "spot"]
DAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def init(all_gpu_df: pd.DataFrame, timeseries_df: pd.DataFrame, hourly_df: pd.DataFrame) -> None:
    """Initialize with DataFrames from app.py's generate_*() functions."""
    global _all_gpu_df, _timeseries_df, _hourly_df
    _all_gpu_df = all_gpu_df
    _timeseries_df = timeseries_df
    _hourly_df = hourly_df


def _require_init() -> None:
    if _all_gpu_df is None:
        raise RuntimeError("gpu_tools not initialized. Call init() first.")


def get_gpu_inventory(cloud: str | None = None, gpu_type: str | None = None) -> dict:
    """Get total GPU count by type and cloud provider."""
    _require_init()
    df = _all_gpu_df.copy()

    if cloud:
        df = df[df["cloud"] == cloud]
    if gpu_type:
        df = df[df["gpu_type"] == gpu_type]

    agg = df.groupby(["gpu_type", "cloud"]).agg(
        total_gpus=("total_gpus", "sum"),
        allocated_gpus=("allocated_gpus", "sum"),
    ).reset_index()

    summary = {
        "total_gpus": int(agg["total_gpus"].sum()),
        "allocated_gpus": int(agg["allocated_gpus"].sum()),
        "used_pct": round(float(agg["allocated_gpus"].sum() / agg["total_gpus"].sum() * 100), 1)
        if agg["total_gpus"].sum() > 0
        else 0.0,
    }

    inventory = agg.to_dict(orient="records")
    for row in inventory:
        row["total_gpus"] = int(row["total_gpus"])
        row["allocated_gpus"] = int(row["allocated_gpus"])

    return {"inventory": inventory, "summary": summary}


def get_team_efficiency(
    team: str,
    gpu_type: str | None = None,
    workload_type: str | None = None,
) -> dict:
    """Get Used%, Utilization%, and waste gap for a team."""
    _require_init()
    df = _all_gpu_df[_all_gpu_df["team"] == team].copy()

    if gpu_type:
        df = df[df["gpu_type"] == gpu_type]
    if workload_type:
        df = df[df["workload_type"] == workload_type]

    if df.empty:
        return {"error": f"No data found for team '{team}' with given filters."}

    avg_used = round(float(df["used_pct"].mean()), 1)
    avg_util = round(float(df["utilization_pct"].mean()), 1)
    waste_gap = round(avg_used - avg_util, 1)
    total_gpus = int(df["total_gpus"].sum())

    breakdown = (
        df.groupby("gpu_type")
        .agg(
            used_pct=("used_pct", "mean"),
            utilization_pct=("utilization_pct", "mean"),
            total_gpus=("total_gpus", "sum"),
        )
        .reset_index()
    )
    breakdown = breakdown.round(1)
    breakdown["total_gpus"] = breakdown["total_gpus"].astype(int)

    return {
        "team": team,
        "avg_used_pct": avg_used,
        "avg_utilization_pct": avg_util,
        "waste_gap_pct": waste_gap,
        "total_gpus": total_gpus,
        "by_gpu_type": breakdown.to_dict(orient="records"),
    }


def get_waste_analysis(min_waste_pct: float = 25.0) -> dict:
    """Find teams/GPU combos with high waste (Used% - Utilization% > threshold)."""
    _require_init()
    df = _all_gpu_df.copy()

    agg = (
        df.groupby(["team", "gpu_type", "workload_type"])
        .agg(
            used_pct=("used_pct", "mean"),
            utilization_pct=("utilization_pct", "mean"),
            total_gpus=("total_gpus", "sum"),
        )
        .reset_index()
    )
    agg["waste_gap_pct"] = agg["used_pct"] - agg["utilization_pct"]
    wasteful = agg[agg["waste_gap_pct"] >= min_waste_pct].sort_values("waste_gap_pct", ascending=False)

    wasteful = wasteful.round(1)
    wasteful["total_gpus"] = wasteful["total_gpus"].astype(int)

    return {
        "threshold_pct": min_waste_pct,
        "wasteful_count": len(wasteful),
        "wasteful_allocations": wasteful.to_dict(orient="records"),
    }


def get_peak_hours(team: str | None = None, gpu_type: str | None = None) -> dict:
    """Find hours/days with highest GPU usage."""
    _require_init()
    df = _hourly_df.copy()

    if team:
        df = df[df["team"] == team]
    if gpu_type:
        df = df[df["gpu_type"] == gpu_type]

    # Aggregate by hour and day
    by_hour = df.groupby("hour").agg(
        gpu_hours=("gpu_hours", "mean"),
        utilization_pct=("utilization_pct", "mean"),
    ).reset_index().round(1)

    by_day = df.groupby("day_of_week").agg(
        gpu_hours=("gpu_hours", "mean"),
        utilization_pct=("utilization_pct", "mean"),
    ).reset_index().round(1)
    by_day["day_name"] = by_day["day_of_week"].map(lambda d: DAY_NAMES[d])

    # Find peak
    peak_hour_row = by_hour.loc[by_hour["gpu_hours"].idxmax()]
    peak_day_row = by_day.loc[by_day["gpu_hours"].idxmax()]

    # Find lowest (best time to schedule)
    low_hour_row = by_hour.loc[by_hour["gpu_hours"].idxmin()]
    low_day_row = by_day.loc[by_day["gpu_hours"].idxmin()]

    return {
        "peak_hour": int(peak_hour_row["hour"]),
        "peak_hour_gpu_hours": float(peak_hour_row["gpu_hours"]),
        "peak_day": DAY_NAMES[int(peak_day_row["day_of_week"])],
        "peak_day_gpu_hours": float(peak_day_row["gpu_hours"]),
        "best_hour_to_schedule": int(low_hour_row["hour"]),
        "best_day_to_schedule": DAY_NAMES[int(low_day_row["day_of_week"])],
        "hourly_breakdown": by_hour.to_dict(orient="records"),
        "daily_breakdown": by_day[["day_name", "gpu_hours", "utilization_pct"]].to_dict(orient="records"),
    }


def get_weekend_usage(team: str | None = None, gpu_type: str | None = None) -> dict:
    """Get Saturday/Sunday utilization by team."""
    _require_init()
    df = _hourly_df[_hourly_df["day_of_week"] >= 5].copy()

    if team:
        df = df[df["team"] == team]
    if gpu_type:
        df = df[df["gpu_type"] == gpu_type]

    by_team_day = (
        df.groupby(["team", "day_of_week"])
        .agg(
            gpu_hours=("gpu_hours", "mean"),
            utilization_pct=("utilization_pct", "mean"),
        )
        .reset_index()
        .round(1)
    )
    by_team_day["day_name"] = by_team_day["day_of_week"].map(lambda d: DAY_NAMES[d])

    # Overall weekend average
    overall_util = round(float(df["utilization_pct"].mean()), 1)

    # Per-team summary
    team_summary = (
        df.groupby("team")
        .agg(
            avg_utilization_pct=("utilization_pct", "mean"),
            avg_gpu_hours=("gpu_hours", "mean"),
        )
        .reset_index()
        .round(1)
        .sort_values("avg_utilization_pct")
    )

    return {
        "overall_weekend_utilization_pct": overall_util,
        "team_summary": team_summary.to_dict(orient="records"),
        "detail": by_team_day[["team", "day_name", "gpu_hours", "utilization_pct"]].to_dict(orient="records"),
    }


def get_trend(metric: str = "utilization_pct", workload_type: str | None = None) -> dict:
    """Get 30-day trend for a metric."""
    _require_init()
    df = _timeseries_df.copy()

    if workload_type:
        df = df[df["workload_type"] == workload_type]

    if metric not in ("used_pct", "utilization_pct"):
        return {"error": f"Unknown metric '{metric}'. Use 'used_pct' or 'utilization_pct'."}

    daily = df.groupby("date")[metric].mean().reset_index()
    daily = daily.sort_values("date")

    values = daily[metric].values
    first_half = float(values[: len(values) // 2].mean())
    second_half = float(values[len(values) // 2 :].mean())
    trend_direction = "increasing" if second_half > first_half + 1 else "decreasing" if second_half < first_half - 1 else "stable"

    daily_records = []
    for _, row in daily.iterrows():
        daily_records.append({
            "date": row["date"].strftime("%Y-%m-%d") if hasattr(row["date"], "strftime") else str(row["date"]),
            metric: round(float(row[metric]), 1),
        })

    return {
        "metric": metric,
        "workload_type": workload_type or "all",
        "avg_value": round(float(values.mean()), 1),
        "min_value": round(float(values.min()), 1),
        "max_value": round(float(values.max()), 1),
        "trend_direction": trend_direction,
        "first_half_avg": round(first_half, 1),
        "second_half_avg": round(second_half, 1),
        "daily": daily_records,
    }


def get_cloud_distribution(team: str | None = None, gpu_type: str | None = None) -> dict:
    """Get GPU distribution across cloud providers."""
    _require_init()
    df = _all_gpu_df.copy()

    if team:
        df = df[df["team"] == team]
    if gpu_type:
        df = df[df["gpu_type"] == gpu_type]

    by_cloud = (
        df.groupby("cloud")
        .agg(
            total_gpus=("total_gpus", "sum"),
            allocated_gpus=("allocated_gpus", "sum"),
            avg_used_pct=("used_pct", "mean"),
            avg_utilization_pct=("utilization_pct", "mean"),
        )
        .reset_index()
        .round(1)
    )
    by_cloud["total_gpus"] = by_cloud["total_gpus"].astype(int)
    by_cloud["allocated_gpus"] = by_cloud["allocated_gpus"].astype(int)

    return {
        "distribution": by_cloud.to_dict(orient="records"),
        "total_gpus": int(by_cloud["total_gpus"].sum()),
    }


# Tool registry for MCP server
TOOL_REGISTRY = {
    "get_gpu_inventory": get_gpu_inventory,
    "get_team_efficiency": get_team_efficiency,
    "get_waste_analysis": get_waste_analysis,
    "get_peak_hours": get_peak_hours,
    "get_weekend_usage": get_weekend_usage,
    "get_trend": get_trend,
    "get_cloud_distribution": get_cloud_distribution,
}

# Tool schemas for MCP server and spec validation
TOOL_SCHEMAS = {
    "get_gpu_inventory": {
        "name": "get_gpu_inventory",
        "description": "Get total GPU count by type and cloud provider. Use to answer questions like 'how many H100s do we have?' or 'what GPUs are in AWS?'",
        "inputSchema": {
            "type": "object",
            "properties": {
                "cloud": {"type": "string", "description": "Filter by cloud provider (AWS, GCP, IBM Cloud)", "enum": CLOUDS},
                "gpu_type": {"type": "string", "description": "Filter by GPU type", "enum": GPU_TYPES},
            },
        },
    },
    "get_team_efficiency": {
        "name": "get_team_efficiency",
        "description": "Get Used%, Utilization%, and waste gap for a specific team. Use to answer questions like 'how efficient is ML Platform?' or 'is Engineering wasting GPUs?'",
        "inputSchema": {
            "type": "object",
            "properties": {
                "team": {"type": "string", "description": "Team name (required)", "enum": TEAMS},
                "gpu_type": {"type": "string", "description": "Filter by GPU type", "enum": GPU_TYPES},
                "workload_type": {"type": "string", "description": "Filter by workload type", "enum": WORKLOAD_TYPES},
            },
            "required": ["team"],
        },
    },
    "get_waste_analysis": {
        "name": "get_waste_analysis",
        "description": "Find teams and GPU type combinations with high waste (allocated but underutilized). Use to answer 'who is wasting GPUs?' or 'where is the biggest inefficiency?'",
        "inputSchema": {
            "type": "object",
            "properties": {
                "min_waste_pct": {
                    "type": "number",
                    "description": "Minimum waste gap percentage threshold (default 25). Lower values return more results.",
                    "default": 25,
                },
            },
        },
    },
    "get_peak_hours": {
        "name": "get_peak_hours",
        "description": "Find hours and days with highest GPU usage, and the best times to schedule jobs. Use to answer 'when are peak hours?' or 'when should I run my batch job?'",
        "inputSchema": {
            "type": "object",
            "properties": {
                "team": {"type": "string", "description": "Filter by team", "enum": TEAMS},
                "gpu_type": {"type": "string", "description": "Filter by GPU type", "enum": GPU_TYPES},
            },
        },
    },
    "get_weekend_usage": {
        "name": "get_weekend_usage",
        "description": "Get Saturday and Sunday GPU utilization by team. Use to answer 'are GPUs idle on weekends?' or 'which teams work weekends?'",
        "inputSchema": {
            "type": "object",
            "properties": {
                "team": {"type": "string", "description": "Filter by team", "enum": TEAMS},
                "gpu_type": {"type": "string", "description": "Filter by GPU type", "enum": GPU_TYPES},
            },
        },
    },
    "get_trend": {
        "name": "get_trend",
        "description": "Get 30-day trend for utilization or allocation. Use to answer 'is utilization going up?' or 'how has usage changed?'",
        "inputSchema": {
            "type": "object",
            "properties": {
                "metric": {
                    "type": "string",
                    "description": "Metric to trend",
                    "enum": ["used_pct", "utilization_pct"],
                    "default": "utilization_pct",
                },
                "workload_type": {"type": "string", "description": "Filter by workload type", "enum": WORKLOAD_TYPES},
            },
        },
    },
    "get_cloud_distribution": {
        "name": "get_cloud_distribution",
        "description": "Get GPU distribution across cloud providers. Use to answer 'where are our A100s?' or 'how many GPUs in GCP?'",
        "inputSchema": {
            "type": "object",
            "properties": {
                "team": {"type": "string", "description": "Filter by team", "enum": TEAMS},
                "gpu_type": {"type": "string", "description": "Filter by GPU type", "enum": GPU_TYPES},
            },
        },
    },
}
