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
    (["cloud", "aws", "gcp", "ibm", "distribution", "where are", "which cloud"], "get_cloud_distribution", {}),
    (["fail", "preempt", "evict", "kill", "why did", "what happened", "error", "pending", "stuck"], "get_waste_analysis", {"min_waste_pct": 15}),
]

TEAM_NAMES = {
    "ml platform": "ML Platform", "ai research": "AI Research",
    "data science": "Data Science", "engineering": "Engineering",
    "customer analytics": "Customer Analytics",
}

GPU_TYPE_NAMES = {
    "l4": "L4", "t4": "T4", "a100-40": "A100-40GB", "a100 40": "A100-40GB",
    "a100-80": "A100-80GB", "a100 80": "A100-80GB", "a100": "A100-80GB",
    "h100": "H100", "h200": "H200", "b200": "B200",
}

SYSTEM_PROMPT = """\
You are a GPU infrastructure analyst for the AIPCC GPU-as-a-Service platform.
You help engineers, team leads, directors, and FinOps understand GPU allocation,
utilization, waste, scheduling, and usage patterns across AWS, GCP, and IBM Cloud.

ALWAYS use the available tools to query data before answering. Never guess numbers.
When reporting metrics, explain what they mean and suggest actionable next steps.
Keep responses concise — 2-4 sentences of insight plus a recommendation.

Key concepts:
- Used% = allocated/total GPUs (reservation rate)
- Utilization% = actual GPU compute load
- Waste = Used% - Utilization% (allocated but idle)
- P1 = guaranteed workloads (cannot be preempted)
- P2 = opportunistic workloads (fully preemptible)
- GPU types ranked by power: B200 > H200 > H100 > A100-80 > A100-40 > T4 > L4
"""

# ── Example prompts — both end-user and executive ────────────────────

EXAMPLE_CATEGORIES = {
    "Scheduling & Jobs": [
        "When should I schedule my batch job?",
        "What are the peak GPU usage hours?",
        "Best time to run a training job on H100?",
        "Is the weekend a good time for long jobs?",
    ],
    "My Team": [
        "How efficient is my team (Engineering)?",
        "Is AI Research wasting H100 GPUs?",
        "Show me Data Science GPU allocation",
        "Compare ML Platform vs Engineering efficiency",
    ],
    "Troubleshooting": [
        "Why might my job be pending?",
        "Which GPUs are most oversubscribed?",
        "Where is the biggest GPU bottleneck?",
        "Are there preemption risks for spot workloads?",
    ],
    "Capacity & Cost": [
        "How many GPUs do we have total?",
        "Where are our H100 GPUs deployed?",
        "Which cloud has the most spare capacity?",
        "Should we buy more B200s or are we underutilizing?",
    ],
    "Trends & Patterns": [
        "Is GPU utilization trending up or down?",
        "How has committed allocation changed this month?",
        "Which teams work on weekends?",
        "Are GPUs idle at night?",
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
                                 marker_color=[{"AWS": "#FF9900", "GCP": "#34A853", "IBM Cloud": "#0F62FE"}.get(c, "#888") for c in df["cloud"]],
                                 text=df["total_gpus"], textposition="outside"))
            fig.add_trace(go.Bar(name="Allocated", x=df["cloud"], y=df["allocated_gpus"],
                                 marker_color=[{"AWS": "#cc7a00", "GCP": "#267a3d", "IBM Cloud": "#0a47b5"}.get(c, "#666") for c in df["cloud"]],
                                 text=df["allocated_gpus"], textposition="outside"))
            fig.update_layout(
                title=f"<b>GPU Distribution by Cloud</b> — {result.get('total_gpus', '?')} total",
                barmode="group", template="plotly_dark", height=450,
                legend=dict(orientation="h", y=1.08, x=0.5, xanchor="center"),
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
# MAIN RENDER — Chat left, Chart right
# ══════════════════════════════════════════════════════════════════════

def render_gpu_assistant():
    """Render the full GPU Assistant page — chat left, chart right."""

    # Init state
    if "chat_messages" not in st.session_state:
        st.session_state.chat_messages = []
    if "last_chart" not in st.session_state:
        st.session_state.last_chart = None

    # ── Layout: left = chat, right = chart ───────────────────────────
    chat_col, chart_col = st.columns([2, 3])

    with chart_col:
        st.markdown("#### Visualization")
        if st.session_state.last_chart is not None:
            st.plotly_chart(st.session_state.last_chart, use_container_width=True, key="main_chart")
        else:
            # Default empty state
            st.markdown(
                '<div style="display:flex; align-items:center; justify-content:center; '
                'height:400px; border:1px dashed #444; border-radius:12px; color:#666; font-size:1.1em;">'
                'Ask a question to generate a chart</div>',
                unsafe_allow_html=True,
            )

    with chat_col:
        st.markdown("#### Chat")

        # Example prompts
        with st.expander("Example questions", expanded=len(st.session_state.chat_messages) == 0):
            for category, prompts in EXAMPLE_CATEGORIES.items():
                st.markdown(f"**{category}**")
                cols = st.columns(2)
                for i, prompt_text in enumerate(prompts):
                    with cols[i % 2]:
                        if st.button(prompt_text, key=f"ex_{hash(prompt_text)}", use_container_width=True):
                            st.session_state["_pending_prompt"] = prompt_text
                            st.rerun()

        # Chat history
        chat_container = st.container(height=420)
        with chat_container:
            for msg in st.session_state.chat_messages:
                with st.chat_message(msg["role"]):
                    st.markdown(msg["content"])

        # Input
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
