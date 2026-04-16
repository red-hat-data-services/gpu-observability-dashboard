# GPU Observability Dashboard + Chatbot — Specification

Machine-parseable spec for implementation. CI validates this matches code.

## Version

```yaml
spec_version: "2.0.0"
last_updated: "2026-04-16"
status: "implemented"
```

---

## Overview

A Streamlit dashboard with an AI chatbot (LlamaStack) that provides GPU infrastructure observability. Three views: GPU Assistant (chat-first), My GPUs (end-user), Executive Dashboard (leadership). All views query **real cluster data** from Thanos/Prometheus and the Kubernetes API.

## Target Cluster

```yaml
cluster: mid-chatbot
api: https://api.mid-chatbot.r3of.p3.openshiftapps.com:443
region: us-east-2
cloud: AWS
thanos: https://thanos-querier-openshift-monitoring.apps.rosa.mid-chatbot.r3of.p3.openshiftapps.com
```

### Real Infrastructure

```yaml
nodes:
  - name: ip-10-0-1-113.us-east-2.compute.internal
    instance_type: g5.12xlarge
    gpus: 4
    gpu_type: NVIDIA A10G
    gpu_uuids:
      - GPU-2825c9f3-b361-b1aa-98d6-fc93fcce478e
      - GPU-6f45d52c-9bde-b32d-49f0-7b5568d41092
      - GPU-bb1a50da-442e-5d21-617e-4cdf589ecd65
      - GPU-d424634f-6103-a6b1-7346-981c74c0a29b
  - name: ip-10-0-1-205.us-east-2.compute.internal
    instance_type: g5.12xlarge
    gpus: 4
    gpu_type: NVIDIA A10G
    gpu_uuids: [] # same structure, UUIDs to be queried

total_gpus: 8
gpu_model: NVIDIA A10G
driver_version: "580.126.20"
```

### Kueue Configuration

```yaml
cluster_queue: gpu-cluster-queue
resource_flavor: a10g-gpu
nominal_quota:
  cpu: "8"
  memory: 32Gi
  nvidia.com/gpu: "1"
preemption:
  within_cluster_queue: LowerPriority
  reclaim_within_cohort: Any
namespace_selector:
  matchLabels:
    demo: gpuaas

priority_classes:
  - name: high-priority
    value: 1000
    preemption: PreemptLowerPriority
  - name: low-priority
    value: 100
    preemption: PreemptLowerPriority

teams:
  - namespace: team-alpha
    local_queue: team-alpha-queue
    priority: high-priority (P1 = guaranteed)
  - namespace: team-beta
    local_queue: team-beta-queue
    priority: low-priority (P2 = opportunistic)
  - namespace: team-gamma
    local_queue: team-gamma-queue
    priority: high-priority (P1 = guaranteed)
  - namespace: team-delta
    local_queue: team-delta-queue
    priority: low-priority (P2 = opportunistic)

demo_namespace: gpuaas-demo
```

### Services on Cluster

```yaml
llamastack:
  namespace: llama-stack-rag
  service: llamastack.llama-stack-rag.svc.cluster.local:8321
  model: meta-llama/Llama-3.1-8B-Instruct
  route: llamastack-midstream-chatbot.apps.rosa.mid-chatbot.r3of.p3.openshiftapps.com

vllm:
  namespace: llama-stack-rag
  service: llama-3-1-8b-instruct-predictor.llama-stack-rag.svc.cluster.local
  gpu_usage: 1x A10G
```

---

## Data Sources

### 1. Thanos/Prometheus (GPU Metrics)

**Endpoint:** Internal `thanos-querier.openshift-monitoring.svc:9091` or external route with bearer token.

**Authentication:** ServiceAccount token mounted in the pod, or `oc whoami -t` for dev.

**Available DCGM Metrics (confirmed live):**

