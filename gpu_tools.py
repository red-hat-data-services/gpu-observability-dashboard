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

# Constants matching real cluster
GPU_TYPES = ["NVIDIA A10G"]
CLOUDS = ["AWS"]
TEAMS = ["team-alpha", "team-beta", "team-gamma", "team-delta", "llama-stack-rag", "gpuaas-demo"]
WORKLOAD_TYPES = ["committed", "spot"]
DAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def init(all_gpu_df: pd.DataFrame, timeseries_df: pd.DataFrame, hourly_df: pd.DataFrame) -> None:
    """Initialize with DataFrames from data_live or mock generators."""
    global _all_gpu_df, _timeseries_df, _hourly_df
    _all_gpu_df = all_gpu_df
    _timeseries_df = timeseries_df
    _hourly_df = hourly_df


def _require_init() -> None:
    if _all_gpu_df is None:
        raise RuntimeError("gpu_tools not initialized. Call init() first.")


# ---------------------------------------------------------------------------
# Existing 7 tools — updated for real cluster data
# ---------------------------------------------------------------------------


def get_gpu_inventory(cloud: str | None = None, gpu_type: str | None = None) -> dict:
    """Get real GPU inventory from cluster nodes and DCGM metrics."""
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
    """Find hours/days with highest GPU usage and best scheduling times."""
    _require_init()
    df = _hourly_df.copy()

    if team:
        df = df[df["team"] == team]
    if gpu_type:
        df = df[df["gpu_type"] == gpu_type]

    by_hour = df.groupby("hour").agg(
        gpu_hours=("gpu_hours", "mean"),
        utilization_pct=("utilization_pct", "mean"),
    ).reset_index().round(1)

    by_day = df.groupby("day_of_week").agg(
        gpu_hours=("gpu_hours", "mean"),
        utilization_pct=("utilization_pct", "mean"),
    ).reset_index().round(1)
    by_day["day_name"] = by_day["day_of_week"].map(lambda d: DAY_NAMES[d])

    peak_hour_row = by_hour.loc[by_hour["gpu_hours"].idxmax()]
    peak_day_row = by_day.loc[by_day["gpu_hours"].idxmax()]
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

    overall_util = round(float(df["utilization_pct"].mean()), 1) if not df.empty else 0.0

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


# ---------------------------------------------------------------------------
# 3 new tools for Kueue + GPU health
# ---------------------------------------------------------------------------


def get_queue_status() -> dict:
    """Get current Kueue queue status — pending workloads, admitted workloads, queue depth."""
    import data_live
    kueue = data_live.fetch_kueue_status()

    cq = kueue.get("cluster_queue", {})
    lqs = kueue.get("local_queues", [])

    pending = cq.get("pending_workloads", 0)
    admitted = cq.get("admitted_workloads", 0)
    quota = cq.get("nominal_quota", {}).get("gpu", 0)

    if pending == 0 and admitted == 0:
        summary = f"Queue is idle — no workloads pending or admitted. {quota} GPU quota available."
    elif pending > 0:
        summary = f"Queue is busy — {pending} workloads pending, {admitted} admitted. GPU quota: {quota}."
    else:
        summary = f"Queue is active — {admitted} workloads admitted, none pending. GPU quota: {quota}."

    return {
        "cluster_queue": {
            "name": cq.get("name", "gpu-cluster-queue"),
            "pending_workloads": pending,
            "admitted_workloads": admitted,
            "nominal_quota": {"gpu": quota},
        },
        "local_queues": lqs,
        "summary": summary,
    }


