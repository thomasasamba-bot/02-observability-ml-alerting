# Grafana Setup & Dashboards

Guide to setting up Grafana for MLOps observability monitoring.

## Quick Start

### 1. Start Grafana

**Docker:**
```bash
docker run -d -p 3000:3000 \
  -e GF_SECURITY_ADMIN_PASSWORD=admin \
  -e GF_PATHS_PROVISIONING=/etc/grafana/provisioning \
  -v $(pwd)/monitoring/grafana/provisioning:/etc/grafana/provisioning \
  grafana/grafana:latest
```

**Kubernetes:**
```bash
kubectl apply -f infra/kubernetes/monitoring/grafana-deployment.yaml
kubectl port-forward service/grafana 3000:3000
```

Default credentials: `admin` / `admin` (change on first login)

### 2. Add Prometheus Data Source

1. Go to **Configuration → Data Sources**
2. Click **Add data source**
3. Select **Prometheus**
4. Set URL: `http://localhost:9090` (local) or `http://prometheus:9090` (Kubernetes)
5. Click **Save & Test**

---

## Dashboard Setup

### Pre-built Dashboards

The platform includes provisioned dashboards in `monitoring/grafana/dashboards/`:

1. **Model Observability** — Drift, confidence, predictions
2. **ML Pipeline Metrics** — Training, feature importance, model quality
3. **Infrastructure Anomalies** — CPU, memory, disk anomalies
4. **Alert Status** — Active alerts and firing rules

**Auto-provisioned on startup via** `monitoring/grafana/provisioning/dashboards/`.

### Import a Custom Dashboard

1. Go to **Dashboards → Import**
2. Upload JSON file from `monitoring/grafana/dashboards/`
3. Select Prometheus data source
4. Click **Import**

---

## Key Panels to Monitor

### 1. Model Drift Dashboard

**Purpose:** Detect feature distribution shifts in real-time

**Panels:**

| Panel | Query | Visualization | Alert Threshold |
|-------|-------|---------------|-----------------|
| **Overall Drift Status** | `ml_drift_detected` | Single Stat | 1 = Drifting |
| **Features Drifted (Count)** | `ml_drift_features_count` | Graph | > 1 feature |
| **PSI by Feature** | `ml_feature_drift_psi` | Heatmap | Color: < 0.1 (green), 0.1–0.25 (yellow), > 0.25 (red) |
| **KS-test p-values** | `ml_feature_drift_ks_pvalue` | Table | p < 0.05 (significant) |
| **Drifted Features List** | `topk(10, ml_feature_drift_psi)` | Table | Sort by PSI desc |

**Layout:**
```
┌─────────────────────────────────────┐
│ Overall Drift (Big Number)          │
├─────────────────────────────────────┤
│ PSI Heatmap (All Features)          │
├─────────────────────────────────────┤
│ KS-test Significance (Table)        │
├─────────────────────────────────────┤
│ Feature PSI Trend (Time Series)     │
└─────────────────────────────────────┘
```

### 2. Prediction Health Dashboard

**Purpose:** Monitor model confidence and decision quality

**Panels:**

| Panel | Query | Visualization | Normal Range |
|-------|-------|---------------|-------------|
| **Avg Confidence** | `ml_prediction_confidence_mean` | Gauge | > 0.50 |
| **Confidence Std Dev** | `ml_prediction_confidence_std` | Gauge | 0.10–0.20 |
| **Default Rate** | `ml_prediction_default_rate` | Gauge | 0.20–0.30 |
| **Predictions/sec** | `rate(ml_predictions_total[1m])` | Graph | — |
| **Decision Split** | `rate(ml_predictions_total[5m])` by decision | Pie Chart | ~24% default |
| **Latency (p50, p95)** | `histogram_quantile(0.95, ml_prediction_latency_seconds_bucket)` | Graph | < 100ms |

### 3. Model Quality Dashboard

**Purpose:** Track model training metrics and drift correlation

**Panels:**

| Panel | Query | Visualization |
|-------|-------|---------------|
| **Test ROC-AUC (Latest)** | `mlflow_run_metric{metric="test_roc_auc"}` | Single Stat (Red < 0.75) |
| **Training Duration** | `mlflow_run_metric{metric="training_duration_seconds"}` | Graph |
| **Feature Importance (Top 5)** | `topk(5, ml_feature_importance)` | Bar Chart |
| **Drift vs ROC-AUC** | `ml_drift_detected` and `mlflow_run_metric{metric="test_roc_auc"}` | Dual-axis graph |

---

## Alert Visualization

### Alerts Panel

Add a **Alerting** panel to show active alerts:

```promql
ALERTS{severity="warning"} or ALERTS{severity="critical"}
```

Display as **Table**:
- Columns: `alertname`, `severity`, `instance`, `summary`
- Refresh: 30 seconds

### Alert Status Gauge

Show count of firing alerts:

```promql
count(ALERTS{severity="critical"}) as critical_count
count(ALERTS{severity="warning"}) as warning_count
```

---

## Grafana Variables (Dynamic Filters)

Add template variables for easier filtering:

### Variable: Feature

**Type:** Query  
**Query:**
```promql
label_values(ml_feature_drift_psi, feature)
```

**Use in panels:**
```promql
ml_feature_drift_psi{feature="$feature"}
```

### Variable: Decision Type

**Type:** Query  
**Query:**
```promql
label_values(ml_predictions_total, decision)
```

---

## Dashboard JSON Example

Minimal dashboard definition:

```json
{
  "dashboard": {
    "title": "Model Drift Detection",
    "panels": [
      {
        "title": "Overall Drift",
        "type": "stat",
        "targets": [
          {
            "expr": "ml_drift_detected",
            "legendFormat": "Drifting"
          }
        ]
      }
    ]
  }
}
```

Export dashboards via **Dashboard menu → Export**.

---

## Performance Tips

1. **Reduce metric cardinality** — Use `topk()` for heatmaps, not all features
2. **Increase scrape interval** — Change Prometheus scrape_interval to 60s if storage is tight
3. **Use dashboard refresh rate** — Set to 30–60s for drift monitoring (real-time not needed)
4. **Archive old alerts** — Alertmanager retention to 15 days

---

## Troubleshooting

### "No data" in panels?

1. Verify Prometheus scrape: `http://localhost:9090/graph`
2. Check data source connectivity in Grafana settings
3. Verify metrics are being exported: `curl http://localhost:8006/metrics`

### Dashboards not loading on startup?

1. Check `monitoring/grafana/provisioning/dashboards/` for JSON files
2. Verify file permissions: `ls -la monitoring/grafana/provisioning/`
3. Check Grafana logs: `docker logs <grafana-container>`

### High dashboard load time?

1. Reduce number of panels
2. Increase Prometheus scrape interval
3. Use recording rules for frequently-queried metrics

---

## Export & Backup

**Export dashboards:**
```bash
# Via UI: Dashboard → Export → JSON
# Or programmatically:
curl -s http://localhost:3000/api/dashboards/db/model-drift-detection \
  -H "Authorization: Bearer $GRAFANA_API_TOKEN" > dashboards/model-drift-detection.json
```

**Backup provisioning configs:**
```bash
tar -czf grafana-backup.tar.gz monitoring/grafana/provisioning/
```

See [Alert Rules](alerts-rules.md) for alert configuration in Grafana.
