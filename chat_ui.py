"""
GPU Assistant — Chat-First Interface
======================================
Chat on the left, generated chart on the right.
Works with LlamaStack (full agentic) or direct mode (no LLM).
"""

import inspect
import json
import os

import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
import pandas as pd

LLAMA_STACK_ENDPOINT = os.environ.get("LLAMA_STACK_ENDPOINT", "http://localhost:8321")
LLAMA_STACK_MODEL = os.environ.get("LLAMA_STACK_MODEL", "meta-llama/Llama-3.1-8B-Instruct")
MCP_SERVER_URL = os.environ.get("MCP_SERVER_URL", "http://localhost:8330/mcp")

# ── Keyword routing for direct mode ──────────────────────────────────
KEYWORD_TOOL_MAP = [
    (["inventory", "how many", "count", "total gpu", "what gpu", "show me gpu"], "get_gpu_inventory", {}),
    (["waste", "wasting", "inefficien", "idle gpu", "hoarding", "biggest ineffic"], "get_waste_analysis", {"min_waste_pct": 20}),
    (["peak", "busiest", "schedule", "best time", "when should", "run my job", "submit", "launch"], "get_peak_hours", {}),
    (["weekend", "saturday", "sunday", "off hours", "night"], "get_weekend_usage", {}),
    (["trend", "going up", "going down", "increasing", "changing", "over time", "last 30", "month"], "get_trend", {}),
    (["cloud", "aws", "distribution", "where are", "which cloud"], "get_cloud_distribution", {}),
    (["queue", "pending", "stuck", "waiting", "why is my job", "busy"], "get_queue_status", {}),
    (["workload", "running", "preempt", "evict", "fail", "what happened", "my job"], "get_workload_status", {}),
    (["health", "temperature", "temp", "hot", "overheat", "power", "healthy", "gpu health"], "get_gpu_health", {}),
]

TEAM_NAMES = {
    "team-alpha": "team-alpha", "team alpha": "team-alpha", "alpha": "team-alpha",
    "team-beta": "team-beta", "team beta": "team-beta", "beta": "team-beta",
    "llama": "llama-stack-rag", "llama-stack": "llama-stack-rag",
    "gpuaas": "gpuaas-demo", "demo": "gpuaas-demo",
}

GPU_TYPE_NAMES = {
    "a10g": "NVIDIA A10G", "a10": "NVIDIA A10G", "nvidia a10": "NVIDIA A10G",
}

SYSTEM_PROMPT = """\
You are a GPU infrastructure analyst for the mid-chatbot cluster (ROSA on AWS).
The cluster has 8x NVIDIA A10G GPUs across 2 g5.12xlarge nodes.
Teams: team-alpha (P1/guaranteed), team-beta (P2/opportunistic).
Kueue manages GPU scheduling with preemption support.

ALWAYS use the available tools to query data before answering. Never guess numbers.
When reporting metrics, explain what they mean and suggest actionable next steps.
Keep responses concise — 2-4 sentences of insight plus a recommendation.

Key concepts:
- Used% = allocated/total GPUs (reservation rate)
- Utilization% = actual GPU compute load (from DCGM)
- Waste = Used% - Utilization% (allocated but idle)
- P1 (high-priority) = guaranteed workloads, cannot be preempted
- P2 (low-priority) = opportunistic workloads, fully preemptible
- Kueue ClusterQueue: gpu-cluster-queue, LocalQueues per team
"""

# ── Example prompts — both end-user and executive ────────────────────

EXAMPLE_CATEGORIES = {
    "Scheduling & Jobs": [
        "When should I schedule my batch job?",
        "Best time to run a training job on A10G?",
        "Is the weekend a good time for long jobs?",
        "Which GPUs are most oversubscribed?",
    ],
    "My Workloads": [
        "Is my job running?",
        "Why is my job pending?",
        "Is the queue busy right now?",
        "What workloads are running?",
        "Are there preemption risks for my spot workload?",
        "What happened to my workload?",
    ],
    "My Team": [
        "How efficient is team-alpha?",
        "Show me team-beta's GPU allocation",
        "Which team is wasting the most GPUs?",
        "Compare team-alpha vs team-beta efficiency",
    ],
    "GPU Health": [
        "Are GPUs healthy?",
        "What's the current GPU temperature?",
        "Is any GPU overheating?",
        "How many GPUs do we have total?",
    ],
    "Trends & Capacity": [
        "Is GPU utilization trending up or down?",
        "What's the waste gap this month?",
        "Should we add more A10G capacity?",
        "Where is the biggest GPU bottleneck?",
    ],
}