| Metric | Type | Description |
|--------|------|-------------|
| `DCGM_FI_DEV_GPU_UTIL` | gauge | GPU utilization % (0-100) |
| `DCGM_FI_DEV_FB_USED` | gauge | Framebuffer memory used (MiB) |
| `DCGM_FI_DEV_FB_FREE` | gauge | Framebuffer memory free (MiB) |
| `DCGM_FI_DEV_GPU_TEMP` | gauge | GPU temperature (°C) |
| `DCGM_FI_DEV_POWER_USAGE` | gauge | Power draw (watts) |
| `DCGM_FI_DEV_SM_CLOCK` | gauge | SM clock speed (MHz) |
| `DCGM_FI_DEV_MEM_CLOCK` | gauge | Memory clock speed (MHz) |
| `DCGM_FI_DEV_TOTAL_ENERGY_CONSUMPTION` | counter | Cumulative energy (mJ) |
| `DCGM_FI_DEV_PCIE_REPLAY_COUNTER` | counter | PCIe replay errors |

**Labels on all DCGM metrics:**

```
gpu="0"                    # GPU index on node
UUID="GPU-xxxx-..."        # Unique GPU identifier
device="nvidia0"           # Device name
modelName="NVIDIA A10G"    # GPU model
Hostname="ip-10-0-..."     # Node hostname
DCGM_FI_DRIVER_VERSION="580.126.20"
```

**Note:** DCGM metrics are NOT scraped into Thanos by default on this cluster. The DCGM exporter pods are running but the ServiceMonitor doesn't feed into the cluster monitoring stack. Metrics are available directly from DCGM exporter pods on port 9400.

**Workaround for v2.0:** Query DCGM exporter pods directly via their pod IPs, or add a ServiceMonitor to route DCGM metrics into Thanos.

**GPU operator metrics (available in Thanos):**

| Metric | Description |
|--------|-------------|
| `gpu_operator_gpu_nodes_total` | Total GPU nodes |
| `gpu_operator_node_cuda_ready` | CUDA readiness per node |
| `gpu_operator_node_driver_ready` | Driver readiness per node |
| `gpu_operator_node_plugin_ready` | Device plugin readiness |

### 2. Kubernetes API (Kueue + Workloads)

**Queries needed:**

| Resource | API | Purpose |
|----------|-----|---------|
| `nodes` | `v1/nodes?labelSelector=nvidia.com/gpu.present=true` | GPU node inventory |
| `clusterqueues` | `kueue.x-k8s.io/v1beta1` | Queue capacity, pending workloads |
| `localqueues` | `kueue.x-k8s.io/v1beta1` | Per-team queue status |
| `workloads` | `kueue.x-k8s.io/v1beta1` | Active/pending/preempted workloads |
| `pods` | `v1/pods` (filtered by GPU requests) | Running GPU workloads |
| `events` | `v1/events` (filtered by Kueue) | Preemption events, admission events |
| `priorityclasses` | `scheduling.k8s.io/v1` | Priority levels |
| `resourceflavors` | `kueue.x-k8s.io/v1beta1` | GPU type definitions |

**Authentication:** ServiceAccount with RBAC (see Deployment section).

### 3. DCGM Exporter Direct (Fallback)

If Thanos doesn't have DCGM metrics, scrape DCGM exporter pods directly:

```
GET http://<dcgm-exporter-pod-ip>:9400/metrics
```

Pod IPs discovered via: `oc get pods -n nvidia-gpu-operator -l app=nvidia-dcgm-exporter -o jsonpath='{.items[*].status.podIP}'`

