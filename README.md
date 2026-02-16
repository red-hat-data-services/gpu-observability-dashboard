# 🌐 GPU Observability Dashboard

Executive-level dashboard for multi-cloud GPU infrastructure visibility and efficiency analysis.

## Overview

This is a **leadership-ready** observability dashboard that provides:
- Cross-cloud GPU capacity aggregation
- Team-based efficiency analysis
- Workload type breakdown (committed, on-demand, spot)
- 30-day trend analysis
- Waste identification and optimization insights

**Target Audience:** Directors, FinOps, Platform Leadership

## Features

### 📊 Section 1: Cross Clusters Overview
- **Committed GPU Inventory** by Type and Cloud
- **30-Day Efficiency Trend** (Used vs Utilization)
- **Team Efficiency Scatter** (allocation vs actual usage)

### ⚡ Section 3: Capacity Consumption & Efficiency
- **Team efficiency trends** across all GPU types
- **Per-GPU-type analysis** with tabs (L4, T4, A100-40GB, A100-80GB, H100, H200, B200)
- **Used vs Utilization** breakdown by team
- **Average baseline** on every chart

### 📅 Section 2: Organizational Time Patterns
- **Metrics × Weekday Heatmap** (Used, Utilization, Idle patterns)
- **Team × Weekday Heatmap** (which teams work weekends)

### 🕐 Section 4: Usage Patterns (Dynamic Heatmap)
- **Hour × Day of Week** behavioral analysis
- **Dynamic filters:** Team, GPU Type, Metric (GPU Hours / Utilization %)
- **Single adaptive heatmap** that aggregates based on selection
- **Pattern detection:** Peak hours, weekend usage, team behavior

## Key Insights

✅ **Allocation ≠ Utilization** - Shows gap between reserved and actual GPU usage  
✅ **Workload Type Behavior** - Committed (60-85% used) vs On-Demand/Spot (~100% used)  
✅ **Team Efficiency** - Identifies wasteful allocation by team and GPU type  
✅ **Weekend Patterns** - Detects idle resources during off-hours  
✅ **Cross-Cloud Visibility** - Aggregates AWS, GCP, IBM Cloud

## Installation

```bash
# Clone the repository
git clone <YOUR_REPO_URL>
cd gpu-observability-dashboard

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip3 install -r requirements.txt
```

## Usage

```bash
# Run the dashboard
streamlit run app.py
```

The dashboard will open at: **http://localhost:8501**

## Data Source

**Current:** Simulated data for demo purposes

**Production:** Connect to Prometheus/Thanos for real metrics:
- `node_gpu_total`
- `node_gpu_allocated`
- `node_gpu_utilization`
- Labels: `cloud`, `cluster`, `gpu_type`, `workload_type`, `team`

## Configuration

### Cloud Providers
- AWS (Orange: #FF9900)
- GCP (Green: #34A853)
- IBM Cloud (Blue: #0F62FE)

### GPU Types Supported
- L4, T4
- A100-40GB, A100-80GB
- H100, H200, B200

### Workload Types
- **Committed** - Reserved capacity (expected 60-85% used)
- **On-Demand** - Dynamic allocation (expected ~100% used)
- **Spot** - Preemptible instances (expected ~100% used)

## Filters

The dashboard supports filtering by:
- Cloud Provider
- GPU Type
- Team

All charts update dynamically based on filter selections.

## Architecture

**Single File Design:**
- `app.py` - Complete Streamlit application
- No external dependencies beyond standard Python packages
- All data simulation in-memory using pandas

## Metrics Explained

- **Used %** = (Allocated GPUs / Total GPUs) × 100
- **Utilization %** = Actual GPU compute load
- **Idle %** = 100 - Used %
- **Average Line** = Mean across all teams (white dashed line)

## License

MIT License - Free to use and modify

## Contact

For questions or support, contact YOUR_TEAM.
