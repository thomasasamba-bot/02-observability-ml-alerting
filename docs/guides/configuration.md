# Configuration Reference

Environment variables and configuration options for the MLOps Observability Platform.

## Quick Start

```bash
# Copy default config
cp .env.example .env

# Set your values
export MLFLOW_TRACKING_URI="http://localhost:5000"
export DRIFT_CHECK_INTERVAL=60
export PSI_ALERT_THRESHOLD=0.25

# Source environment
source .env
```

---

## Service Configuration

### Inference Server (port 8006)

File: `app/serving/config.py`

| Variable | Default | Description |
|----------|---------|-------------|
| `INFERENCE_PORT` | `8006` | Server port |
| `INFERENCE_WORKERS` | `1` | FastAPI workers (keep at 1 for in-process buffer) |
| `MODEL_CACHE_DIR` | `/tmp/mlflow-cache` | Local model cache location |
| `PREDICTION_BUFFER_SIZE` | `10000` | Rolling buffer for confidence tracking |
| `DECISION_THRESHOLD` | `0.40` | Classification threshold (recall-focused) |
| `MLFLOW_TRACKING_URI` | `http://localhost:5000` | MLflow server endpoint |
| `MLFLOW_ARTIFACT_PATH` | `mlartifacts/` | Where to store downloaded models |

**Set via:**
```bash
export DECISION_THRESHOLD="0.40"
export PREDICTION_BUFFER_SIZE="10000"
```

---

### Metrics Exporter (port 8007)

File: `app/exporter/config.py`

| Variable | Default | Description |
|----------|---------|-------------|
| `EXPORTER_PORT` | `8007` | Exporter port |
| `EXPORTER_POLL_INTERVAL` | `60` | How often to fetch MLflow metrics (seconds) |
| `MLFLOW_TRACKING_URI` | `http://localhost:5000` | MLflow server endpoint |
| `INFERENCE_BASE_URL` | `http://localhost:8006` | Inference server for status checks |
| `SCHEMA_PATH` | `data/processed/feature_schema.json` | Path to training schema |

**Set via:**
```bash
export EXPORTER_POLL_INTERVAL="30"
export MLFLOW_TRACKING_URI="http://mlflow:5000"
```

---

### Drift Detector

File: `app/anomaly_detection/config.py`

| Variable | Default | Description |
|----------|---------|-------------|
| `DRIFT_CHECK_INTERVAL` | `60` | Background check frequency (seconds) |
| `PSI_ALERT_THRESHOLD` | `0.25` | PSI threshold for alert (> = drift) |
| `PSI_WARNING_THRESHOLD` | `0.10` | PSI threshold for warning |
| `KS_TEST_ALPHA` | `0.05` | Significance level for KS-test |
| `PSI_BINS` | `10` | Number of bins for PSI calculation |
| `ANOMALY_DETECTION_METHODS` | `["zscore", "ewma", "isolation_forest"]` | Which methods to enable |

**Set via:**
```bash
export DRIFT_CHECK_INTERVAL="120"
export PSI_ALERT_THRESHOLD="0.30"
```

---

### Alertmanager Integration

File: `app/anomaly_detection/alerting.py`

| Variable | Default | Description |
|----------|---------|-------------|
| `ALERTMANAGER_URL` | `http://localhost:9093` | Alertmanager endpoint |
| `ALERTMANAGER_TIMEOUT` | `10` | Request timeout (seconds) |

**Set via:**
```bash
export ALERTMANAGER_URL="http://alertmanager:9093"
```

---

## MLflow Configuration

### Training

File: `app/pipeline/train.py`

| Variable | Default | Description |
|----------|---------|-------------|
| `MLFLOW_EXPERIMENT_NAME` | `credit-scoring` | Experiment to log to |
| `MLFLOW_RUN_NAME` | Auto-generated | Custom run name |
| `MLFLOW_TRACKING_URI` | `http://localhost:5000` | MLflow server |
| `MODEL_REGISTRY_URI` | Same as tracking | Model registry location |
| `AUTO_REGISTER_MODEL` | `True` | Automatically register trained model |
| `MODEL_MIN_ROC_AUC` | `0.75` | Min ROC-AUC to register |

**Set via:**
```bash
export MLFLOW_EXPERIMENT_NAME="credit-v2"
export MLFLOW_TRACKING_URI="http://mlflow:5000"
```

---

## Data Configuration

File: `scripts/data/generate_data.py` and `app/pipeline/predict.py`

| Variable | Default | Description |
|----------|---------|-------------|
| `DATA_RANDOM_SEED` | `42` | Seed for reproducible data generation |
| `TRAINING_DATA_SIZE` | `5000` | Records in baseline dataset |
| `DRIFTED_DATA_SIZE` | `1000` | Records in drifted dataset |
| `DEFAULT_RATE_BASELINE` | `0.248` | Target default rate in training |
| `DEFAULT_RATE_DRIFTED` | `0.242` | Default rate in drifted scenario |
| `FEATURE_SCHEMA_PATH` | `data/processed/feature_schema.json` | Where to save schema |

**Set via:**
```bash
export DATA_RANDOM_SEED="2024"
export TRAINING_DATA_SIZE="10000"
```

---

## Prometheus Configuration

File: `monitoring/prometheus/prometheus.yml`