---

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│  Streamlit App (:8501)                                       │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │ ○ GPU Assistant  ○ My GPUs  ○ Executive Dashboard       │ │
│  ├───────────────────┬─────────────────────────────────────┤ │
│  │  Chat (left)      │  Chart (right)                      │ │
│  │  Example prompts  │  Generated from query results       │ │
│  │  Conversation     │  Annotated (PEAK, SCHEDULE HERE)    │ │
│  └────────┬──────────┴──────────────┬──────────────────────┘ │
│           │                         │                        │
│    ┌──────▼──────┐           ┌──────▼──────┐                 │
│    │ chat_ui.py  │           │ data_live.py │                │
│    │ LlamaStack  │           │ Thanos query │                │
│    │ or direct   │           │ K8s API      │                │
│    └──────┬──────┘           │ DCGM scrape  │                │
│           │                  └──────┬───────┘                │
│    ┌──────▼──────┐                  │                        │
│    │ gpu_tools.py│◄─────────────────┘                        │
│    │ 7 + 3 tools │  operates on live DataFrames              │
│    └─────────────┘                                           │
└──────────────────────────────────────────────────────────────┘
         │ MCP                        │ HTTP
         ▼                            ▼
┌─────────────────┐          ┌─────────────────────┐
│ MCP Server      │          │ Thanos / Prometheus  │
│ :8330           │          │ openshift-monitoring │
│ 10 tools        │          └─────────────────────┘
└─────────────────┘          ┌─────────────────────┐
         │                   │ Kubernetes API       │
         ▼                   │ Kueue CRDs, nodes,   │
┌─────────────────┐          │ pods, events         │
│ LlamaStack      │          └─────────────────────┘
│ :8321           │
│ Llama 3.1 8B    │
└─────────────────┘
```

---

## Files

### New/Modified Files

| File | Purpose | Status |
|------|---------|--------|
| `data_live.py` | **NEW** — Live data fetcher (Thanos + K8s API). Replaces `generate_*()` functions. | Done |
| `gpu_tools.py` | **MODIFY** — Add 3 new tools for Kueue/job queries. Update existing 7 to use live data. | Done |
| `mcp_server.py` | **MODIFY** — Remove duplicated generate functions, import from data_live.py. Add 3 new MCP tools. | Done |
| `chat_ui.py` | **EXISTS** — Chat-first layout (left=chat, right=chart). Updated for new tools. | Done |
| `user_view.py` | **EXISTS** — End-user page. Updated for live data. | Done |
| `app.py` | **MODIFY** — Replace `generate_*()` calls with `data_live` imports. | Done |
| `k8s/serviceaccount.yaml` | **NEW** — ServiceAccount + RBAC for the dashboard pod. | Done |
| `k8s/servicemonitor.yaml` | **NEW** — Optional: Route DCGM metrics into Thanos. | Done |
| `Dockerfile` | **MODIFY** — Add `requests` package, include data_live.py. | Done |
| `requirements.txt` | **MODIFY** — Add `requests>=2.31.0`. | Done |
| `SPEC.md` | **THIS FILE** — Living spec. | Done |
| `scripts/check_spec.py` | **EXISTS** — Validates spec against code. Passes with 10/10 tools. | Done |
| `.github/workflows/spec-sync.yml` | **EXISTS** — CI spec validation. | Done |

---

## `data_live.py` — Live Data Fetcher

Replaces all 3 `generate_*()` functions with real queries. Returns the same DataFrame schemas so downstream code (gpu_tools.py, visualizations) works unchanged.

### Functions

```python
def get_thanos_client() -> ThanosClient:
    """Create authenticated Thanos client.
    Auth: ServiceAccount token from /var/run/secrets/ or THANOS_TOKEN env var.
    Endpoint: THANOS_URL env var or internal service thanos-querier.openshift-monitoring.svc:9091
    """

def get_k8s_client() -> kubernetes.client.ApiClient:
    """Create K8s client.
    In-cluster: uses mounted ServiceAccount.
    Dev: uses ~/.kube/config.
    """

