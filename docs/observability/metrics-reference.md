# Prometheus Metrics Reference

Complete catalog of all Prometheus metrics exported by the MLOps Observability Platform.

## Drift Detection Metrics

| Metric | Type | Labels | Description | Example |
|--------|------|--------|-------------|---------|
| `ml_feature_drift_psi` | Gauge | `feature` | Population Stability Index per feature vs training baseline | `0.2635` (income) |
| `ml_feature_drift_ks_statistic` | Gauge | `feature` | Kolmogorov-Smirnov test statistic per feature | `0.2190` |
| `ml_feature_drift_ks_pvalue` | Gauge | `feature` | KS-test p-value (significance of drift) | `0.0000` (significant) |
| `ml_drift_detected` | Gauge | — | Binary flag: 1 if any feature PSI > 0.25 | `1` (drift) or `0` (stable) |
| `ml_drift_features_count` | Gauge | — | Number of features exceeding alert threshold | `3` |
| `ml_drift_window_size` | Gauge | — | Number of records in current drift check window | `1000` |

**Notes:**
- PSI thresholds: `< 0.10` (stable), `0.10–0.25` (monitor), `> 0.25` (investigate)
- KS-test: `p < 0.05` indicates statistically significant shift
- Drift checks run every 60s (configurable via `DRIFT_CHECK_INTERVAL`)

## Prediction Metrics

| Metric | Type | Labels | Description | Range |
|--------|------|--------|-------------|-------|
| `ml_prediction_confidence_mean` | Gauge | — | Rolling mean of prediction probabilities | `0.0–1.0` |
| `ml_prediction_confidence_std` | Gauge | — | Rolling std of prediction probabilities | `0.0–0.5` |
| `ml_prediction_confidence_min` | Gauge | — | Min prediction probability in window | `0.0–1.0` |
| `ml_prediction_confidence_max` | Gauge | — | Max prediction probability in window | `0.0–1.0` |
| `ml_prediction_default_rate` | Gauge | — | Proportion of "default" decisions in live predictions | `0.0–1.0` |
| `ml_predictions_total` | Counter | `decision` | Total predictions by decision class (`default`, `no_default`) | cumulative |
| `ml_prediction_latency_seconds` | Histogram | — | End-to-end prediction latency | buckets: 0.01s–10s |
| `ml_prediction_latency_seconds_sum` | Gauge | — | Total latency across all predictions | seconds |
| `ml_prediction_latency_seconds_count` | Gauge | — | Total prediction count | count |

**Notes:**
- Confidence mean < 0.35 for 5min is a **leading indicator** of accuracy degradation
- Confidence clustering toward 0.5 suggests model uncertainty (often precedes drift detection)
- Latency percentiles can be derived from histogram buckets

## Model Quality Metrics (from MLflow)

| Metric | Type | Description | Source |
|--------|------|-------------|--------|
| `mlflow_run_metric{experiment="credit-scoring",metric="test_roc_auc"}` | Gauge | Latest test ROC-AUC from trained model | MLflow Tracking Server |
| `mlflow_run_metric{experiment="credit-scoring",metric="test_f1"}` | Gauge | Latest test F1 score | MLflow |
| `mlflow_run_metric{experiment="credit-scoring",metric="train_roc_auc"}` | Gauge | Cross-validation ROC-AUC | MLflow |
| `mlflow_run_metric{experiment="credit-scoring",metric="training_duration_seconds"}` | Gauge | Time to train model | MLflow |
| `ml_model_version` | Gauge | Current model version loaded in inference server | Inference Server |

## Dataset Metrics

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `ml_dataset_feature_mean` | Gauge | `dataset`, `feature` | Feature mean by dataset (`training`, `live`) |
| `ml_dataset_feature_std` | Gauge | `dataset`, `feature` | Feature std by dataset |
| `ml_dataset_record_count` | Gauge | `dataset` | Total records in dataset |
| `ml_schema_feature_mean` | Gauge | `feature` | Training-set feature mean (baseline) |
| `ml_schema_feature_std` | Gauge | `feature` | Training-set feature std (baseline) |

## Infrastructure Anomaly Detection Metrics

| Metric | Type | Description | Anomaly Methods |
|--------|------|-------------|-----------------|
| `infrastructure_cpu_zscore` | Gauge | Z-Score anomaly on CPU usage | Z-Score |
| `infrastructure_memory_ewma` | Gauge | EWMA anomaly on memory usage | EWMA |
| `infrastructure_disk_isolation_forest` | Gauge | Isolation Forest anomaly on disk usage | Isolation Forest |
| `infrastructure_anomaly_composite_score` | Gauge | Weighted composite anomaly score | All three methods |

## System Metrics

| Metric | Type | Description |
|--------|------|-------------|
| `ml_inference_server_up` | Gauge | 1 if inference server is healthy | 
| `ml_metrics_exporter_up` | Gauge | 1 if metrics exporter is running |
| `ml_mlflow_server_up` | Gauge | 1 if MLflow tracking server is reachable |
| `process_resident_memory_bytes` | Gauge | Process memory usage |
| `process_cpu_seconds_total` | Counter | Process CPU time |

---

## Prometheus Query Examples

### Detection Performance Dashboard

```promql
# Is the model currently drifting?
ml_drift_detected

# Which features are drifting most?
sort_desc(ml_feature_drift_psi)

# Model confidence trend (last 6 hours)
rate(ml_prediction_latency_seconds_sum[5m]) / rate(ml_prediction_latency_seconds_count[5m])

# Default rate rising?
ml_prediction_default_rate

# Test ROC-AUC over time
mlflow_run_metric{metric="test_roc_auc"}
```

### Alert-Ready Queries

```promql
# Drift detected for >2m
ml_drift_detected == 1 for 2m

# Confidence degradation
ml_prediction_confidence_mean < 0.35 for 5m

# Model accuracy critical
mlflow_run_metric{metric="test_roc_auc"} < 0.75

# High default rate
ml_prediction_default_rate > 0.50 for 10m
```

### Baseline Comparison

```promql
# Income feature drift over time
ml_feature_drift_psi{feature="income"}

# Compare to KS-test statistical significance
ml_feature_drift_ks_pvalue{feature="income"}

# Feature-by-feature PSI heatmap
topk(10, ml_feature_drift_psi)
```

---

## Scrape Configuration

Add to your `prometheus.yml`:

```yaml
global:
  scrape_interval: 30s

scrape_configs:
  - job_name: 'inference-server'
    static_configs:
      - targets: ['localhost:8006']
    metrics_path: '/metrics'

  - job_name: 'metrics-exporter'
    static_configs:
      - targets: ['localhost:8007']
    metrics_path: '/metrics'

  - job_name: 'mlflow'
    static_configs:
      - targets: ['localhost:5000']
    metrics_path: '/metrics'
```

---

## Retention & Storage

- **Default retention:** 15 days (Prometheus)
- **High-cardinality metrics:** Drift detection features (8 features = 8 PSI series)
- **Typical disk usage:** ~500MB per week at 30s scrape interval
- **Recommendation:** 2-3 weeks retention for drift trending analysis

See [Grafana Setup Guide](grafana-setup.md) for dashboard configuration.