```yaml
global:
  scrape_interval: 30s          # How often to scrape metrics
  evaluation_interval: 15s      # How often to evaluate alert rules
  external_labels:
    environment: 'production'

scrape_configs:
  - job_name: 'inference-server'
    static_configs:
      - targets: ['localhost:8006']

  - job_name: 'metrics-exporter'
    static_configs:
      - targets: ['localhost:8007']
```

**Environment variables:**
```bash
export PROMETHEUS_SCRAPE_INTERVAL="60s"
export PROMETHEUS_RETENTION_DAYS="15"
```

---

## Grafana Configuration

File: `monitoring/grafana/provisioning/`

| Variable | Default | Description |
|----------|---------|-------------|
| `GF_SECURITY_ADMIN_PASSWORD` | `admin` | Grafana admin password |
| `GF_PATHS_PROVISIONING` | `/etc/grafana/provisioning` | Provisioning config path |
| `GF_INSTALL_PLUGINS` | — | Plugins to install on startup |

**Set via:**
```bash
export GF_SECURITY_ADMIN_PASSWORD="secure-password"
```

---

## Kubernetes Configuration

### Deployments

File: `infra/kubernetes/deployments/`

| Config | Default | Description |
|--------|---------|-------------|
| `replicas` | `1` | Pod replicas (must be 1 for inference server due to in-process buffer) |
| `memory_request` | `512Mi` | Requested memory |
| `memory_limit` | `1Gi` | Memory limit |
| `cpu_request` | `250m` | Requested CPU |
| `cpu_limit` | `500m` | CPU limit |

**Update in YAML:**
```yaml
resources:
  requests:
    memory: "512Mi"
    cpu: "250m"
  limits:
    memory: "1Gi"
    cpu: "500m"
```

### Environment in Pods

```yaml
env:
  - name: MLFLOW_TRACKING_URI
    value: "http://mlflow:5000"
  - name: DRIFT_CHECK_INTERVAL
    value: "60"
  - name: PSI_ALERT_THRESHOLD
    value: "0.25"
```

---

## Logging Configuration

File: `app/utils/logger.py`

| Variable | Default | Description |
|----------|---------|-------------|
| `LOG_LEVEL` | `INFO` | Logging level (DEBUG, INFO, WARNING, ERROR) |
| `LOG_FORMAT` | `%(asctime)s %(levelname)s %(name)s %(message)s` | Log format string |

**Set via:**
```bash
export LOG_LEVEL="DEBUG"
```

---

## CI/CD Configuration

File: `.github/workflows/`

| Variable | Default | Description |
|----------|---------|-------------|
| `PYTHON_VERSION` | `3.12` | Python version for CI |
| `RUFF_VERSION` | `0.6.9` | Ruff linter version |
| `PYTEST_TIMEOUT` | `300` | Test timeout (seconds) |

**Update in workflow YAML:**
```yaml
- name: Set up Python
  uses: actions/setup-python@v5
  with:
    python-version: "3.12"
```

---

## Development Configuration

### Local Setup

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dev dependencies
pip install -r requirements.txt
pip install pytest pytest-cov ruff black

# Generate data
python scripts/data/generate_data.py

# Run tests
pytest tests/unit/ -v

# Start MLflow (Terminal 1)
mlflow server --host 0.0.0.0 --port 5000

# Start inference server (Terminal 2)
uvicorn app.serving.app:app --host 0.0.0.0 --port 8006 --reload

# Start metrics exporter (Terminal 3)
uvicorn app.exporter.metrics_exporter:app --host 0.0.0.0 --port 8007 --reload
```

### Docker Compose

File: `docker-compose.yml`

```yaml
services:
  mlflow:
    image: ghcr.io/mlflow/mlflow:latest
    ports:
      - "5000:5000"
    volumes:
      - ./mlartifacts:/mlflow/mlartifacts

  prometheus:
    image: prom/prometheus:latest
    ports:
      - "9090:9090"
    volumes:
      - ./monitoring/prometheus/prometheus.yml:/etc/prometheus/prometheus.yml
```

**Start all services:**
```bash
docker-compose up -d
```

---

## Troubleshooting Configuration

### "ModuleNotFoundError: No module named 'app'"

**Solution:** Ensure `tests/conftest.py` exists and Python path is set
```bash
python -c "import sys; print(sys.path)"
```

### "ConnectionError: Cannot reach MLflow at..."

**Solution:** Verify MLflow is running and accessible
```bash
curl -s http://localhost:5000/health
```

### High memory usage

**Solution:** Reduce `PREDICTION_BUFFER_SIZE` or increase pod memory limit
```bash
export PREDICTION_BUFFER_SIZE="1000"
```

---

## Performance Tuning

| Setting | Recommended | High-Throughput | Low-Resource |
|---------|-------------|-----------------|--------------|
| `INFERENCE_WORKERS` | 1 | 2–4 | 1 |
| `DRIFT_CHECK_INTERVAL` | 60s | 30s | 120s |
| `PSI_BINS` | 10 | 10 | 5 |
| `PREDICTION_BUFFER_SIZE` | 10k | 50k | 1k |
| `PROMETHEUS_SCRAPE_INTERVAL` | 30s | 15s | 60s |

---

See [Troubleshooting](troubleshooting.md) for common issues.