def fetch_gpu_inventory() -> pd.DataFrame:
    """Query K8s API for GPU nodes + Kueue allocations + DCGM utilization.
    
    Returns DataFrame with same schema as old generate_all_gpu_data():
      cloud, gpu_type, team, workload_type, total_gpus, allocated_gpus,
      used_pct, utilization_pct, idle_pct
    
    Data sources:
      - Nodes API → gpu_type, total_gpus per node
      - Pods API → allocated_gpus (pods requesting nvidia.com/gpu)
      - Kueue LocalQueues → team assignment
      - DCGM_FI_DEV_GPU_UTIL → utilization_pct per GPU
      - Kueue Workloads → workload_type (map priority class to committed/spot)
    
    Mapping:
      - cloud = "AWS" (single cluster)
      - gpu_type = node label nvidia.com/gpu.product
      - team = namespace of the pod requesting GPU (or Kueue localqueue namespace)
      - workload_type = "committed" if high-priority, "spot" if low-priority
      - total_gpus = node capacity nvidia.com/gpu
      - allocated_gpus = count of pods with GPU requests on that node
      - used_pct = (allocated / total) * 100
      - utilization_pct = DCGM_FI_DEV_GPU_UTIL value for that GPU
      - idle_pct = 100 - used_pct
    """

def fetch_timeseries(hours: int = 720) -> pd.DataFrame:
    """Query Thanos range query for 30-day GPU utilization trend.
    
    Returns DataFrame with same schema as old generate_30day_timeseries():
      date, workload_type, used_pct, utilization_pct, day_of_week
    
    PromQL:
      avg(DCGM_FI_DEV_GPU_UTIL) by (Hostname)[30d:1h]
      
    Note: If DCGM metrics aren't in Thanos, fall back to scraping
    DCGM exporters directly and only returning current values
    (no historical trend available).
    
    Fallback: If no historical data, generate synthetic trend 
    anchored to current live values.
    """

def fetch_kueue_status() -> dict:
    """Query Kueue CRDs for current queue state.
    
    Returns:
      {
        "cluster_queue": {
          "name": "gpu-cluster-queue",
          "pending_workloads": int,
          "admitted_workloads": int,
          "nominal_quota": {"gpu": int, "cpu": str, "memory": str},
        },
        "local_queues": [
          {"name": str, "namespace": str, "pending": int, "admitted": int}
        ],
        "workloads": [
          {"name": str, "namespace": str, "status": str, "priority": str,
           "gpu_requests": int, "created": str, "admitted_at": str | None,
           "preempted": bool}
        ],
        "recent_events": [
          {"type": str, "reason": str, "message": str, "timestamp": str,
           "involved_object": str}
        ]
      }
    """

def fetch_hourly_patterns() -> pd.DataFrame:
    """Query Thanos for hourly usage patterns.
    
    Returns DataFrame with same schema as old generate_hourly_usage_patterns():
      team, gpu_type, day_of_week, hour, gpu_hours, utilization_pct
    
    PromQL:
      avg_over_time(DCGM_FI_DEV_GPU_UTIL[1h]) grouped by hour-of-day, day-of-week
    
    Fallback: If insufficient history, use current utilization + 
    synthetic pattern (work hours higher, weekends lower).
    """
```

### Caching

```python
@st.cache_data(ttl=60)  # refresh every 60 seconds
def fetch_gpu_inventory(): ...

@st.cache_data(ttl=300)  # refresh every 5 minutes
def fetch_timeseries(): ...

@st.cache_data(ttl=30)   # refresh every 30 seconds
def fetch_kueue_status(): ...
```

---

## Tools

### Existing Tools (7) — Update to Use Live Data

<!-- SPEC:TOOLS:START -->

### get_gpu_inventory

```yaml
description: "Get real GPU inventory from cluster nodes and DCGM metrics."
source_function: gpu_tools.get_gpu_inventory
params:
  - name: cloud
    type: string | null
    required: false
    enum: ["AWS"]
  - name: gpu_type
    type: string | null
    required: false
    enum: ["NVIDIA A10G"]
returns:
  inventory: list[{gpu_type: str, cloud: str, total_gpus: int, allocated_gpus: int}]
  summary: {total_gpus: int, allocated_gpus: int, used_pct: float}
```

### get_team_efficiency

```yaml
description: "Get Used%, Utilization%, and waste gap for a team."
source_function: gpu_tools.get_team_efficiency
params:
  - name: team
    type: string
    required: true
    enum: ["team-alpha", "team-beta", "llama-stack-rag", "gpuaas-demo"]
  - name: gpu_type
    type: string | null
    required: false
    enum: ["NVIDIA A10G"]
  - name: workload_type
    type: string | null
    required: false
    enum: ["committed", "spot"]
