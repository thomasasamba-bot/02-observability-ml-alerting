# Troubleshooting Guide

Common issues, diagnostics, and solutions for the MLOps Observability Platform.

## Inference Server Issues

### "Connection refused" when calling /predict

**Symptoms:**
```
curl: (7) Failed to connect to localhost port 8006: Connection refused
```

**Diagnostics:**
```bash
# Check if server is running
lsof -i :8006

# Check logs
docker logs <inference-server-container>
# or
kubectl logs deployment/inference-server -n mlops
```

**Solutions:**
1. **Server not started**
   ```bash
   uvicorn app.serving.app:app --host 0.0.0.0 --port 8006
   ```

2. **Port already in use**
   ```bash
   # Find and kill process using port 8006
   kill -9 $(lsof -ti:8006)
   
   # Or use different port
   uvicorn app.serving.app:app --host 0.0.0.0 --port 8007
   ```

3. **Model loading failed**
   - Check: "Model not loaded" in `/health/ready` response
   - Verify MLflow is running: `curl http://localhost:5000/health`
   - Check model registry: `mlflow models list`

---

### Prediction returns 503 "Model not loaded"

**Symptoms:**
```json
{
  "detail": "Model not loaded. Check MLflow connectivity."
}
```

**Diagnostics:**
```bash
# Check MLflow connectivity
curl -s http://localhost:5000/health

# Check model file exists
ls -la mlartifacts/1/*/artifacts/model

# Check logs
docker logs <inference-server> | grep -i "model\|mlflow"
```

**Solutions:**

1. **MLflow not running**
   ```bash
   mlflow server --host 0.0.0.0 --port 5000
   ```

2. **Model not trained yet**
   ```bash
   python -m app.pipeline.train
   ```

3. **Model version mismatch**
   ```bash
   # Check available models
   curl -s http://localhost:5000/api/2.0/model-registry/models | python3 -m json.tool
   
   # Verify model in code
   # app/serving/app.py: check MODEL_VERSION = X
   ```

4. **MLflow artifact path incorrect**
   ```bash
   # Set correct path
   export MLFLOW_ARTIFACT_PATH="/path/to/mlartifacts"
   ```

---

### Slow predictions (latency > 100ms)

**Symptoms:**
```json
{
  "latency_ms": 250.5
}
```

**Diagnostics:**
```bash
# Profile inference
python -m cProfile -s cumulative app/serving/app.py

# Check model complexity
curl -s http://localhost:6006/metrics | grep latency_bucket
```

**Solutions:**

1. **Model too complex**
   - Reduce number of features
   - Use simpler model (LogisticRegression vs RandomForest)
   - Enable model quantization

2. **System under load**
   - Increase workers (but keep at 1 for inference server)
   - Add more replicas: `kubectl scale deployment/inference-server --replicas=3 -n mlops`

3. **MLflow query slow**
   - Increase MLflow server resources
   - Cache model locally (already done in inference-server)

---

## Drift Detection Issues

### Drift detector never fires

**Symptoms:**
```
ml_drift_detected = 0 (always)
ml_feature_drift_psi < 0.10 (all features)
```

**Diagnostics:**
```bash
# Test manually
python -m app.pipeline.drift_detector --current-csv data/raw/credit_drifted.csv

# Check schema
cat data/processed/feature_schema.json | python3 -m json.tool | head -20

# Check threshold config
grep -r "PSI_ALERT_THRESHOLD" app/anomaly_detection/
```

**Solutions:**

1. **PSI threshold too high**
   ```python
   # app/anomaly_detection/config.py
   PSI_ALERT_THRESHOLD = 0.15  # Lower from 0.25
   ```

2. **Schema not built** (empty bins)
   ```bash
   # Retrain to regenerate schema
   python -m app.pipeline.train --force
   ```

3. **Detector not running**
   - Check: `ps aux | grep drift_detector`
   - Check logs: `docker logs metrics-exporter`

4. **Data too similar**
   - Run chaos test: `python tests/chaos/inject_drift.py`
   - Verify drifted CSV has different distributions

---

### False positives (drift fires on baseline data)

**Symptoms:**
```
ml_drift_detected = 1 (on baseline CSV)
ml_feature_drift_psi = [0.0080, 0.0092, ...]  # All < 0.25
```

**Diagnostics:**
```bash
# Check PSI calculation
python -c "
from app.pipeline.drift_detector import check_drift
report = check_drift('data/raw/credit_baseline.csv')
for feature in report['features']:
    print(f\"{feature['feature']}: PSI={feature['psi']}\")
"
```

**Solutions:**

1. **Statistical noise**
   - Increase window size (more data points)
   - Use KS-test p-value instead of PSI
   ```python
   # Check if KS-test is significant
   if ks_pvalue < 0.05 and psi > 0.25:
       drift_detected = True
   ```

2. **Bins too small**
   ```python
   # app/anomaly_detection/config.py
   PSI_BINS = 5  # Fewer bins, less noise
   ```

3. **Training data too small**
   ```bash
   # Regenerate with more samples
   export TRAINING_DATA_SIZE=10000
   python scripts/data/generate_data.py
   python -m app.pipeline.train
   ```

---

## MLflow Issues

### "MLflowException: Credentials are not configured"

**Symptoms:**
```
MLflowException: Credentials are not configured for the Databricks workspace.
```

**Diagnostics:**
```bash
# Check MLflow tracking URI
echo $MLFLOW_TRACKING_URI

# Try connecting
curl -s http://localhost:5000/health
```

**Solutions:**

