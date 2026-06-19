# Alert Rules & Runbooks

Production alert definitions and escalation procedures for the MLOps Observability Platform.

## Alert Definitions

### 1. ModelDriftDetected

**Severity:** ⚠️ Warning  
**Duration:** 2 minutes  
**Condition:** `ml_drift_detected == 1 for 2m`

**What it means:**
One or more features show significant Population Stability Index (PSI > 0.25), indicating the current data distribution is substantially different from training data.

**Common causes:**
- Seasonal change in customer behavior
- Data collection pipeline misconfiguration
- External market conditions affecting applicants
- Feature encoding bug in upstream system

**Action:**
1. Check [Model Drift Runbook](../runbooks/model-drift-detected.md)
2. Review drifted features: `ml_feature_drift_psi` for specific features
3. Compare baseline vs current feature distributions in Grafana
4. If false positive: verify PSI thresholds in `app/anomaly_detection/config.py`

**Escalation:**
- Warn: ML team lead (2min)
- Critical: Trigger retraining if drift persists >15min

---

### 2. PredictionConfidenceLow

**Severity:** ⚠️ Warning  
**Duration:** 5 minutes  
**Condition:** `ml_prediction_confidence_mean < 0.35 for 5m`

**What it means:**
Average prediction probability is clustering around 0.5, indicating model uncertainty. This often precedes accuracy degradation and can be a **leading indicator** before drift or ROC-AUC drops.

**Common causes:**
- Feature drift not yet detected by PSI
- Model trained on insufficient data
- Overlapping class distributions in data
- Confidence threshold needs calibration

**Action:**
1. Check `ml_prediction_confidence_std` — high std is less alarming than low mean
2. Compare to `ml_drift_detected` — if drifting, confidence drop is expected
3. Review recent predictions in inference server logs
4. If clustered at 0.50: model may need retraining

**Escalation:**
- Warn: ML team (5min)
- Critical: If also drifting, trigger retraining

---

### 3. ModelAccuracyDegraded

**Severity:** 🔴 Critical  
**Duration:** Immediate  
**Condition:** `mlflow_run_metric{metric="test_roc_auc"} < 0.75`

**What it means:**
Test ROC-AUC from the latest trained model is below acceptable threshold (production baseline: 0.829). This occurs only when a new model is registered and evaluated.

**Common causes:**
- Auto-retraining on degraded/drifted data
- Insufficient training samples
- Feature engineering regression
- Class imbalance worsened

**Action:**
1. Check [Model Retraining Runbook](../runbooks/model-retraining.md)
2. Review MLflow experiment: which features were selected?
3. Inspect training data quality: default rate, feature distributions
4. Decide: Rollback model or investigate root cause

**Escalation:**
- Immediate: ML team lead + on-call engineer
- Consider: Disable auto-retraining, manual review required

---

### 4. HighDefaultRate

**Severity:** ⚠️ Warning  
**Duration:** 10 minutes  
**Condition:** `ml_prediction_default_rate > 0.50 for 10m`

**What it means:**
>50% of live predictions are "default" decisions. This is either:
- Model is overly conservative (threshold too low)
- Actual portfolio risk has increased significantly
- Data quality issue

**Baseline:** ~24% default rate in training data

**Action:**
1. Compare to `ml_drift_detected` and `ml_prediction_confidence_mean`
2. If confidence is high: data quality is genuinely worse, not model issue
3. Review decision threshold in `app/serving/config.py`
4. Check with business: is this a portfolio shift or model miscalibration?

**Escalation:**
- Notify: Risk & Compliance team + ML team

---

### 5. InferenceServerDown

**Severity:** 🔴 Critical  
**Duration:** 1 minute  
**Condition:** `ml_inference_server_up == 0 for 1m`

**What it means:**
Inference server is not responding to health checks. Predictions cannot be made.

