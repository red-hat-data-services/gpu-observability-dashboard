# Quick Setup Guide

## Prerequisites
- Python 3.8+
- pip3

## Installation (2 minutes)

```bash
# 1. Navigate to the project
cd gpu-observability-dashboard

# 2. Create virtual environment
python3 -m venv venv

# 3. Activate virtual environment
source venv/bin/activate

# 4. Install dependencies
pip3 install -r requirements.txt
```

## Run the Dashboard

```bash
streamlit run app.py
```

**Dashboard URL:** http://localhost:8501

## Troubleshooting

**Issue:** `command not found: streamlit`  
**Solution:** Make sure virtual environment is activated: `source venv/bin/activate`

**Issue:** Port 8501 already in use  
**Solution:** `streamlit run app.py --server.port 8502`

**Issue:** Slow performance  
**Solution:** Install watchdog: `pip3 install watchdog`

## Production Deployment

For production use with real Prometheus data:

1. Update data generation functions in `app.py`
2. Replace `generate_all_gpu_data()` with Prometheus queries
3. Configure Prometheus endpoint in environment variables
4. Add authentication if needed

See comments in code marked with: `# In production: Query Prometheus...`