1. **Local MLflow setup**
   ```bash
   # Use SQLite backend (no remote needed)
   export MLFLOW_TRACKING_URI="sqlite:///mlflow.db"
   mlflow server --backend-store-uri sqlite:///mlflow.db --default-artifact-root ./mlartifacts
   ```

2. **Remote MLflow not running**
   ```bash
   # Verify endpoint
   curl -v http://your-mlflow-server:5000/health
   
   # Check connectivity
   telnet your-mlflow-server 5000
   ```

---

### Models not registered

**Symptoms:**
```
mlflow.exceptions.MlflowException: Model not found: credit-scoring
```

**Diagnostics:**
```bash
# List all models
curl -s http://localhost:5000/api/2.0/model-registry/models | python3 -m json.tool

# Check experiment runs
mlflow experiments view --experiment-name credit-scoring
```

**Solutions:**

1. **Model not trained yet**
   ```bash
   python -m app.pipeline.train
   ```

2. **Auto-registration disabled**
   ```python
   # app/pipeline/train.py
   AUTO_REGISTER = True  # Enable auto-registration
   ```

3. **Model quality below threshold**
   ```bash
   # Check ROC-AUC
   mlflow experiments search --experiment-names credit-scoring
   
   # Lower threshold temporarily for testing
   export MODEL_MIN_ROC_AUC=0.70
   ```

---

## Kubernetes Deployment Issues

### Pod crashes with "CrashLoopBackOff"

**Diagnostics:**
```bash
# Check pod status
kubectl get pods -n mlops

# View logs
kubectl logs deployment/inference-server -n mlops --tail=50

# Describe pod
kubectl describe pod <pod-name> -n mlops
```

**Common causes:**

1. **Model not found**
   ```
   ERROR: Model not found in /app/mlartifacts
   ```
   **Fix:** Train model before deploying
   ```bash
   python -m app.pipeline.train
   ```

2. **Environment variable missing**
   ```
   ERROR: MLFLOW_TRACKING_URI not set
   ```
   **Fix:** Add to deployment spec:
   ```yaml
   env:
     - name: MLFLOW_TRACKING_URI
       value: "http://mlflow:5000"
   ```

3. **Image not found**
   ```
   Failed to pull image "ghcr.io/owner/observability-ml:sha-abc123"
   ```
   **Fix:** Build and push image
   ```bash
   docker build -f app/serving/Dockerfile -t ghcr.io/owner/observability-ml:latest .
   docker push ghcr.io/owner/observability-ml:latest
   ```

---

### Service not accessible from outside cluster

**Diagnostics:**
```bash
# Check ingress
kubectl get ingress -n mlops

# Check service
kubectl get svc -n mlops

# Port-forward for testing
kubectl port-forward svc/inference-server 8006:8006 -n mlops
```

**Solutions:**

1. **Ingress not configured**
   ```bash
   kubectl apply -f infra/kubernetes/ingress/ingress.yaml
   
   # Wait for external IP
   kubectl get ingress inference-ingress -n mlops --watch
   ```

2. **Load balancer pending**
   ```bash
   # On minikube, enable ingress addon
   minikube addons enable ingress
   ```

---

## Test Failures

### "ModuleNotFoundError: No module named 'app'"

**Diagnostics:**
```bash
# Check if conftest.py exists
ls -la tests/conftest.py

# Check Python path
python -c "import sys; print('\\n'.join(sys.path))"
```

**Solution:**
```bash
# Create conftest.py if missing
cat > tests/conftest.py << 'EOF'
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
EOF

# Run tests again
pytest tests/unit/ -v
```

---

### "pytest: command not found"

**Solution:**
```bash
# Install pytest
pip install pytest

# Or ensure you're in virtual environment
source .venv/bin/activate
```

---

## Performance & Monitoring

### High memory usage

**Diagnostics:**
```bash
# Check process memory
ps aux | grep python | grep serving

# Monitor in real-time
docker stats <container-name>
```

**Solutions:**

1. **Reduce prediction buffer**
   ```python
   # app/serving/config.py
   PREDICTION_BUFFER_SIZE = 1000  # Down from 10000
   ```

2. **Restart pod**
   ```bash
   kubectl rollout restart deployment/inference-server -n mlops
   ```

---

### Metrics not appearing in Prometheus

**Diagnostics:**
```bash
# Check if metrics exporter is running
curl -s http://localhost:8007/metrics | head -20

# Check Prometheus scrape status
curl -s http://localhost:9090/api/v1/targets | python3 -m json.tool
```

**Solutions:**

1. **Exporter not running**
   ```bash
   uvicorn app.exporter.metrics_exporter:app --host 0.0.0.0 --port 8007
   ```

2. **Prometheus not scraping**
   ```yaml
   # monitoring/prometheus/prometheus.yml
   scrape_configs:
     - job_name: 'metrics-exporter'
       static_configs:
         - targets: ['localhost:8007']
   ```

---

## Getting Help

**Check logs first:**
```bash
# Inference server
kubectl logs -f deployment/inference-server -n mlops

# Metrics exporter
kubectl logs -f deployment/metrics-exporter -n mlops

# Drift detector (background job)
grep -r "ERROR\|Exception" mlruns/ | tail -20
```

**Common log patterns:**
- `ERROR.*Model not found` — Model not trained
- `ERROR.*Connection refused` — Service unreachable
- `WARNING.*Drift detected` — Normal operation
- `ERROR.*Validation failed` — Bad input data

**Debug mode:**
```bash
export LOG_LEVEL=DEBUG
python -m app.pipeline.train
```

See [Configuration Reference](configuration.md) for environment setup.