# ── Chart builders ───────────────────────────────────────────────────

def _build_chart(tool_name: str, result: dict) -> go.Figure | None:
    """Generate a Plotly chart from tool results."""
    try:
        if tool_name == "get_gpu_inventory" and "inventory" in result:
            df = pd.DataFrame(result["inventory"])
            if df.empty:
                return None
            fig = px.bar(
                df, x="gpu_type", y="total_gpus", color="cloud",
                title="<b>GPU Inventory by Type & Cloud</b>",
                color_discrete_map={"AWS": "#FF9900", "GCP": "#34A853", "IBM Cloud": "#0F62FE"},
                barmode="group", template="plotly_dark",
                labels={"total_gpus": "GPU Count", "gpu_type": "GPU Type"},
            )
            fig.update_traces(texttemplate="%{y}", textposition="outside")
            fig.update_layout(height=450, legend=dict(orientation="h", y=1.08, x=0.5, xanchor="center"))
            return fig

        elif tool_name == "get_team_efficiency" and "by_gpu_type" in result:
            df = pd.DataFrame(result["by_gpu_type"])
            if df.empty:
                return None
            team = result.get("team", "")
            fig = go.Figure()
            fig.add_trace(go.Bar(name="Used %", x=df["gpu_type"], y=df["used_pct"],
                                 marker_color="#1f77b4", text=df["used_pct"].round(0).astype(int),
                                 textposition="outside"))
            fig.add_trace(go.Bar(name="Utilization %", x=df["gpu_type"], y=df["utilization_pct"],
                                 marker_color="#2ca02c", text=df["utilization_pct"].round(0).astype(int),
                                 textposition="outside"))
            waste = result.get("waste_gap_pct", 0)
            color = "#d62728" if waste > 25 else "#ff7f0e" if waste > 10 else "#2ca02c"
            fig.update_layout(
                title=f"<b>{team}</b> — Efficiency by GPU Type  <span style='color:{color}'>(waste: {waste}%)</span>",
                barmode="group", template="plotly_dark", height=450,
                legend=dict(orientation="h", y=1.08, x=0.5, xanchor="center"),
            )
            return fig

        elif tool_name == "get_waste_analysis" and "wasteful_allocations" in result:
            records = result["wasteful_allocations"][:10]
            if not records:
                return None
            df = pd.DataFrame(records)
            df["label"] = df["team"] + "\n" + df["gpu_type"]
            fig = go.Figure()
            fig.add_trace(go.Bar(
                x=df["label"], y=df["waste_gap_pct"],
                marker_color=[("#d62728" if w > 30 else "#ff7f0e" if w > 20 else "#f0c040") for w in df["waste_gap_pct"]],
                text=[f"{w:.0f}%" for w in df["waste_gap_pct"]],
                textposition="outside",
            ))
            fig.update_layout(
                title=f"<b>Top {len(df)} Wasteful GPU Allocations</b> — allocated but idle",
                yaxis_title="Waste Gap %", template="plotly_dark", height=450,
                xaxis_tickangle=45,
            )
            return fig

        elif tool_name == "get_peak_hours" and "hourly_breakdown" in result:
            df = pd.DataFrame(result["hourly_breakdown"])
            peak = result.get("peak_hour", 0)
            best = result.get("best_hour_to_schedule", 0)
            colors = []
            for h in df["hour"]:
                if h == peak:
                    colors.append("#d62728")
                elif h == best:
                    colors.append("#2ca02c")
                else:
                    colors.append("#4682b4")
            fig = go.Figure()
            fig.add_trace(go.Bar(
                x=[f"{int(h):02d}:00" for h in df["hour"]], y=df["gpu_hours"],
                marker_color=colors,
                text=[f"{v:.0f}" for v in df["gpu_hours"]],
                textposition="outside",
            ))
            fig.add_annotation(x=f"{peak:02d}:00", y=df[df["hour"] == peak]["gpu_hours"].values[0],
                               text="PEAK", showarrow=True, arrowhead=2, font=dict(color="#d62728", size=14))
            fig.add_annotation(x=f"{best:02d}:00", y=df[df["hour"] == best]["gpu_hours"].values[0],
                               text="SCHEDULE HERE", showarrow=True, arrowhead=2, font=dict(color="#2ca02c", size=14))
            fig.update_layout(
                title=f"<b>GPU Load by Hour</b> — best time: <span style='color:#2ca02c'>{best:02d}:00</span>",
                yaxis_title="Avg GPU Hours", template="plotly_dark", height=450,
            )
            return fig

        elif tool_name == "get_weekend_usage" and "team_summary" in result:
            df = pd.DataFrame(result["team_summary"])
            if df.empty:
                return None
            overall = result.get("overall_weekend_utilization_pct", 0)
            fig = go.Figure()
            fig.add_trace(go.Bar(
                x=df["team"], y=df["avg_utilization_pct"],
                marker_color=[("#2ca02c" if u > 40 else "#ff7f0e" if u > 25 else "#d62728") for u in df["avg_utilization_pct"]],
                text=[f"{v:.0f}%" for v in df["avg_utilization_pct"]],
                textposition="outside",
            ))
            fig.add_hline(y=overall, line_dash="dash", line_color="white",
                          annotation_text=f"Avg: {overall}%", annotation_position="top right")
            fig.update_layout(
                title=f"<b>Weekend GPU Utilization</b> — org average: {overall}%",
                yaxis_title="Utilization %", template="plotly_dark", height=450,
            )
            return fig

        elif tool_name == "get_trend" and "daily" in result:
            df = pd.DataFrame(result["daily"])
            metric = result.get("metric", "utilization_pct")
            direction = result.get("trend_direction", "stable")
            arrow = {"increasing": "trending up", "decreasing": "trending down", "stable": "stable"}
            color = {"increasing": "#2ca02c", "decreasing": "#d62728", "stable": "#ff7f0e"}
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=df["date"], y=df[metric], mode="lines+markers",
                line=dict(color=color.get(direction, "#4682b4"), width=3),
                marker=dict(size=5),
                fill="tozeroy", fillcolor=f"rgba(70,130,180,0.1)",
            ))
            avg = result.get("avg_value", 0)
            fig.add_hline(y=avg, line_dash="dot", line_color="white",
                          annotation_text=f"Avg: {avg}%", annotation_position="top right")
            fig.update_layout(
                title=f"<b>30-Day {metric.replace('_', ' ').title()}</b> — {arrow.get(direction, direction)}",
                yaxis_title=metric.replace("_", " ").title() + " %",
                template="plotly_dark", height=450,
            )
            return fig

        elif tool_name == "get_cloud_distribution" and "distribution" in result:
            df = pd.DataFrame(result["distribution"])
            if df.empty:
                return None
            fig = go.Figure()
            fig.add_trace(go.Bar(name="Total", x=df["cloud"], y=df["total_gpus"],
                                 marker_color=[{"AWS": "#FF9900"}.get(c, "#888") for c in df["cloud"]],
                                 text=df["total_gpus"], textposition="outside"))
            fig.add_trace(go.Bar(name="Allocated", x=df["cloud"], y=df["allocated_gpus"],
                                 marker_color=[{"AWS": "#cc7a00"}.get(c, "#666") for c in df["cloud"]],
                                 text=df["allocated_gpus"], textposition="outside"))
            fig.update_layout(
                title=f"<b>GPU Distribution by Cloud</b> — {result.get('total_gpus', '?')} total",
                barmode="group", template="plotly_dark", height=450,
                legend=dict(orientation="h", y=1.08, x=0.5, xanchor="center"),
            )
            return fig

        elif tool_name == "get_queue_status" and "cluster_queue" in result:
            cq = result["cluster_queue"]
            lqs = result.get("local_queues", [])
            labels = [cq.get("name", "cluster")] + [lq["name"] for lq in lqs]
            pending = [cq.get("pending_workloads", 0)] + [lq.get("pending", 0) for lq in lqs]
            admitted = [cq.get("admitted_workloads", 0)] + [lq.get("admitted", 0) for lq in lqs]
            fig = go.Figure()
            fig.add_trace(go.Bar(name="Admitted", x=labels, y=admitted, marker_color="#2ca02c",
                                 text=admitted, textposition="outside"))
            fig.add_trace(go.Bar(name="Pending", x=labels, y=pending, marker_color="#ff7f0e",
                                 text=pending, textposition="outside"))
            fig.update_layout(
                title="<b>Kueue Queue Status</b>",
                barmode="group", template="plotly_dark", height=400,
                legend=dict(orientation="h", y=1.08, x=0.5, xanchor="center"),
            )
            return fig

        elif tool_name == "get_workload_status" and "workloads" in result:
            workloads = result.get("workloads", [])
            if not workloads:
                by = result.get("by_status", {})
                labels = list(by.keys())
                values = list(by.values())
                colors = {"admitted": "#2ca02c", "pending": "#ff7f0e", "preempted": "#d62728"}
                fig = go.Figure(data=[go.Bar(
                    x=labels, y=values,
                    marker_color=[colors.get(l, "#888") for l in labels],
                    text=values, textposition="outside",
                )])
                fig.update_layout(
                    title="<b>Workload Status</b> — no workloads",
                    yaxis_title="Count", template="plotly_dark", height=400,
                )
                return fig
            # Per-workload bar: GPU requests colored by status
            names = [w["name"][:25] for w in workloads]
            gpus = [w.get("gpu_requests", 0) for w in workloads]
            status_colors = {"admitted": "#2ca02c", "pending": "#ff7f0e", "preempted": "#d62728"}
            colors_list = [status_colors.get(w.get("status", ""), "#888") for w in workloads]
            hover = [
                f"{w['name']}<br>{w.get('namespace','')}<br>Status: {w.get('status','')}<br>Priority: {w.get('priority','')}"
                for w in workloads
            ]
            fig = go.Figure(data=[go.Bar(
                x=names, y=gpus,
                marker_color=colors_list,
                text=[w.get("status", "") for w in workloads],
                textposition="outside",
                hovertext=hover, hoverinfo="text",
            )])
            qctx = result.get("queue_context", {})
            quota = qctx.get("gpu_quota", 0)
            if quota:
                fig.add_hline(y=quota, line_dash="dash", line_color="white",
                              annotation_text=f"Quota: {quota} GPU(s)", annotation_position="top right")
            fig.update_layout(
                title=f"<b>Workloads</b> — {len(workloads)} total",
                yaxis_title="GPU Requests", template="plotly_dark", height=400,
            )
            return fig

        elif tool_name == "get_gpu_health" and "gpus" in result:
            gpus = result["gpus"]
            if not gpus:
                return None
            df = pd.DataFrame(gpus)
            status_colors = {"healthy": "#2ca02c", "idle": "#4682b4", "warm": "#ff7f0e", "hot": "#d62728"}
            fig = go.Figure()
            fig.add_trace(go.Bar(
                x=[f"GPU-{g['gpu_index']}<br>{g['node'][-15:]}" for g in gpus],
                y=df["temperature_c"],
                marker_color=[status_colors.get(g["status"], "#888") for g in gpus],
                text=[f"{t}°C" for t in df["temperature_c"]],
                textposition="outside",
                name="Temperature",
            ))
            fig.add_hline(y=85, line_dash="dash", line_color="#d62728",
                          annotation_text="Hot threshold", annotation_position="top right")
            fig.update_layout(
                title="<b>GPU Health — Temperature</b>",
                yaxis_title="Temperature (°C)", template="plotly_dark", height=400,
            )
            return fig

    except Exception:
        return None
    return None


