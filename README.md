# 🌐 GPU Observability Dashboard

**Executive-level dashboard for multi-cloud GPU infrastructure visibility and efficiency analysis.**

Target Audience: **Directors · FinOps · Platform Leadership**

---

## 📋 Table of Contents

1. [Overview](#overview)
2. [Quick Start](#quick-start)
3. [Dashboard Sections](#dashboard-sections)
4. [Graph Details & Examples](#graph-details--examples)
5. [Key Insights](#key-insights)
6. [Installation](#installation)
7. [Production Deployment](#production-deployment)

---

## Overview

This dashboard provides **cross-cloud GPU observability** for organizations managing GPU infrastructure across:
- ✅ Multiple cloud providers (AWS, GCP, IBM Cloud)
- ✅ Multiple GPU types (L4, T4, A100-40GB, A100-80GB, H100, H200, B200)
- ✅ Multiple workload types (committed, on-demand, spot)
- ✅ Multiple teams

**Key Questions Answered:**
1. Who uses which GPUs?
2. How much GPU capacity does each team consume?
3. What is the real utilization vs allocation?
4. Where is waste and inefficiency?
5. When are peak usage hours?
6. Which teams work on weekends?

---

## Quick Start

```bash
# Install dependencies
pip3 install -r requirements.txt

# Run dashboard
streamlit run app.py
```

Dashboard opens at: **http://localhost:8501**

---

## Dashboard Sections

### 🌐 Section 1: Cross Clusters Overview (Committed GPUs Only)
High-level organizational capacity and efficiency view.

### 👥 Section 2: Who Uses What - Detailed Breakdown
Multi-dimensional analysis of GPU consumption by team, type, workload, and cloud.

### ⚡ Section 3: Capacity Consumption & Efficiency
Team efficiency trends with drill-down by GPU type and workload.

### 🕐 Section 4: Usage Patterns & Time Analysis
Behavioral patterns showing when and how teams use GPUs.

---

## Graph Details & Examples

### 📊 Section 1: Cross Clusters Overview

#### **Graph 1: Committed GPU Inventory by Type and Cloud**

**Type:** Grouped vertical bar chart

**What it shows:**
- Total committed GPU count per GPU type
- Breakdown by cloud provider (AWS, GCP, IBM Cloud)
- Total count annotated above each GPU type group

**Example Use Case:**
> *"I want to see how many H100 GPUs we have committed across all clouds."*
> 
> **Answer:** Look at the H100 bars. If AWS has 64, GCP has 70, IBM has 44, total is 178 H100s.

**Key Insight:** Identifies GPU type distribution and potential cloud concentration risks.

---

#### **Graph 2: 30-Day Organizational Efficiency Trend (Committed)**

**Type:** Dual line chart

**What it shows:**
- **Blue solid line:** Used % (allocation rate)
- **Light blue dashed line:** Utilization % (actual GPU load)
- 30-day daily trend for committed GPUs only

**Example Use Case:**
> *"Are we allocating more GPUs than we're actually using?"*
> 
> **Answer:** If Used % is 70% but Utilization % is 45%, there's a 25% efficiency gap.

**Key Insight:** The **gap between Used and Utilization = waste**. Larger gap = more inefficiency.

---

#### **Graph 3: Team Efficiency Scatter**

**Type:** Bubble scatter plot

**What it shows:**
- **X-axis:** Allocated % (Used)
- **Y-axis:** Avg Utilization %
- **Bubble size:** Total GPUs per team
- **Bubble color:** Idle % (green = low, red = high)

**Example Use Case:**
> *"Which teams are hoarding GPUs without using them efficiently?"*
> 
> **Answer:** Large bubbles in the top-left corner = high allocation, low utilization = hoarding.

**Key Insight:** Identifies inefficient teams visually. Teams with large bubbles and low utilization need optimization.

---

### 👥 Section 2: Who Uses What

#### **Component 1: Complete Usage Breakdown Table**

**Type:** Filterable data table

**Columns:**
- Team
- GPU Type
- Workload Type (committed/on-demand/spot)
- Cloud
- GPU Hours (30-day total)
- Avg Utilization %
- Total GPUs

**Filters Available:**
- Filter by Team
- Filter by GPU Type
- Filter by Workload
- Filter by Cloud

**Example Use Case:**
> *"How many GPU hours did the AI Research team use on H100s in AWS with committed workload?"*
> 
> **Answer:** Filter: Team=AI Research, GPU Type=H100, Workload=committed, Cloud=AWS. Read GPU Hours column.

**Key Insight:** Answers "who uses what, how much, where" with exact numbers.

---

#### **Component 2: Daily GPU Usage by Team (Cloud Tabs)**

**Type:** Stacked area charts in tabs

**Structure:**
- **Tabs:** AWS | GCP | IBM Cloud
- **Within each tab:** Grid of GPU types (3 per row)
- **Each small chart:** 30-day stacked area showing team contribution

**What it shows:**
- Which teams drive GPU usage in each cloud
- Daily patterns per GPU type
- Weekend dips (teams that stop using GPUs)

**Example Use Case:**
> *"In AWS, which team dominates H100 usage?"*
> 
> **Answer:** Go to AWS tab → Find H100 chart → Largest area = dominant team.

**Key Insight:** Identifies dominant teams per GPU type per cloud. Helps with capacity planning and team accountability.

---

#### **Component 3: GPU Usage Breakdown (Side by Side)**

**Left: Sunburst Hierarchy**

**Type:** Interactive circular hierarchy

**Structure:**
- Center = Teams
- Middle ring = GPU Types
- Outer ring = Workload Types
- Size = GPU Hours
- Color = Utilization %

**How to use:**
- Click segments to drill down
- Hover to see exact values
- Visual size comparison

**Example Use Case:**
> *"Which team consumes the most GPU hours overall?"*
> 
> **Answer:** Largest center segment = biggest consumer.

**Key Insight:** Quick visual overview of organizational GPU consumption hierarchy.

---

**Right: Daily GPU Hours Trend (with Tabs)**

**Type:** Multi-line chart with nested tabs

**Structure:**
- **Level 1 Tabs:** All GPU Types | L4 | T4 | A100-40GB | etc.
- **Level 2 Tabs:** All | committed | on-demand | spot
- **Lines:** One per team

**What it shows:**
- Daily GPU hours consumption per team over 30 days
- Growth or decline trends
- Weekend usage patterns

**Example Use Case:**
> *"Did the Data Science team increase H100 committed usage over the last month?"*
> 
> **Answer:** 
> 1. Select H100 tab
> 2. Select committed tab
> 3. Find Data Science line
> 4. Check if it trends upward

**Key Insight:** Identifies growth patterns, helps forecast capacity needs.

---

### ⚡ Section 3: Capacity Consumption & Efficiency

#### **Top Row: Team Efficiency Trends (All GPU Types)**

**Left: Used % by Team (Committed Only)**

**Type:** Multi-line chart

**What it shows:**
- Daily Used % (allocation rate) per team
- **White dashed line:** Organizational average
- Committed workloads only

**Example Use Case:**
> *"Is the ML Platform team allocating more GPUs than the average?"*
> 
> **Answer:** If ML Platform line is above the white dashed average line → yes.

**Key Insight:** Teams above average may be over-allocating. Teams below average have room to grow.

---

**Right: Utilization % by Team (All Workload Types)**

**Type:** Multi-line chart

**What it shows:**
- Daily Utilization % per team
- All workload types combined
- **White dashed line:** Average

**Example Use Case:**
> *"Which team has the lowest actual GPU utilization?"*
> 
> **Answer:** Lowest line = most wasteful team.

**Key Insight:** Low utilization = inefficiency. Use for optimization conversations with teams.

---

#### **Tabs: Per GPU Type Analysis**

**Structure:**
- **Tabs:** All GPU Types | L4 | T4 | A100-40GB | A100-80GB | H100 | H200 | B200

**Within each tab:** 2 charts side by side
- **Left:** Used % by Team
- **Right:** Utilization % by Team

**Example Use Case:**
> *"Which team is wasteful specifically with H100 GPUs?"*
> 
> **Answer:**
> 1. Select H100 tab
> 2. Look at Utilization % chart (right)
> 3. Lowest line = most wasteful with H100s

**Key Insight:** GPU-specific efficiency analysis. Some teams may be efficient with T4s but wasteful with H100s.

---

### 🕐 Section 4: Usage Patterns & Time Analysis

#### **Filters (Apply to All Section 4 Graphs)**

**Available Filters:**
- Focus Teams (refines from global filters)
- Focus GPU Types (refines from global filters)
- Metric (GPU Hours or Utilization %)
- Reset button (returns to global filter state)

**How It Works:**
1. Global filters (top of dashboard) set the baseline
2. Section 4 filters further refine the selection
3. All 3 heatmaps update dynamically

---

#### **Left: Hourly Usage Pattern**

**Type:** 2D Heatmap (Hour × Day of Week)

**What it shows:**
- **X-axis:** Hour of Day (0-23)
- **Y-axis:** Day of Week (Monday-Sunday)
- **Color:** Selected metric (GPU Hours or Utilization %)
- **Resolution:** 168 data points (24 hours × 7 days)

**Example Use Case:**
> *"When is our peak GPU usage hour?"*
> 
> **Answer:** Find the brightest green cell. E.g., Thursday 2:00 PM = peak.

**Key Insight:** 
- **Capacity planning:** Know when to add capacity
- **Cost optimization:** Identify unused night/weekend hours
- **Scheduling:** Avoid launching workloads during peak hours

---

#### **Right Top: Metrics × Weekday**

**Type:** Small heatmap (Metrics × Days)

**What it shows:**
- **Rows:** Used %, Utilization %, Idle %
- **Columns:** Monday-Sunday
- **Filtered** by selected teams and GPU types

**Example Use Case:**
> *"What's our typical Friday utilization?"*
> 
> **Answer:** Look at Utilization % row, Friday column. E.g., 48%.

**Key Insight:** Weekday patterns help identify weekend waste and plan maintenance windows.

---

#### **Right Bottom: Team × Weekday**

**Type:** Heatmap (Teams × Days)

**What it shows:**
- **Rows:** Teams (filtered)
- **Columns:** Monday-Sunday
- **Color:** Utilization % (yellow/orange/red scale)

**Example Use Case:**
> *"Which teams work on weekends?"*
> 
> **Answer:** Rows with warm colors (orange/red) on Saturday/Sunday = weekend workers.

**Key Insight:** 
- Identifies teams with 24/7 workloads
- Helps plan resource scaling for weekends
- Detects idle resources during off-hours

---

## Key Insights

### **1. Allocated ≠ Utilized**
**Used %** shows reserved GPUs. **Utilization %** shows actual compute load.

**Gap = Waste**

**Example:**
- Used: 80%
- Utilization: 45%
- **Waste: 35%** of allocated GPUs are idle

---

### **2. Workload Type Behavior**

**Committed:** Expected 60-85% Used (reserved capacity, not always fully allocated)

**On-Demand / Spot:** Expected ~100% Used (dynamic, paid per use)

If committed shows 100% Used → may need to shift to on-demand.

---

### **3. Team Efficiency Variance**

Some teams may be:
- **Efficient with T4s** (75% utilization)
- **Wasteful with H100s** (30% utilization)

Use **Section 3 GPU Type tabs** to identify these patterns.

---

### **4. Peak Hours Detection**

**Section 4 Hourly Heatmap** reveals:
- Peak hours: Bright green cells
- Idle hours: Dark blue cells
- Weekend patterns: Light colors = lower usage

**Actionable:**
- Schedule batch jobs during dark blue hours
- Add capacity during bright green hours
- Reclaim resources during weekend dark periods

---

### **5. Cloud Distribution**

**Section 2 Table + Daily Usage** shows:
- Which teams use which clouds
- Imbalanced distribution (all teams on AWS = risk)
- Opportunities to migrate workloads between clouds

---

## Installation

### Prerequisites
- Python 3.8+
- pip3

### Steps

```bash
# Clone repository
git clone https://github.com/red-hat-data-services/gpu-observability-dashboard.git
cd gpu-observability-dashboard

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip3 install -r requirements.txt

# Run dashboard
streamlit run app.py
```

Dashboard opens at: **http://localhost:8501**

---

## Production Deployment

### Connecting to Prometheus/Thanos

**Current State:** Simulated data for demo

**Production:** Replace data generation functions with Prometheus queries

**Required Metrics:**
```promql
# Total GPUs per node
node_gpu_total{cloud, cluster, gpu_type, team, workload_type}

# Allocated GPUs per node
node_gpu_allocated{cloud, cluster, gpu_type, team, workload_type}

# GPU Utilization % per node
node_gpu_utilization{cloud, cluster, gpu_type, team, workload_type}
```

**Labels Required:**
- `cloud` - AWS, GCP, IBM Cloud
- `cluster` - Cluster identifier
- `gpu_type` - L4, T4, A100-40GB, etc.
- `team` - Team tag/label
- `workload_type` - committed, on-demand, spot

**Update Functions:**
- `generate_all_gpu_data()` → Query Prometheus API
- `generate_30day_timeseries()` → Prometheus range query
- `generate_hourly_usage_patterns()` → Prometheus hourly data

See code comments marked with: `# In production: Query Prometheus...`

---

## Configuration

### Cloud Provider Colors (Consistent Throughout)
- **AWS:** Orange (#FF9900)
- **GCP:** Green (#34A853)
- **IBM Cloud:** Blue (#0F62FE)

### Workload Type Colors
- **Committed:** Blue (#1f77b4)
- **On-Demand:** Orange (#ff7f0e)
- **Spot:** Green (#2ca02c)

### GPU Types Supported
```
Low-end:     L4, T4
Mid-range:   A100-40GB, A100-80GB
High-end:    H100, H200, B200
```

---

## Metrics Explained

### **Used %**
```
Used % = (Allocated GPUs / Total GPUs) × 100
```
Percentage of GPUs that are reserved/allocated.

**Expected values:**
- Committed: 60-85%
- On-Demand: ~100%
- Spot: ~100%

---

### **Utilization %**
```
Utilization % = Actual GPU compute load
```
Real GPU usage (independent of allocation).

**Interpretation:**
- **High (>60%):** GPUs are actively computing
- **Medium (30-60%):** Moderate usage
- **Low (<30%):** Wasteful - GPUs allocated but idle

---

### **Idle %**
```
Idle % = 100 - Used %
```
Percentage of total capacity that is unallocated.

**Note:** Not the same as (100 - Utilization). Idle = physical availability.

---

### **GPU Hours**
```
GPU Hours = Total GPUs × (Used % / 100) × 24 hours × Days
```
Cumulative GPU-hours consumed over a period.

**Example:**
- 10 GPUs × 80% Used × 24 hours × 30 days = 5,760 GPU-hours

---

## Filter Behavior

### **Global Filters (Top of Dashboard)**
Apply to **all sections** except where explicitly overridden:
- Cloud Provider
- GPU Type
- Team

### **Section 2 Table Filters**
Independent filters within the Complete Usage Breakdown table.

### **Section 4 Pattern Filters**
- **Inherit** from global filters
- **Refine** selection further
- **Reset button** returns to global filter state

---

## Use Cases

### **Use Case 1: Capacity Planning**
**Question:** Do we need more H100 GPUs?

**How to Answer:**
1. **Section 1, Graph 1:** Check current H100 inventory
2. **Section 1, Graph 2:** Check if Used % > 85% and Utilization % > 60%
3. **Section 4, Hourly Heatmap:** Identify if peak hours show maxed capacity
4. **Decision:** If all 3 indicators are high → Yes, need more capacity

---

### **Use Case 2: Team Accountability**
**Question:** Which team is most wasteful with A100 GPUs?

**How to Answer:**
1. **Section 3:** Click **A100-40GB** tab
2. **Right chart:** Utilization % by Team
3. **Find lowest line** = most wasteful team
4. **Action:** Schedule optimization discussion with that team

---

### **Use Case 3: Weekend Waste Detection**
**Question:** Are GPUs sitting idle on weekends?

**How to Answer:**
1. **Section 4, Right Bottom:** Team × Weekday heatmap
2. **Look at Saturday/Sunday columns**
3. **Dark/cool colors** = low utilization = waste
4. **Action:** Reclaim idle weekend resources

---

### **Use Case 4: Cost Optimization**
**Question:** Where can we save money?

**How to Answer:**
1. **Section 2, Table:** Sort by GPU Hours descending
2. **Section 2, Table:** Filter Utilization % < 30%
3. **Identify:** High GPU hours + Low utilization = waste
4. **Action:** Work with those teams to optimize or reduce allocation

---

### **Use Case 5: Cloud Migration Decision**
**Question:** Should we migrate workloads from AWS to GCP?

**How to Answer:**
1. **Section 2, Daily Usage:** Compare AWS vs GCP tabs
2. **Section 1, Graph 1:** Check current distribution
3. **Section 2, Table:** Filter by Cloud, compare utilization
4. **Decision:** If GCP has lower utilization + spare capacity → yes

---

## Architecture

**Single File Design:**
- `app.py` - Complete Streamlit application (~2,000 lines)
- In-memory data simulation using pandas
- No external database required
- Production-ready for Prometheus integration

**Key Technologies:**
- Streamlit 1.30+
- Plotly (interactive charts)
- Pandas (data manipulation)
- NumPy (simulations)

---

## Troubleshooting

**Issue:** Dashboard shows "No data"  
**Solution:** Check global filters - at least 1 cloud, team, and GPU type must be selected

**Issue:** Charts not updating  
**Solution:** Click browser refresh or Streamlit "Rerun"

**Issue:** Tabs not showing data  
**Solution:** Check if filtered data exists for that GPU type/workload combination

**Issue:** Performance is slow  
**Solution:** Install watchdog: `pip3 install watchdog`

---

## Contributing

This is a demo dashboard. For production use:
1. Fork the repository
2. Update data sources to Prometheus
3. Add authentication
4. Deploy to cloud platform

---

## License

MIT License - Free to use and modify

---

## Support

For questions or issues:
- GitHub Issues: https://github.com/red-hat-data-services/gpu-observability-dashboard/issues
- Internal: Contact your platform team

---

## Version History

**v1.0 (Current)**
- Section 1: Cross Clusters Overview
- Section 2: Who Uses What (table, daily usage, breakdown)
- Section 3: Capacity & Efficiency (team trends with tabs)
- Section 4: Usage Patterns (hourly + weekly heatmaps)
- Global and local filters
- PII-free, production-ready code

---

**Built for leadership visibility · Optimized for decision-making · Ready for action** 🚀