**Action:**
1. Check [Inference Server Runbook](../runbooks/inference-server-down.md)
2. SSH to inference server pod: `kubectl logs -f deployment/inference-server`
3. Check if model is loading: "Loading model from MLflow"
4. Verify MLflow connectivity: `curl -s http://mlflow:5000/health`
5. Restart if needed: `kubectl rollout restart deployment/inference-server`

**Escalation:**
- Immediate: SRE + ML team on-call
- This is a production outage

---

### 6. MetricsExporterDown

**Severity:** ⚠️ Warning  
**Duration:** 2 minutes  
**Condition:** `ml_metrics_exporter_up == 0 for 2m`

**What it means:**
Metrics exporter cannot bridge MLflow metrics to Prometheus. Observability is degraded but inference still works.

**Action:**
1. Check exporter logs: `kubectl logs deployment/metrics-exporter`
2. Verify MLflow connectivity: can exporter reach MLflow?
3. Check if exporter process crashed: restart `deployment/metrics-exporter`

**Escalation:**
- Notify: ML team (not critical)

---

## Alert Thresholds & Rationale

| Alert | Threshold | Reasoning |
|-------|-----------|-----------|
| ModelDriftDetected | PSI > 0.25 | Industry standard for "significant" drift |
| PredictionConfidenceLow | mean < 0.35 | Indicates model uncertainty; precedes accuracy drop |
| ModelAccuracyDegraded | ROC-AUC < 0.75 | 8.5% drop from production baseline (0.829) |
| HighDefaultRate | default_rate > 50% | 2x the training baseline (24%) |
| InferenceServerDown | up == 0 for 1m | Production outage threshold |
| MetricsExporterDown | up == 0 for 2m | Non-critical; slightly longer grace period |

**Tuning:** Adjust in `monitoring/prometheus/alert_rules.yml` based on your SLOs.

---

## Escalation Matrix

| Alert | Severity | On-Call | Escalate | Time |
|-------|----------|---------|----------|------|
| ModelDriftDetected | Warning | ML Team Lead | Director if >15min | 2min |
| PredictionConfidenceLow | Warning | ML Team | ML Lead + SRE if also drifting | 5min |
| ModelAccuracyDegraded | Critical | ML Lead + SRE | VP Eng if not resolved | Immediate |
| HighDefaultRate | Warning | Risk + ML | CFO if portfolio decision | 10min |
| InferenceServerDown | Critical | SRE + ML | VP Eng + On-call | 1min |
| MetricsExporterDown | Warning | ML Team | — | 2min |

---

## Notification Channels

Configure in `monitoring/alertmanager/alertmanager.yml`:

```yaml
global:
  resolve_timeout: 5m

route:
  receiver: 'default'
  group_by: ['alertname']
  group_wait: 10s
  group_interval: 10s
  repeat_interval: 12h
  routes:
    - match:
        severity: critical
      receiver: 'pagerduty-critical'
      continue: true
    - match:
        severity: warning
      receiver: 'slack-warnings'

receivers:
  - name: 'default'
    slack_configs:
      - api_url: $SLACK_WEBHOOK_URL
        channel: '#ml-alerts'

  - name: 'pagerduty-critical'
    pagerduty_configs:
      - service_key: $PAGERDUTY_SERVICE_KEY

  - name: 'slack-warnings'
    slack_configs:
      - api_url: $SLACK_WEBHOOK_URL
        channel: '#ml-warnings'
```

---

## Testing Alerts

Simulate alerts locally for testing:

```bash
# Trigger drift alert (set metric to 1)
curl -s -X POST http://localhost:9093/api/v1/alerts -H "Content-Type: application/json" \
  -d '[{
    "status": "firing",
    "labels": {
      "alertname": "ModelDriftDetected",
      "severity": "warning"
    },
    "annotations": {
      "summary": "Model drift detected — income, debt_to_income, missed_payments",
      "description": "3 features with PSI > 0.25"
    }
  }]'
```

See runbooks in [`docs/runbooks/`](../runbooks/) for detailed remediation steps.