# ── Text formatting ──────────────────────────────────────────────────

def _format_result(tool_name: str, result: dict) -> str:
    """Format tool result as readable markdown."""
    lines = []

    if tool_name == "get_gpu_inventory":
        s = result.get("summary", {})
        lines.append(f"**GPU Inventory:** {s.get('total_gpus', '?')} total, {s.get('allocated_gpus', '?')} allocated ({s.get('used_pct', '?')}% used)")
        for row in result.get("inventory", [])[:8]:
            lines.append(f"- {row['gpu_type']} / {row['cloud']}: **{row['total_gpus']}** total, {row['allocated_gpus']} allocated")

    elif tool_name == "get_team_efficiency":
        waste = result.get("waste_gap_pct", 0)
        icon = "🔴" if waste > 25 else "🟡" if waste > 10 else "🟢"
        lines.append(f"**{result.get('team', '?')}** — {icon} {waste}% waste gap")
        lines.append(f"- Used: **{result.get('avg_used_pct')}%** | Utilization: **{result.get('avg_utilization_pct')}%** | GPUs: **{result.get('total_gpus')}**")
        if waste > 20:
            lines.append(f"\n💡 **Recommendation:** Review committed allocations — {waste}% of reserved GPUs are sitting idle.")

    elif tool_name == "get_waste_analysis":
        count = result.get("wasteful_count", 0)
        lines.append(f"**{count} wasteful allocations** found (>{result.get('threshold_pct')}% waste)")
        for row in result.get("wasteful_allocations", [])[:5]:
            lines.append(f"- **{row['team']}** / {row['gpu_type']} ({row['workload_type']}): **{row['waste_gap_pct']}%** waste")
        if count > 0:
            top = result["wasteful_allocations"][0]
            lines.append(f"\n💡 **Start here:** {top['team']}'s {top['gpu_type']} {top['workload_type']} allocation has the highest waste at {top['waste_gap_pct']}%.")

    elif tool_name == "get_peak_hours":
        lines.append(f"**Peak hour:** {result.get('peak_hour')}:00 ({result.get('peak_hour_gpu_hours', 0):.0f} avg GPU-hrs)")
        lines.append(f"**Peak day:** {result.get('peak_day')}")
        lines.append(f"\n✅ **Best time to schedule:** **{result.get('best_day_to_schedule')} at {result.get('best_hour_to_schedule')}:00**")
        lines.append("Jobs submitted during off-peak hours get scheduled faster and are less likely to be preempted.")

    elif tool_name == "get_weekend_usage":
        overall = result.get("overall_weekend_utilization_pct", 0)
        lines.append(f"**Weekend utilization:** {overall}% overall")
        for row in result.get("team_summary", []):
            icon = "🟢" if row["avg_utilization_pct"] > 40 else "🟡" if row["avg_utilization_pct"] > 25 else "🔴"
            lines.append(f"- {icon} {row['team']}: **{row['avg_utilization_pct']}%** util")
        if overall < 30:
            lines.append(f"\n💡 **Opportunity:** Weekend utilization is only {overall}% — great time for batch/training jobs.")

    elif tool_name == "get_trend":
        direction = result.get("trend_direction", "stable")
        icon = {"increasing": "📈", "decreasing": "📉", "stable": "➡️"}
        lines.append(f"{icon.get(direction, '')} **30-day trend ({result.get('metric', '?')}):** {direction}")
        lines.append(f"- Average: **{result.get('avg_value')}%** | Range: {result.get('min_value')}% – {result.get('max_value')}%")
        lines.append(f"- First half: {result.get('first_half_avg')}% → Second half: {result.get('second_half_avg')}%")

    elif tool_name == "get_cloud_distribution":
        lines.append(f"**{result.get('total_gpus')} GPUs** across clouds:")
        for row in result.get("distribution", []):
            lines.append(f"- **{row['cloud']}**: {row['total_gpus']} GPUs ({row['avg_utilization_pct']}% util)")

    elif tool_name == "get_queue_status":
        cq = result.get("cluster_queue", {})
        lines.append(f"**Queue:** {cq.get('name', 'gpu-cluster-queue')}")
        lines.append(f"- Pending: **{cq.get('pending_workloads', 0)}** | Admitted: **{cq.get('admitted_workloads', 0)}** | GPU quota: **{cq.get('nominal_quota', {}).get('gpu', '?')}**")
        for lq in result.get("local_queues", []):
            lines.append(f"- {lq['namespace']}/{lq['name']}: {lq.get('pending', 0)} pending, {lq.get('admitted', 0)} admitted")
        lines.append(f"\n{result.get('summary', '')}")

    elif tool_name == "get_workload_status":
        by = result.get("by_status", {})
        qctx = result.get("queue_context", {})
        lines.append(f"**{result.get('total_workloads', 0)} workloads** — {by.get('admitted', 0)} admitted, {by.get('pending', 0)} pending, {by.get('preempted', 0)} preempted")
        if qctx:
            lines.append(f"GPU quota: **{qctx.get('gpu_admitted', 0)}/{qctx.get('gpu_quota', '?')}** used, **{qctx.get('gpu_available', 0)}** available")
        for w in result.get("workloads", [])[:8]:
            icon = "🟢" if w["status"] == "admitted" else "🟡" if w["status"] == "pending" else "🔴"
            status_line = f"- {icon} **{w['name']}** ({w['namespace']}) — {w['status']}, {w.get('gpu_requests', 0)} GPU(s)"
            if w.get("priority"):
                status_line += f", priority: {w['priority']}"
            lines.append(status_line)
            if w.get("pending_reason"):
                lines.append(f"  ↳ *{w['pending_reason']}*")
        if result.get("recent_events"):
            lines.append("\n**Recent events:**")
            for ev in result["recent_events"][:3]:
                lines.append(f"- {ev['reason']}: {ev['message'][:100]}")

    elif tool_name == "get_gpu_health":
        summary = result.get("summary", {})
        lines.append(f"**{summary.get('total', 0)} GPUs** — {summary.get('healthy', 0)} healthy, {summary.get('idle', 0)} idle, {summary.get('hot', 0)} hot/warm")
        for g in result.get("gpus", []):
            icon = {"healthy": "🟢", "idle": "🔵", "warm": "🟡", "hot": "🔴"}.get(g["status"], "⚪")
            lines.append(f"- {icon} GPU-{g['gpu_index']} ({g['node'][-20:]}): {g['utilization_pct']}% util, {g['temperature_c']}°C, {g['power_watts']}W, {g['memory_used_mib']}/{g['memory_used_mib']+g['memory_free_mib']:.0f} MiB")

    return "\n".join(lines)


