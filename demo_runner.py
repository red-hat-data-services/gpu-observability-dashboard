"""
Demo Scenario Runner
=====================
Creates test GPU workloads via Kueue to demonstrate scheduling,
preemption, and queue behavior. Live event log for observability.
"""

import json
import logging
import time
from datetime import datetime

import streamlit as st

import data_live

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Job templates
# ---------------------------------------------------------------------------

_JOB_TEMPLATE = {
    "apiVersion": "batch/v1",
    "kind": "Job",
    "metadata": {},
    "spec": {
        "suspend": True,
        "backoffLimit": 0,
        "template": {
            "spec": {
                "restartPolicy": "Never",
                "containers": [{
                    "name": "gpu-test",
                    "image": "registry.access.redhat.com/ubi9/ubi-minimal:latest",
                    "command": ["sleep", "120"],
                    "resources": {
                        "requests": {"nvidia.com/gpu": "1"},
                        "limits": {"nvidia.com/gpu": "1"},
                    },
                }],
            },
        },
    },
}


def _make_job(name: str, namespace: str, queue: str, priority: str, gpus: int = 1, duration: int = 120) -> dict:
    """Build a Job manifest."""
    import copy
    job = copy.deepcopy(_JOB_TEMPLATE)
    job["metadata"] = {
        "name": name,
        "namespace": namespace,
        "labels": {"kueue.x-k8s.io/queue-name": queue, "app": "gpu-demo"},
    }
    job["spec"]["template"]["spec"]["priorityClassName"] = priority
    job["spec"]["template"]["spec"]["containers"][0]["command"] = ["sleep", str(duration)]
    job["spec"]["template"]["spec"]["containers"][0]["resources"]["requests"]["nvidia.com/gpu"] = str(gpus)
    job["spec"]["template"]["spec"]["containers"][0]["resources"]["limits"]["nvidia.com/gpu"] = str(gpus)
    return job


# ---------------------------------------------------------------------------
# K8s operations
# ---------------------------------------------------------------------------


def _create_job(job: dict) -> str:
    """Create a Job via K8s API. Returns status message."""
    ns = job["metadata"]["namespace"]
    name = job["metadata"]["name"]
    try:
        import requests as req
        base = data_live._k8s_base()
        r = req.post(
            f"{base}/apis/batch/v1/namespaces/{ns}/jobs",
            headers={**data_live._k8s_headers(), "Content-Type": "application/json"},
            json=job,
            verify=data_live._ca_bundle(),
            timeout=10,
        )
        if r.status_code in (200, 201):
            return f"Created {ns}/{name}"
        elif r.status_code == 409:
            return f"Already exists: {ns}/{name}"
        else:
            return f"Failed {ns}/{name}: {r.status_code} {r.text[:100]}"
    except Exception as e:
        return f"Error creating {ns}/{name}: {e}"


def _delete_job(name: str, namespace: str) -> str:
    """Delete a Job via K8s API."""
    try:
        import requests as req
        base = data_live._k8s_base()
        r = req.delete(
            f"{base}/apis/batch/v1/namespaces/{ns}/jobs/{name}",
            headers=data_live._k8s_headers(),
            params={"propagationPolicy": "Background"},
            verify=data_live._ca_bundle(),
            timeout=10,
        )
        if r.status_code in (200, 202):
            return f"Deleted {namespace}/{name}"
        elif r.status_code == 404:
            return f"Not found: {namespace}/{name}"
        else:
            return f"Failed to delete {namespace}/{name}: {r.status_code}"
    except Exception as e:
        return f"Error deleting {namespace}/{name}: {e}"


def _delete_demo_jobs(namespace: str) -> list[str]:
    """Delete all jobs with label app=gpu-demo in a namespace."""
    results = []
    try:
        import requests as req
        base = data_live._k8s_base()
        r = req.get(
            f"{base}/apis/batch/v1/namespaces/{namespace}/jobs",
            headers=data_live._k8s_headers(),
            params={"labelSelector": "app=gpu-demo"},
            verify=data_live._ca_bundle(),
            timeout=10,
        )
        if r.status_code == 200:
            for job in r.json().get("items", []):
                name = job["metadata"]["name"]
                dr = req.delete(
                    f"{base}/apis/batch/v1/namespaces/{namespace}/jobs/{name}",
                    headers=data_live._k8s_headers(),
                    params={"propagationPolicy": "Background"},
                    verify=data_live._ca_bundle(),
                    timeout=10,
                )
                results.append(f"Deleted {namespace}/{name}" if dr.status_code in (200, 202) else f"Failed {namespace}/{name}")
    except Exception as e:
        results.append(f"Error: {e}")
    return results


def _get_recent_events(namespace: str, limit: int = 15) -> list[dict]:
    """Get recent events from a namespace."""
    try:
        events = data_live._k8s_get(f"/api/v1/namespaces/{namespace}/events?limit=50")
        items = events.get("items", [])
        # Sort by last timestamp descending
        items.sort(key=lambda e: e.get("lastTimestamp") or e.get("eventTime") or "", reverse=True)
        result = []
        for ev in items[:limit]:
            ts = ev.get("lastTimestamp") or ev.get("eventTime") or ""
            if ts and "T" in ts:
                ts = ts.split("T")[1][:8]  # HH:MM:SS
            result.append({
                "time": ts,
                "type": ev.get("type", ""),
                "reason": ev.get("reason", ""),
                "object": ev.get("involvedObject", {}).get("name", ""),
                "message": ev.get("message", "")[:80],
            })
        return result
    except Exception:
        return []


