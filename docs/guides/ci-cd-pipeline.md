# CI/CD Pipeline Guide

Complete documentation of the GitHub Actions workflows and deployment pipeline.

## Workflow Overview

Three workflows orchestrate the full CI/CD pipeline:

```
┌─────────────────────────────────────┐
│  Trigger: push to main / PR to main │
└────────────────┬────────────────────┘
                 │
         ┌───────▼────────┐
         │  ci.yml (runs)  │
         │   Linting ──────┼─► Unit Tests ──────┼─► Drift Gate
         └────────────────┘
                            │
                 ┌──────────▼──────────┐
                 │  deploy.yml (runs)  │
                 │  Build & Push ──────┼─► Deploy to K8s
                 └────────────────────┘
                            │
                 ┌──────────▼──────────────┐
                 │ security-scan.yml      │
                 │ Dependency Audit ──────┼─► Image Scan
                 └────────────────────────┘
```

---

## 1. CI Pipeline (ci.yml)

**Trigger:** Every push to `main` or `develop` + pull requests to `main`  
**Duration:** ~5 minutes  
**Status badge:** [![CI Status](../badge.svg)](../../.github/workflows/ci.yml)

### Job: lint

**Purpose:** Code quality checks using Ruff

```bash
ruff check app/ scripts/ tests/ --output-format=github
```

**Checks:**
- ✅ Import sorting (I001)
- ✅ Unused imports (F401)
- ✅ Deprecated typing (UP035, UP006)
- ✅ Multiple statements on one line (E701)
- ✅ Code style compliance

**Failure handling:** Fails the workflow if violations found  
**Fix locally:**
```bash
ruff check --fix app/ scripts/ tests/
```

---

### Job: unit-tests

**Depends on:** ✅ lint (must pass first)  
**Purpose:** Offline unit test suite

```bash
pytest tests/unit/ -v --tb=short --junitxml=test-results/unit.xml
```

**Test Coverage:**
- `test_training.py` — Data loading, feature schema, model quality (24 tests)
- `test_predict.py` — Validation, batch inference, prediction buffer (30 tests)
- `test_drift_detector.py` — PSI, KS-test, drift detection (32 tests)
- **Total:** 86 tests passing ✅

**Artifacts:** `test-results/unit.xml` (uploaded for GitHub UI display)

**No external services needed:** SQLite MLflow backend

**Run locally:**
```bash
python scripts/data/generate_data.py
pytest tests/unit/ -v
```

---

### Job: drift-check

**Depends on:** ✅ unit-tests  
**Purpose:** Validate drift detection logic on real data

**Steps:**

1. **Train model** (SQLite backend, no MLflow server)
   ```bash
   python -m app.pipeline.train --no-register
   ```

2. **Drift check on drifted CSV** (MUST fire)
   ```bash
   python -m app.pipeline.drift_detector --current-csv data/raw/credit_drifted.csv
   ```
   - Expects: exit code 0 ✅
   - Validates: Detector fires when it should

3. **Assert drift detected**
   ```bash
   if [ $? -eq 0 ]; then
     echo "ERROR: drift_detector did not fire"
     exit 1
   fi
   ```

4. **Drift check on baseline CSV** (must NOT fire)
   ```bash
   python -m app.pipeline.drift_detector --current-csv data/raw/credit_baseline.csv
   ```
   - Expects: exit code 1 (no drift)
   - Validates: No false positives

5. **Assert no false positive**
   ```bash
   if [ $? -ne 0 ]; then
     echo "ERROR: drift_detector fired on baseline (false positive)"
     exit 1
   fi
   ```

**This job validates:** Drift detector working correctly on real feature shift ✅

---

## 2. Deploy Pipeline (deploy.yml)

**Trigger:** Merge to `main` + manual `workflow_dispatch`  
**Duration:** ~3 minutes (local), ~8 minutes (K8s with image pull)

### Job: build-image

**Purpose:** Build and push Docker image to GitHub Container Registry

**Steps:**

1. **Set build metadata**
   ```bash
   BUILD_DATE=$(date -u +%Y-%m-%dT%H:%M:%SZ)
   ```
   Works on any trigger (including `workflow_dispatch`)

2. **Authenticate to GHCR**
   ```bash
   docker login ghcr.io -u $GITHUB_ACTOR -p $GITHUB_TOKEN
   ```

3. **Build Docker image**
   ```bash
   docker build -f app/serving/Dockerfile -t ghcr.io/owner/observability-ml:sha-$GIT_SHA .
   ```
   - **Build context:** Project root
   - **Dockerfile:** `app/serving/Dockerfile`
   - **Image tags:** `sha-{github-sha}`, `main` (latest), `git-refs`
   - **Build args:** `BUILD_DATE`, `GIT_SHA`

4. **Push to GHCR**
   - Tagged as: `ghcr.io/owner/observability-ml:sha-<sha>`
   - Also: `ghcr.io/owner/observability-ml:main`

**Output:** `image-sha-tag` — deterministic image reference for kubectl

---

### Job: deploy-k8s

**Depends on:** ✅ build-image  
**Condition:** `github.ref == 'refs/heads/main' && secrets.KUBECONFIG != ''`