# ── Direct mode (no LLM) ────────────────────────────────────────────

def _detect_params(query: str) -> dict:
    params = {}
    q = query.lower()
    for keyword, team_name in TEAM_NAMES.items():
        if keyword in q:
            params["team"] = team_name
            break
    for keyword, gpu_name in GPU_TYPE_NAMES.items():
        if keyword in q:
            params["gpu_type"] = gpu_name
            break
    return params


def _call_direct(user_message: str) -> tuple[str, go.Figure | None]:
    import gpu_tools

    query = user_message.lower()
    detected = _detect_params(user_message)

    # Team-specific efficiency query
    if "team" in detected:
        for keywords, _, _ in KEYWORD_TOOL_MAP:
            if any(kw in query for kw in keywords):
                break
        else:
            tool_name = "get_team_efficiency"
            kwargs = {"team": detected["team"]}
            if "gpu_type" in detected:
                kwargs["gpu_type"] = detected["gpu_type"]
            result = gpu_tools.TOOL_REGISTRY[tool_name](**kwargs)
            return _format_result(tool_name, result), _build_chart(tool_name, result)

    # Keyword matching
    for keywords, tool_name, default_kwargs in KEYWORD_TOOL_MAP:
        if any(kw in query for kw in keywords):
            kwargs = dict(default_kwargs)
            fn = gpu_tools.TOOL_REGISTRY[tool_name]
            sig = inspect.signature(fn)
            for key in ("team", "gpu_type"):
                if key in detected and key in sig.parameters:
                    kwargs[key] = detected[key]
            result = fn(**kwargs)
            return _format_result(tool_name, result), _build_chart(tool_name, result)

    # Team fallback
    if "team" in detected:
        result = gpu_tools.TOOL_REGISTRY["get_team_efficiency"](team=detected["team"])
        return _format_result("get_team_efficiency", result), _build_chart("get_team_efficiency", result)

    # Default: inventory
    result = gpu_tools.get_gpu_inventory()
    text = _format_result("get_gpu_inventory", result)
    return f"Here's the current GPU inventory:\n\n{text}", _build_chart("get_gpu_inventory", result)