def get_workload_status(namespace: str | None = None) -> dict:
    """Get status of Kueue workloads — running, pending, preempted."""
    import data_live
    kueue = data_live.fetch_kueue_status()

    workloads = kueue.get("workloads", [])
    events = kueue.get("recent_events", [])
    cq = kueue.get("cluster_queue", {})
    lqs = kueue.get("local_queues", [])

    if namespace:
        workloads = [w for w in workloads if w.get("namespace") == namespace]

    by_status = {"admitted": 0, "pending": 0, "preempted": 0}
    for w in workloads:
        s = w.get("status", "pending")
        if s in by_status:
            by_status[s] += 1

    # Enrich pending workloads with reason + admission context
    quota = cq.get("nominal_quota", {}).get("gpu", 0)
    admitted_gpu_total = sum(
        w.get("gpu_requests", 0) for w in workloads if w.get("status") == "admitted"
    )
    gpu_available = max(0, quota - admitted_gpu_total)

    for w in workloads:
        if w.get("status") == "pending":
            gpu_req = w.get("gpu_requests", 0)
            priority = w.get("priority", "")

            # Determine reason
            if gpu_available < gpu_req:
                if priority in ("low-priority", ""):
                    # Check if higher-priority workloads hold the GPUs
                    higher_admitted = [
                        a for a in workloads
                        if a.get("status") == "admitted"
                        and a.get("priority") in ("high-priority",)
                    ]
                    if higher_admitted:
                        w["pending_reason"] = (
                            f"Quota full ({admitted_gpu_total}/{quota} GPUs admitted). "
                            f"Higher-priority workloads hold the GPUs. "
                            f"This low-priority workload will be admitted when a "
                            f"high-priority workload finishes or quota is increased."
                        )
                    else:
                        w["pending_reason"] = (
                            f"Quota full ({admitted_gpu_total}/{quota} GPUs admitted). "
                            f"Will be admitted when a running workload completes."
                        )
                else:
                    w["pending_reason"] = (
                        f"Quota full ({admitted_gpu_total}/{quota} GPUs admitted). "
                        f"This high-priority workload may preempt a lower-priority one."
                    )
            else:
                w["pending_reason"] = "Waiting for Kueue admission controller to process."
        elif w.get("status") == "admitted":
            w["pending_reason"] = None

    return {
        "total_workloads": len(workloads),
        "by_status": by_status,
        "workloads": workloads,
        "recent_events": events[-10:],
        "queue_context": {
            "gpu_quota": quota,
            "gpu_admitted": admitted_gpu_total,
            "gpu_available": gpu_available,
        },
    }


def get_gpu_health(node: str | None = None) -> dict:
    """Get real-time GPU health — temperature, power, memory, utilization per GPU."""
    import data_live
    return data_live.fetch_gpu_health(node=node)


# ---------------------------------------------------------------------------
# Tool registry and schemas
# ---------------------------------------------------------------------------

TOOL_REGISTRY = {
    "get_gpu_inventory": get_gpu_inventory,
    "get_team_efficiency": get_team_efficiency,
    "get_waste_analysis": get_waste_analysis,
    "get_peak_hours": get_peak_hours,
    "get_weekend_usage": get_weekend_usage,
    "get_trend": get_trend,
    "get_cloud_distribution": get_cloud_distribution,
    "get_queue_status": get_queue_status,
    "get_workload_status": get_workload_status,
    "get_gpu_health": get_gpu_health,
}

TOOL_SCHEMAS = {
    "get_gpu_inventory": {
        "name": "get_gpu_inventory",
        "description": "Get real GPU inventory from cluster nodes and DCGM metrics.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "cloud": {"type": "string", "description": "Filter by cloud provider", "enum": CLOUDS},
                "gpu_type": {"type": "string", "description": "Filter by GPU type", "enum": GPU_TYPES},
            },
        },
    },
    "get_team_efficiency": {
        "name": "get_team_efficiency",
        "description": "Get Used%, Utilization%, and waste gap for a team.",
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
        "description": "Find GPU allocations with high waste.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "min_waste_pct": {
                    "type": "number",
                    "description": "Minimum waste gap percentage threshold (default 25).",
                    "default": 25,
                },
            },
        },
    },
    "get_peak_hours": {
        "name": "get_peak_hours",
        "description": "Find hours/days with highest GPU usage and best scheduling times.",
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
        "description": "Get Saturday/Sunday GPU utilization.",
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
        "description": "Get 30-day utilization or allocation trend.",
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
        "description": "Get GPU distribution across cloud providers.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "team": {"type": "string", "description": "Filter by team", "enum": TEAMS},
                "gpu_type": {"type": "string", "description": "Filter by GPU type", "enum": GPU_TYPES},
            },
        },
    },
    "get_queue_status": {
        "name": "get_queue_status",
        "description": "Get current Kueue queue status — pending workloads, admitted workloads, queue depth. Use to answer 'why is my job pending?' or 'is the queue busy?'",
        "inputSchema": {
            "type": "object",
            "properties": {},
        },
    },
    "get_workload_status": {
        "name": "get_workload_status",
        "description": "Get status of Kueue workloads — running, pending, preempted. Use to answer 'why is my job failing?' or 'what happened to my workload?'",
        "inputSchema": {
            "type": "object",
            "properties": {
                "namespace": {
                    "type": "string",
                    "description": "Filter by team namespace",
                    "enum": ["team-alpha", "team-beta", "team-gamma", "team-delta", "gpuaas-demo"],
                },
            },
        },
    },
    "get_gpu_health": {
        "name": "get_gpu_health",
        "description": "Get real-time GPU health — temperature, power, memory, utilization per GPU. Use to answer 'are GPUs healthy?' or 'is any GPU overheating?'",
        "inputSchema": {
            "type": "object",
            "properties": {
                "node": {
                    "type": "string",
                    "description": "Filter by node hostname",
                },
            },
        },
    },
}
