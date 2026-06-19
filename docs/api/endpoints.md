# API Reference

Complete endpoint documentation for the MLOps Inference Server and Metrics Exporter.

## Inference Server (Port 8006)

Base URL: `http://localhost:8006` (local) or `http://inference-server:8006` (Kubernetes)

### Prediction Endpoints

#### `POST /predict`

**Single credit scoring prediction**

**Request:**
```json
{
  "age": 45,
  "income": 95000,
  "loan_amount": 12000,
  "credit_score": 760,
  "debt_to_income": 0.18,
  "employment_years": 12.0,
  "num_credit_lines": 6,
  "missed_payments": 0
}
```

**Response (200 OK):**
```json
{
  "decision": "no_default",
  "probability": 0.847,
  "confidence_flag": "high",
  "model_version": "2",
  "latency_ms": 12.3,
  "features_used": 8,
  "timestamp": "2026-06-19T20:59:41Z"
}
```

**Field Descriptions:**
- `decision` — `"default"` or `"no_default"` based on probability > 0.40
- `probability` — Raw model probability [0.0, 1.0]
- `confidence_flag` — `"high"` (p > 0.60), `"medium"` (0.40 < p < 0.60), `"low"` (p < 0.40)
- `model_version` — Current model in inference server
- `latency_ms` — End-to-end prediction time

**Error (400):**
```json
{
  "error": "validation_error",
  "missing_fields": ["income"],
  "message": "Missing required feature: income"
}
```

**Curl Example:**
```bash
curl -X POST http://localhost:8006/predict \
  -H "Content-Type: application/json" \
  -d '{
    "age": 45, "income": 95000, "loan_amount": 12000,
    "credit_score": 760, "debt_to_income": 0.18,
    "employment_years": 12.0, "num_credit_lines": 6,
    "missed_payments": 0
  }'
```

---

#### `POST /predict/batch`

**Batch predictions (up to 500 records)**

**Request:**
```json
{
  "records": [
    {
      "age": 45, "income": 95000, "loan_amount": 12000,
      "credit_score": 760, "debt_to_income": 0.18,
      "employment_years": 12.0, "num_credit_lines": 6,
      "missed_payments": 0
    },
    {
      "age": 32, "income": 55000, "loan_amount": 8000,
      "credit_score": 680, "debt_to_income": 0.32,
      "employment_years": 5.0, "num_credit_lines": 4,
      "missed_payments": 2
    }
  ]
}
```

**Response (200 OK):**
```json
{
  "batch_id": "batch-2026-06-19-001",
  "total_records": 2,
  "predictions": [
    {
      "record_id": 0,
      "decision": "no_default",
      "probability": 0.847,
      "confidence_flag": "high"
    },
    {
      "record_id": 1,
      "decision": "default",
      "probability": 0.623,
      "confidence_flag": "medium"
    }
  ],
  "processing_time_ms": 24.5,
  "default_rate": 0.500
}
```

**Constraints:**
- Max 500 records per batch
- All required features must be present
- Extra fields are ignored

**Curl Example:**
```bash
curl -X POST http://localhost:8006/predict/batch \
  -H "Content-Type: application/json" \
  -d @batch_data.json
```

---

### Drift Detection Endpoints

#### `GET /drift/status`

**Current drift detection status**

**Response (200 OK):**
```json
{
  "overall_drift": true,
  "drifted_features": ["income", "debt_to_income", "missed_payments"],
  "num_drifted_features": 3,
  "window_size": 1000,
  "prediction_count": 1000,
  "default_rate": 0.242,
  "mean_confidence": 0.587,
  "timestamp": "2026-06-19T21:00:06Z"
}
```

**Example:**
```bash
curl -s http://localhost:8006/drift/status | python3 -m json.tool
```

---

#### `GET /drift/report`

**Detailed per-feature drift analysis**

**Response (200 OK):**
```json
{
  "overall_drift": true,
  "features": [
    {
      "feature": "income",
      "psi": 0.2635,
      "ks_statistic": 0.2270,
      "ks_pvalue": 0.0000,
      "severity": "alert",
      "baseline_mean": 53528.42,
      "current_mean": 39322.15,
      "baseline_std": 28195.61,
      "current_std": 24891.33
    },
    {
      "feature": "credit_score",
      "psi": 0.2148,
      "ks_statistic": 0.1950,
      "ks_pvalue": 0.0000,
      "severity": "warning",
      "baseline_mean": 678.21,
      "current_mean": 640.91,
      "baseline_std": 78.45,
      "current_std": 85.32
    }
  ],
  "window_size": 1000,
  "check_timestamp": "2026-06-19T21:00:06Z"
}
```