# ── LlamaStack mode ─────────────────────────────────────────────────

def _call_llamastack(user_message: str) -> tuple[str, go.Figure | None]:
    from openai import OpenAI

    client = OpenAI(base_url=f"{LLAMA_STACK_ENDPOINT}/v1", api_key="not-needed")

    input_messages = []
    recent = st.session_state.get("chat_messages", [])[-6:]
    for msg in recent:
        input_messages.append({"role": msg["role"], "content": msg["content"]})
    input_messages.append({"role": "user", "content": user_message})

    response = client.responses.create(
        model=LLAMA_STACK_MODEL,
        input=input_messages,
        instructions=SYSTEM_PROMPT,
        tools=[{
            "type": "mcp",
            "server_label": "gpu-data",
            "server_url": MCP_SERVER_URL,
            "require_approval": "never",
        }],
        parallel_tool_calls=True,
        stream=False,
    )

    text_parts = []
    tool_results = []
    for item in response.output:
        if item.type == "message":
            for content in item.content:
                if hasattr(content, "text"):
                    text_parts.append(content.text)
        elif item.type == "mcp_call_output":
            try:
                parsed = json.loads(item.output) if isinstance(item.output, str) else item.output
                tool_name = getattr(item, "name", "") or ""
                tool_results.append((tool_name, parsed))
            except (json.JSONDecodeError, AttributeError, TypeError):
                pass

    response_text = "\n".join(text_parts) or "I queried the data but couldn't generate a summary. Try rephrasing."
    chart = None
    for tool_name, tool_data in tool_results:
        chart = _build_chart(tool_name, tool_data)
        if chart:
            break

    return response_text, chart