# ---------------------------------------------------------------------------
# Test scenarios
# ---------------------------------------------------------------------------

SCENARIOS = {
    "P1 job → team-alpha": {
        "description": "Submit 1 high-priority job (1 GPU) to team-alpha",
        "jobs": [
            {"name": "demo-p1-alpha-{ts}", "namespace": "team-alpha",
             "queue": "team-alpha-queue", "priority": "high-priority", "gpus": 1},
        ],
    },
    "P2 job → team-beta": {
        "description": "Submit 1 low-priority job (1 GPU) to team-beta",
        "jobs": [
            {"name": "demo-p2-beta-{ts}", "namespace": "team-beta",
             "queue": "team-beta-queue", "priority": "low-priority", "gpus": 1},
        ],
    },
    "Preemption test": {
        "description": "Submit P2 to team-beta first, then P1 to team-alpha — P1 should preempt P2",
        "jobs": [
            {"name": "demo-victim-{ts}", "namespace": "team-beta",
             "queue": "team-beta-queue", "priority": "low-priority", "gpus": 1},
            {"name": "demo-preempt-{ts}", "namespace": "team-alpha",
             "queue": "team-alpha-queue", "priority": "high-priority", "gpus": 1, "delay": 5},
        ],
    },
    "Fill queue": {
        "description": "Submit 2 jobs to team-alpha — second should stay pending (quota=1)",
        "jobs": [
            {"name": "demo-fill-1-{ts}", "namespace": "team-alpha",
             "queue": "team-alpha-queue", "priority": "high-priority", "gpus": 1},
            {"name": "demo-fill-2-{ts}", "namespace": "team-alpha",
             "queue": "team-alpha-queue", "priority": "high-priority", "gpus": 1},
        ],
    },
}


# ---------------------------------------------------------------------------
# Streamlit UI
# ---------------------------------------------------------------------------


def render_demo_panel():
    """Render the demo scenario runner in the sidebar."""
    st.sidebar.markdown("---")
    st.sidebar.markdown("### Test Scenarios")
    st.sidebar.caption("Submit GPU workloads to test Kueue scheduling")

    ts = str(int(time.time()))[-5:]

    # Scenario buttons
    for scenario_name, scenario in SCENARIOS.items():
        st.sidebar.markdown(f"**{scenario_name}**")
        st.sidebar.caption(scenario["description"])
        if st.sidebar.button(f"Run: {scenario_name}", key=f"demo_{hash(scenario_name)}"):
            log_lines = []
            for job_spec in scenario["jobs"]:
                delay = job_spec.pop("delay", 0)
                if delay:
                    log_lines.append(f"Waiting {delay}s before next job...")
                    st.session_state["demo_log"] = log_lines.copy()
                    time.sleep(delay)

                name = job_spec["name"].format(ts=ts)
                job = _make_job(
                    name=name,
                    namespace=job_spec["namespace"],
                    queue=job_spec["queue"],
                    priority=job_spec["priority"],
                    gpus=job_spec.get("gpus", 1),
                )
                result = _create_job(job)
                log_lines.append(f"{datetime.now().strftime('%H:%M:%S')} {result}")

            st.session_state["demo_log"] = log_lines
            st.rerun()

    # Clean up
    st.sidebar.markdown("---")
    if st.sidebar.button("Clean up all demo jobs", key="demo_cleanup"):
        log_lines = []
        for ns in ["team-alpha", "team-beta"]:
            results = _delete_demo_jobs(ns)
            log_lines.extend(f"{datetime.now().strftime('%H:%M:%S')} {r}" for r in results)
        if not log_lines:
            log_lines.append(f"{datetime.now().strftime('%H:%M:%S')} No demo jobs found")
        st.session_state["demo_log"] = log_lines
        st.rerun()

    # Auto-refresh
    st.sidebar.markdown("---")
    auto_refresh = st.sidebar.checkbox("Auto-refresh (10s)", key="demo_auto_refresh")
    if st.sidebar.button("Refresh now", key="demo_refresh"):
        st.cache_data.clear()
        st.rerun()

    # Live log
    if st.session_state.get("demo_log"):
        st.sidebar.markdown("---")
        st.sidebar.markdown("#### Activity Log")
        for line in st.session_state["demo_log"]:
            st.sidebar.text(line)

    # Recent events from team namespaces
    st.sidebar.markdown("---")
    st.sidebar.markdown("#### Recent Events")
    all_events = []
    for ns in ["team-alpha", "team-beta"]:
        all_events.extend(_get_recent_events(ns, limit=8))
    all_events.sort(key=lambda e: e["time"], reverse=True)

    if all_events:
        for ev in all_events[:10]:
            icon = "🟢" if ev["type"] == "Normal" else "🟡"
            st.sidebar.markdown(
                f'<div style="font-size:0.78em;margin-bottom:4px">'
                f'{icon} <b>{ev["time"]}</b> {ev["reason"]}: {ev["message"]}</div>',
                unsafe_allow_html=True,
            )
    else:
        st.sidebar.caption("No recent events")

    # Auto-refresh implementation
    if auto_refresh:
        time.sleep(10)
        st.cache_data.clear()
        st.rerun()