**Severity Levels:**
- `"stable"` — PSI < 0.10, KS-test p > 0.05
- `"warning"` — PSI 0.10–0.25 OR KS-test p < 0.05
- `"alert"` — PSI > 0.25

**Example:**
```bash
curl -s http://localhost:8006/drift/report | python3 -m json.tool | head -30
```

---

### Health Checks

#### `GET /health/live`

**Liveness probe** (is the server responding?)

**Response (200 OK):**
```json
{"status": "alive"}
```

**Use for:** Kubernetes liveness probe, load balancer health checks

---

#### `GET /health/ready`

**Readiness probe** (is the model loaded and ready for predictions?)

**Response (200 OK):**
```json
{
  "status": "ready",
  "model_loaded": true,
  "model_version": "2",
  "mlflow_connected": true
}
```

**Response (503 Unavailable):**
```json
{
  "status": "not_ready",
  "reason": "model_not_loaded"
}
```

**Use for:** Kubernetes readiness probe, deployment gates

---

### Status Endpoints

#### `GET /metrics`

**Prometheus metrics in text exposition format**

**Example:**
```
# TYPE ml_drift_detected gauge
ml_drift_detected 1.0
# TYPE ml_feature_drift_psi gauge
ml_feature_drift_psi{feature="income"} 0.2635
ml_feature_drift_psi{feature="credit_score"} 0.2148
# TYPE ml_prediction_confidence_mean gauge
ml_prediction_confidence_mean 0.587
```

**Use:** Scraped by Prometheus at `/metrics`

---

#### `GET /status`

**Service status and statistics**

**Response (200 OK):**
```json
{
  "service": "inference-server",
  "version": "1.0.0",
  "uptime_seconds": 3600,
  "model_version": "2",
  "total_predictions": 12547,
  "total_batches": 234,
  "avg_latency_ms": 11.2,
  "predictions_per_minute": 3.5,
  "errors_total": 2,
  "error_rate_percent": 0.016
}
```

---

## Metrics Exporter (Port 8007)

Base URL: `http://localhost:8007` (local) or `http://metrics-exporter:8007` (Kubernetes)

### Exporter Endpoints

#### `GET /metrics`

**Bridge MLflow and dataset metrics to Prometheus**

Exports:
- Latest model metrics from MLflow (ROC-AUC, F1, training time)
- Dataset statistics (feature means, distribution info)
- Training schema baseline values

**Example scrape:**
```bash
curl -s http://localhost:8007/metrics | grep mlflow
# TYPE mlflow_run_metric gauge
mlflow_run_metric{experiment="credit-scoring",metric="test_roc_auc"} 0.829
mlflow_run_metric{experiment="credit-scoring",metric="test_f1"} 0.682
mlflow_run_metric{experiment="credit-scoring",metric="training_duration_seconds"} 12.5
```

---

#### `GET /health`

**Exporter health check**

**Response (200 OK):**
```json
{
  "status": "healthy",
  "mlflow_connected": true,
  "last_scrape_time": "2026-06-19T21:00:05Z",
  "uptime_seconds": 1800
}
```

---

## Error Codes

| Code | Message | Cause |
|------|---------|-------|
| 200 | OK | Successful prediction or query |
| 400 | Bad Request | Missing/invalid fields |
| 422 | Unprocessable Entity | Type validation failed |
| 503 | Service Unavailable | Model not loaded, MLflow unreachable |
| 504 | Gateway Timeout | Prediction taking too long |

---

## Rate Limiting

**Inference Server:**
- No hard rate limit (depends on deployment)
- Recommended: 1000 requests/sec per deployment
- Batch max: 500 records

**Metrics Exporter:**
- No rate limiting
- Scrape interval: 30 seconds (Prometheus default)

---

## Authentication

Currently **no authentication** (mutual TLS can be added via Kubernetes NetworkPolicy).

For production with auth:
```python
# In app/serving/app.py
from fastapi.security import HTTPBearer

security = HTTPBearer()

@app.post("/predict")
async def predict(data: PredictionRequest, credentials: HTTPAuthCredentials = Depends(security)):
    # Verify token
    ...
```

---

## Timeouts

- Single prediction: 100ms
- Batch prediction: 500ms
- Drift check query: 30 seconds
- MLflow connection: 10 seconds

Adjust in `app/serving/config.py` if needed.

---

See [Troubleshooting](../guides/troubleshooting.md) for common API issues.