# ══════════════════════════════════════════════════════════════════════
# MAIN RENDER — Input → Answer → Chart (vertical flow)
# ══════════════════════════════════════════════════════════════════════

def _render_suggested_questions():
    """Render suggested questions as clickable buttons."""
    st.markdown("#### Try asking")
    for category, prompts in EXAMPLE_CATEGORIES.items():
        st.markdown(f"**{category}**")
        for prompt_text in prompts:
            if st.button(prompt_text, key=f"ex_{hash(prompt_text)}", use_container_width=True):
                st.session_state["_pending_prompt"] = prompt_text
                st.rerun()
        st.markdown("")


def render_gpu_assistant():
    """Render the GPU Assistant page — left: answer+chart, right: suggested questions."""

    # Init state
    if "chat_messages" not in st.session_state:
        st.session_state.chat_messages = []
    if "last_chart" not in st.session_state:
        st.session_state.last_chart = None

    # ── Input bar ───────────────────────────────────────────────────
    pending = st.session_state.pop("_pending_prompt", None)
    typed = st.chat_input("Ask about GPUs...", key="gpu_chat_input")
    prompt = pending or typed

    if prompt:
        st.session_state.chat_messages.append({"role": "user", "content": prompt})

        try:
            response_text, chart = _call_llamastack(prompt)
        except Exception:
            response_text, chart = _call_direct(prompt)

        st.session_state.chat_messages.append({"role": "assistant", "content": response_text})

        if chart is not None:
            st.session_state.last_chart = chart

        st.rerun()

    # ── Two-column layout: left = answer + chart, right = suggestions ─
    main_col, suggest_col = st.columns([3, 1])

    with suggest_col:
        _render_suggested_questions()

    with main_col:
        if st.session_state.chat_messages:
            # Find last user question + assistant answer
            messages = st.session_state.chat_messages
            last_user = None
            last_assistant = None
            for msg in reversed(messages):
                if msg["role"] == "assistant" and last_assistant is None:
                    last_assistant = msg["content"]
                elif msg["role"] == "user" and last_user is None:
                    last_user = msg["content"]
                if last_user and last_assistant:
                    break

            if last_user:
                st.markdown(
                    f'<div style="background:#1a1a2e;border-radius:8px;padding:10px 16px;margin-bottom:8px">'
                    f'<span style="color:#9ca3af;font-size:0.85em">You asked:</span><br>'
                    f'<span style="font-size:1.05em">{last_user}</span></div>',
                    unsafe_allow_html=True,
                )

            if last_assistant:
                st.markdown(
                    f'<div style="background:#0f2027;border-left:3px solid #2ca02c;'
                    f'border-radius:6px;padding:12px 18px;margin-bottom:12px">'
                    f'{last_assistant}</div>',
                    unsafe_allow_html=True,
                )

            # Chart
            if st.session_state.last_chart is not None:
                st.plotly_chart(st.session_state.last_chart, use_container_width=True, key="main_chart")

            # Previous conversation (collapsed)
            if len(messages) > 2:
                with st.expander(f"Conversation history ({len(messages) // 2} exchanges)"):
                    for msg in messages[:-2]:
                        with st.chat_message(msg["role"]):
                            st.markdown(msg["content"])

        else:
            # Empty state
            st.markdown(
                '<div style="display:flex;align-items:center;justify-content:center;'
                'height:300px;border:1px dashed #444;border-radius:12px;color:#666;font-size:1.1em">'
                'Ask a question or click a suggestion to get started</div>',
                unsafe_allow_html=True,
            )