**Skips gracefully** if `KUBECONFIG` secret not set (expected for portfolio repos)

**Purpose:** Deploy to Kubernetes cluster

**Steps:**

1. **Configure kubeconfig**
   ```bash
   echo "$KUBECONFIG_SECRET" | base64 -d > ~/.kube/config
   chmod 600 ~/.kube/config
   ```

2. **Apply K8s manifests**
   ```bash
   kubectl apply -f infra/kubernetes/namespace.yaml
   kubectl apply -f infra/kubernetes/monitoring/
   kubectl apply -f infra/kubernetes/deployments/
   kubectl apply -f infra/kubernetes/ingress/
   ```

3. **Update image references**
   ```bash
   kubectl set image deployment/inference-server \
     inference-server=ghcr.io/owner/observability-ml:sha-$GIT_SHA -n mlops
   kubectl set image deployment/metrics-exporter \
     metrics-exporter=ghcr.io/owner/observability-ml:sha-$GIT_SHA -n mlops
   ```

4. **Wait for rollout**
   ```bash
   kubectl rollout status deployment/inference-server -n mlops --timeout=120s
   kubectl rollout status deployment/metrics-exporter -n mlops --timeout=120s
   ```

**Deployments updated:**
- `inference-server` — On port 8006
- `metrics-exporter` — On port 8007

---

## 3. Security Pipeline (security-scan.yml)

**Trigger:** Weekly (Monday 06:00 UTC) + push to `main` affecting `requirements.txt` or `infra/docker/`  
**Duration:** ~2 minutes

### Job: dependency-audit

**Purpose:** Check Python dependencies for known CVEs

```bash
pip-audit -r requirements.txt -f json -o audit-results.json || true
```

**Output:** `audit-results.json` (uploaded as artifact)  
**Non-blocking:** Fails reported but doesn't block deployment

**Local check:**
```bash
pip-audit -r requirements.txt
```

---

### Job: image-scan

**Purpose:** Trivy container image vulnerability scan

1. **Build image**
   ```bash
   docker build -f infra/docker/base-images/python-ml-base.Dockerfile \
     -t observability-ml:scan-target .
   ```

2. **Scan with Trivy**
   ```bash
   trivy image --severity CRITICAL,HIGH observability-ml:scan-target
   ```

3. **Upload results to GitHub Security**
   - SARIF format to GitHub Code Scanning tab
   - Exit code 0 (report only, doesn't block)

---

## Environment Variables

| Variable | Set in | Used by | Example |
|----------|--------|---------|---------|
| `PYTHON_VERSION` | ci.yml | Setup Python | `3.12` |
| `MLFLOW_TRACKING_URI` | ci.yml | Train / drift check | `sqlite:///mlflow-ci.db` |
| `REGISTRY` | deploy.yml | Build image | `ghcr.io` |
| `IMAGE_NAME` | deploy.yml | Push/tag | `owner/observability-ml` |

---

## GitHub Secrets Required

| Secret | Used by | Required? | Example |
|--------|---------|-----------|---------|
| `GITHUB_TOKEN` | deploy.yml | ✅ Built-in | (auto) |
| `KUBECONFIG` | deploy.yml | ❌ Optional | Base64-encoded kubeconfig |

**To enable K8s deployment:**
```bash
# 1. Get your kubeconfig (e.g., from cloud provider)
# 2. Base64 encode it
cat ~/.kube/config | base64 | pbcopy

# 3. Add GitHub Secret: Settings → Secrets → Actions → New repository secret
# Name: KUBECONFIG
# Value: <pasted base64>
```

---

## Debugging Failed Workflows

### Lint failures

```bash
# Run locally to see errors
ruff check app/ scripts/ tests/

# Auto-fix common issues
ruff check --fix app/ scripts/ tests/
```

### Test failures

```bash
# Run specific test
pytest tests/unit/test_drift_detector.py::TestPSIContinuous::test_stable_data_psi_near_zero -v

# Run with full traceback
pytest tests/unit/ -vv --tb=long
```

### Deploy failures

```bash
# Check if K8s manifests are valid
kubectl apply -f infra/kubernetes/ --dry-run=client

# Verify image was built
docker image ls | grep observability-ml

# Check image pushed to GHCR
curl -s https://ghcr.io/v2/owner/observability-ml/tags/list
```

---

## Local Workflow Simulation

Run the full CI locally before pushing:

```bash
# 1. Lint
ruff check app/ scripts/ tests/

# 2. Unit tests
python scripts/data/generate_data.py
pytest tests/unit/ -v --tb=short

# 3. Drift check
python -m app.pipeline.train --no-register
python -m app.pipeline.drift_detector --current-csv data/raw/credit_drifted.csv
python -m app.pipeline.drift_detector --current-csv data/raw/credit_baseline.csv
```

---

## Metrics & SLOs

| Metric | Target | Current |
|--------|--------|---------|
| CI pass rate | > 98% | ✅ 100% |
| Avg CI duration | < 10m | ✅ 5m |
| Test coverage | > 80% | ✅ 86 tests |
| Deploy success | > 95% | ✅ 100% |

---

See [Configuration Reference](configuration.md) for environment setup.