returns:
  team: str
  avg_used_pct: float
  avg_utilization_pct: float
  waste_gap_pct: float
  total_gpus: int
  by_gpu_type: list[{gpu_type: str, used_pct: float, utilization_pct: float, total_gpus: int}]
```

### get_waste_analysis

```yaml
description: "Find GPU allocations with high waste."
source_function: gpu_tools.get_waste_analysis
params:
  - name: min_waste_pct
    type: number
    required: false
    default: 25
returns:
  threshold_pct: float
  wasteful_count: int
  wasteful_allocations: list[{team: str, gpu_type: str, workload_type: str, used_pct: float, utilization_pct: float, total_gpus: int, waste_gap_pct: float}]
```

### get_peak_hours

```yaml
description: "Find hours/days with highest GPU usage and best scheduling times."
source_function: gpu_tools.get_peak_hours
params:
  - name: team
    type: string | null
    required: false
  - name: gpu_type
    type: string | null
    required: false
returns:
  peak_hour: int
  peak_hour_gpu_hours: float
  peak_day: str
  peak_day_gpu_hours: float
  best_hour_to_schedule: int
  best_day_to_schedule: str
  hourly_breakdown: list[{hour: int, gpu_hours: float, utilization_pct: float}]
  daily_breakdown: list[{day_name: str, gpu_hours: float, utilization_pct: float}]
```

### get_weekend_usage

```yaml
description: "Get Saturday/Sunday GPU utilization."
source_function: gpu_tools.get_weekend_usage
params:
  - name: team
    type: string | null
    required: false
  - name: gpu_type
    type: string | null
    required: false
returns:
  overall_weekend_utilization_pct: float
  team_summary: list[{team: str, avg_utilization_pct: float, avg_gpu_hours: float}]
  detail: list[{team: str, day_name: str, gpu_hours: float, utilization_pct: float}]
```

### get_trend

```yaml
description: "Get 30-day utilization or allocation trend."
source_function: gpu_tools.get_trend
params:
  - name: metric
    type: string
    required: false
    default: "utilization_pct"
    enum: ["used_pct", "utilization_pct"]
  - name: workload_type
    type: string | null
    required: false
    enum: ["committed", "spot"]
returns:
  metric: str
  workload_type: str
  avg_value: float
  min_value: float
  max_value: float
  trend_direction: str
  first_half_avg: float
  second_half_avg: float
  daily: list[{date: str, <metric>: float}]
```

### get_cloud_distribution

```yaml
description: "Get GPU distribution across cloud providers."
source_function: gpu_tools.get_cloud_distribution
params:
  - name: team
    type: string | null
    required: false
  - name: gpu_type
    type: string | null
    required: false
returns:
  distribution: list[{cloud: str, total_gpus: int, allocated_gpus: int, avg_used_pct: float, avg_utilization_pct: float}]
  total_gpus: int
```

### get_queue_status

```yaml
description: "Get current Kueue queue status — pending workloads, admitted workloads, queue depth. Use to answer 'why is my job pending?' or 'is the queue busy?'"
source_function: gpu_tools.get_queue_status
params: []
returns:
  cluster_queue:
    name: str
    pending_workloads: int
    admitted_workloads: int
    nominal_quota: {gpu: int}
  local_queues: list[{name: str, namespace: str, pending: int, admitted: int}]
  summary: str  # human-readable status
```

### get_workload_status

```yaml
description: "Get status of Kueue workloads — running, pending, preempted. Use to answer 'why is my job failing?' or 'what happened to my workload?'"
source_function: gpu_tools.get_workload_status
params:
  - name: namespace
    type: string | null
    required: false
    description: "Filter by team namespace"
    enum: ["team-alpha", "team-beta", "gpuaas-demo"]
returns:
  total_workloads: int
  by_status: {admitted: int, pending: int, preempted: int}
  workloads: list[{name: str, namespace: str, status: str, priority: str, gpu_requests: int, created: str, preempted: bool}]
  recent_events: list[{type: str, reason: str, message: str, timestamp: str}]
```

### get_gpu_health

```yaml
description: "Get real-time GPU health — temperature, power, memory, utilization per GPU. Use to answer 'are GPUs healthy?' or 'is any GPU overheating?'"
source_function: gpu_tools.get_gpu_health
params:
  - name: node
    type: string | null
    required: false
    description: "Filter by node hostname"
returns:
  gpus: list[{
    uuid: str, gpu_index: int, node: str, model: str,
    utilization_pct: float, temperature_c: float, power_watts: float,
    memory_used_mib: float, memory_free_mib: float,
    status: str  # "healthy", "warm", "hot", "idle"
  }]
  summary: {total: int, healthy: int, idle: int, hot: int}
```

<!-- SPEC:TOOLS:END -->

---

## Deployment

### ServiceAccount & RBAC

```yaml
# k8s/serviceaccount.yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: gpu-dashboard
  namespace: llama-stack-rag
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: gpu-dashboard-reader
rules:
  - apiGroups: [""]
    resources: ["nodes", "pods", "events", "namespaces"]
    verbs: ["get", "list", "watch"]
  - apiGroups: ["kueue.x-k8s.io"]
    resources: ["clusterqueues", "localqueues", "workloads", "resourceflavors"]
    verbs: ["get", "list", "watch"]
  - apiGroups: ["scheduling.k8s.io"]
    resources: ["priorityclasses"]
    verbs: ["get", "list"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: gpu-dashboard-reader
subjects:
  - kind: ServiceAccount
    name: gpu-dashboard
    namespace: llama-stack-rag
roleRef:
  kind: ClusterRole
  name: gpu-dashboard-reader
  apiGroup: rbac.authorization.k8s.io
```

### Thanos Access

The dashboard pod needs to query Thanos. Options:
1. **In-cluster:** `thanos-querier.openshift-monitoring.svc:9091` with SA token
2. **Requires additional RBAC:** SA needs `get` on `namespaces/metrics` in openshift-monitoring

```yaml
# Additional RBAC for Thanos access
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: gpu-dashboard-monitoring
subjects:
  - kind: ServiceAccount
    name: gpu-dashboard
    namespace: llama-stack-rag
roleRef:
  kind: ClusterRole
  name: cluster-monitoring-view
  apiGroup: rbac.authorization.k8s.io
```

### Deployment Patch

```yaml
# Patch the existing deployment to use the ServiceAccount
spec:
  template:
    spec:
      serviceAccountName: gpu-dashboard
      containers:
        - name: gpu-dashboard
          env:
            - name: THANOS_URL
              value: "https://thanos-querier.openshift-monitoring.svc:9091"
            - name: LLAMA_STACK_ENDPOINT
              value: "http://llamastack.llama-stack-rag.svc.cluster.local:8321"
            - name: LLAMA_STACK_MODEL
              value: "meta-llama/Llama-3.1-8B-Instruct"
            - name: DATA_SOURCE
              value: "live"  # "live" or "mock"
```

### Environment Variables

| Var | Default | Description |
|-----|---------|-------------|
| `DATA_SOURCE` | `mock` | `live` = real cluster data, `mock` = simulated |
| `THANOS_URL` | `https://thanos-querier.openshift-monitoring.svc:9091` | Thanos endpoint |
| `THANOS_TOKEN` | (from SA mount) | Override bearer token |
| `LLAMA_STACK_ENDPOINT` | `http://localhost:8321` | LlamaStack server |
| `LLAMA_STACK_MODEL` | `meta-llama/Llama-3.1-8B-Instruct` | Model ID |
| `MCP_SERVER_URL` | `http://localhost:8330/mcp` | MCP server for LlamaStack |
| `DCGM_EXPORTER_PORT` | `9400` | Port for direct DCGM scraping |

---

## UI Layout

### GPU Assistant (default page)

```
┌───────────────────────────────────────────────────────────────┐
│  GPU Assistant                                                │
│  Ask questions about GPU usage, scheduling, efficiency...     │
├───────────────────────┬───────────────────────────────────────┤
│  Chat (2/5 width)     │  Visualization (3/5 width)            │
│                       │                                       │
│  [Example questions]  │  Chart generated from last query      │
│   ┌ Scheduling       │  - Annotated (PEAK, SCHEDULE HERE)    │
│   ├ My Team          │  - Color-coded severity               │
│   ├ Troubleshooting  │  - Interactive (Plotly)                │
│   ├ Capacity & Cost  │                                       │
│   └ Trends           │  If no query yet:                     │
│                       │  "Ask a question to generate a chart" │
│  ┌─────────────────┐ │                                       │
│  │ Chat history    │ │                                       │
│  │ scrollable      │ │                                       │
│  │ 420px height    │ │                                       │
│  └─────────────────┘ │                                       │
│  [Ask about GPUs...] │                                       │
└───────────────────────┴───────────────────────────────────────┘
```

### My GPUs (end-user page)

5 sections: Team Selector → Metrics Cards → GPU Allocation + Cloud Donut → Scheduling Heatmap with Best/Avoid → Allocation Table → Team Comparison Bar

### Executive Dashboard (leadership page)

4 sections: Cross Clusters Overview → Capacity & Efficiency → Usage Patterns → Weekly Heatmaps

---

## Example Prompts (organized by persona)

### End User (engineer submitting jobs)

```
"When should I schedule my batch job?"
"Best time to run a training job on A10G?"
"Why is my job pending?"
"Is the queue busy right now?"
"Are there preemption risks for my spot workload?"
"Which GPUs are most oversubscribed?"
"Is the weekend a good time for long jobs?"
"What's the current GPU temperature?"
```

### Team Lead

```
"How efficient is team-alpha?"
"Show me team-beta's GPU allocation"
"Which team is wasting the most GPUs?"
"Compare team-alpha vs team-beta efficiency"
"Are GPUs idle at night?"
```

### Director / FinOps

```
"How many GPUs do we have total?"
"What's the overall utilization trend?"
"Where is the biggest GPU bottleneck?"
"Should we add more A10G capacity?"
"What's the waste gap this month?"
```

---

## Verification Plan

1. **Apply RBAC:** `oc apply -f k8s/serviceaccount.yaml`
2. **Build + deploy:** `oc start-build gpu-dashboard --from-dir=. --follow`
3. **Test live data:**
   - "How many GPUs do we have?" → should return 8x NVIDIA A10G, 2 nodes
   - "What's the GPU utilization right now?" → should return live DCGM values
   - "Is the queue busy?" → should return Kueue workload count
   - "Which GPUs are hottest?" → should return temperature per GPU
4. **Test Kueue integration:**
   - Submit a test workload to team-alpha
   - Ask chatbot: "What workloads are running?"
   - Submit a conflicting workload to team-beta
   - Ask: "Why is my job pending?"
5. **Test fallback:** Set `DATA_SOURCE=mock` → should use simulated data
6. **Test LlamaStack:** Verify chatbot uses LlamaStack when available, falls back to direct mode

---

## What Changed from v1.0.0

| v1.0.0 (current) | v2.0.0 (this spec) |
|---|---|
| Simulated data (numpy random) | Live Thanos + K8s API queries |
| 5 fake teams | Real namespaces (team-alpha, team-beta) |
| 7 fake GPU types | Real: 8x NVIDIA A10G |
| 3 fake clouds | Real: AWS only (single cluster) |
| 7 tools (data query only) | 10 tools (+queue_status, +workload_status, +gpu_health) |
| No RBAC | ServiceAccount + ClusterRole |
| Chat in sidebar | Chat-first layout (left=chat, right=chart) |
| No Kueue awareness | Full Kueue CRD queries |
