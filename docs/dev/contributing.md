# Development & Contributing Guide

Guide for developers contributing to the MLOps Observability Platform.

## Local Development Setup

### Prerequisites

- **Python 3.12+**
- **Docker Desktop** (for local services)
- **Git**
- **Make** (optional, for shortcuts)

### 1. Clone Repository

```bash
git clone https://github.com/thomasasamba-bot/02-observability-ml-alerting
cd 02-observability-ml-alerting
```

### 2. Set Up Virtual Environment

```bash
# Create virtual environment
python -m venv .venv

# Activate it
source .venv/bin/activate  # macOS/Linux
# or
.venv\Scripts\activate     # Windows

# Upgrade pip
pip install --upgrade pip
```

### 3. Install Dependencies

```bash
# Production dependencies
pip install -r requirements.txt

# Development dependencies
pip install -r requirements-dev.txt  # If exists
# Or manually:
pip install pytest pytest-cov ruff black mypy sphinx
```

### 4. Generate Test Data

```bash
python scripts/data/generate_data.py
```

### 5. Start Services (4 Terminals)

**Terminal 1 — MLflow:**
```bash
source .venv/bin/activate
mlflow server --host 0.0.0.0 --port 5000
```
Then open: http://localhost:5000

**Terminal 2 — Inference Server:**
```bash
source .venv/bin/activate
uvicorn app.serving.app:app --host 0.0.0.0 --port 8006 --reload
```
Then test: `curl http://localhost:8006/health/live`

**Terminal 3 — Metrics Exporter:**
```bash
source .venv/bin/activate
uvicorn app.exporter.metrics_exporter:app --host 0.0.0.0 --port 8007 --reload
```
Then test: `curl http://localhost:8007/health`

**Terminal 4 — Development/Testing:**
```bash
source .venv/bin/activate
# Run tests, train models, etc.
```

---

## Project Structure

```
.
├── app/                          # Main application code
│   ├── anomaly_detection/        # Infrastructure anomaly detection
│   ├── exporter/                 # Metrics exporter
│   ├── pipeline/                 # ML pipeline (train, predict, drift)
│   └── serving/                  # FastAPI inference server
├── tests/                        # Test suite
│   ├── unit/                     # Offline unit tests (86 tests)
│   ├── integration/              # Integration tests
│   └── chaos/                    # Chaos engineering tests
├── infra/                        # Infrastructure as Code
│   ├── docker/                   # Docker files
│   ├── kubernetes/               # K8s manifests
│   └── terraform/                # Terraform configs
├── scripts/                      # Utility scripts
│   ├── bootstrap/                # Setup scripts
│   ├── data/                     # Data generation
│   └── deployment/               # Deployment scripts
├── monitoring/                   # Observability configs
│   ├── prometheus/               # Alert rules
│   ├── grafana/                  # Dashboards
│   └── alertmanager/             # Alert routing
├── docs/                         # Documentation
│   ├── observability/            # Metrics, alerts, Grafana
│   ├── guides/                   # CI/CD, config, troubleshooting
│   ├── api/                      # API reference
│   ├── runbooks/                 # Runbook procedures
│   └── architecture/             # Architecture diagrams
└── README.md                     # This file
```

---

## Development Workflow

### 1. Create a Branch

```bash
git checkout -b feature/your-feature-name
# or
git checkout -b fix/issue-number
```

**Branch naming conventions:**
- `feature/*` — New features
- `fix/*` — Bug fixes
- `docs/*` — Documentation
- `chore/*` — Refactoring, dependencies
- `test/*` — Test improvements

### 2. Make Changes

Edit code in your editor. Use proper formatting:

```bash
# Format code
ruff check --fix app/ scripts/ tests/

# Type checking
mypy app/ --ignore-missing-imports

# Manual style check
ruff check app/ scripts/ tests/ --output-format=github
```

### 3. Run Tests Locally

```bash
# Generate data (one time)
python scripts/data/generate_data.py

# Run all unit tests
pytest tests/unit/ -v

# Run specific test
pytest tests/unit/test_drift_detector.py -v

# With coverage
pytest tests/unit/ --cov=app --cov-report=html

# Run integration tests (requires services running)
pytest tests/integration/ -v
```

### 4. Commit Changes

```bash
git add .
git commit -m "descriptive message

Longer explanation if needed. Reference issue #123."
```

**Commit message conventions:**
- Use imperative mood: "Add feature" not "Added feature"
- Keep subject line < 50 characters
- Reference issue numbers: "Fixes #123"

### 5. Push and Create Pull Request

```bash
git push origin feature/your-feature-name
```

Then create PR on GitHub. CI will automatically run:
- Linting (ruff)
- Unit tests (pytest)
- Drift detection gate
- Security scanning

---

## Code Style & Standards

### Imports

Sorted automatically by ruff:
```python
import sys
from pathlib import Path
from typing import Optional

import numpy as np
from pydantic import BaseModel

from app.utils import logger
```

### Type Hints

Always add type hints:

```python
def predict(
    features: dict[str, float],
    threshold: float = 0.40
) -> dict[str, Any]:
    """Make a prediction."""
    ...
```

### Docstrings

Use Google-style docstrings:

```python
def calculate_psi(
    baseline: np.ndarray,
    current: np.ndarray,
    bins: int = 10
) -> float:
    """Calculate Population Stability Index.
    
    Args:
        baseline: Training data distribution.
        current: Current data distribution.
        bins: Number of bins for histogram.
    
    Returns:
        PSI value (0 = stable, >0.25 = drift).
    
    Raises:
        ValueError: If arrays have mismatched shapes.
    """
    ...
```

### Logging

Use structured logging:

```python
from app.utils.logger import get_logger

logger = get_logger(__name__)

logger.info("Training model", extra={"model": "RandomForest"})
logger.warning("Drift detected", extra={"feature": "income", "psi": 0.26})
logger.error("Model load failed", exc_info=True)
```

---

## Adding Tests

### Unit Tests (Offline)

```python
# tests/unit/test_my_feature.py

import pytest
from app.my_module import my_function

def test_happy_path():
    result = my_function(input_value=42)
    assert result == expected_output

def test_edge_case_raises():
    with pytest.raises(ValueError):
        my_function(input_value=-1)

@pytest.fixture
def sample_data():
    return {"key": "value"}

def test_with_fixture(sample_data):
    result = my_function(sample_data)
    assert result is not None
```

Run: `pytest tests/unit/test_my_feature.py -v`

### Integration Tests (Requires Services)

```python
# tests/integration/test_end_to_end.py

import pytest
import requests

@pytest.mark.integration
def test_predict_end_to_end():
    # Requires inference server running on :8006
    response = requests.post(
        "http://localhost:8006/predict",
        json={...}
    )
    assert response.status_code == 200
    assert "prediction" in response.json()
```

Run: `pytest tests/integration/ -v`

---

## Debugging

### VS Code Debug Configuration

Create `.vscode/launch.json`:

```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Python: Training",
      "type": "python",
      "request": "launch",
      "module": "app.pipeline.train",
      "console": "integratedTerminal"
    },
    {
      "name": "Python: Tests",
      "type": "python",
      "request": "launch",
      "module": "pytest",
      "args": ["tests/unit/", "-v"],
      "console": "integratedTerminal"
    }
  ]
}
```

### Print Debugging

```python
import pdb

# Breakpoint (Python 3.7+)
breakpoint()  # Debugger will pause here

# Or inspect variables
print(f"Debug: {variable_name = }")  # Python 3.8+
```

### Profiling

```bash
# Profile training
python -m cProfile -s cumtime -m app.pipeline.train | head -20

# Profile predictions
python -m cProfile -s cumtime -m app.serving.app
```

---

## Documentation

### Docstring Format

Use Google style (already enforced):
```python
"""Short description.

Longer description spanning multiple lines if needed.

Args:
    param1: Description of param1.
    param2: Description of param2.

Returns:
    Description of return value.

Raises:
    CustomException: When this condition occurs.
"""
```

### Update README

When adding major features:
1. Update `## Architecture` section if architecture changed
2. Add to `## What's inside` table
3. Add API docs to relevant section
4. Link to detailed docs in `docs/`

### Add Docs

New detailed docs should go in:
- `docs/guides/` — Operational guides
- `docs/api/` — API reference
- `docs/observability/` — Monitoring/alerting
- `docs/runbooks/` — Incident response

See [Documentation Structure](../README.md#documentation) for template.

---

## Dependency Management

### Adding Dependencies

```bash
# Add production dependency
pip install package-name
pip freeze > requirements.txt

# Or for dev-only
pip install pytest-plugin
# Add to requirements-dev.txt manually
```

### Updating Dependencies

```bash
# Update all packages
pip install --upgrade -r requirements.txt

# Update specific package
pip install --upgrade package-name
pip freeze > requirements.txt

# Check for security issues
pip-audit -r requirements.txt
```

### Version Pinning

Pin in `requirements.txt` for reproducibility:
```
pandas==2.1.4
numpy>=1.24,<2.0
scikit-learn~=1.3.0  # Allows patch updates
```

---

## Before Submitting PR

Checklist:

- [ ] Code follows style guide (ran `ruff check --fix`)
- [ ] Tests pass locally (`pytest tests/unit/ -v`)
- [ ] New features have tests
- [ ] Documentation updated
- [ ] Commit message is descriptive
- [ ] No secrets or credentials in code
- [ ] No unnecessary dependencies added

---

## Code Review

**What reviewers look for:**
1. Correctness — Does it work as intended?
2. Style — Follows project conventions?
3. Tests — Adequate test coverage?
4. Documentation — Clear and helpful?
5. Performance — No regressions?
6. Security — No vulnerabilities introduced?

**Addressing feedback:**
```bash
# Make requested changes
git add .
git commit -m "Address review feedback"
git push  # Auto-updates PR
```

---

## Release Process

Releasing a new version:

```bash
# Update version
# 1. Update version in setup.py or __init__.py
# 2. Update CHANGELOG.md
# 3. Commit & tag

git tag v1.2.3
git push --tags

# GitHub Actions will build and release automatically
```

---

## Getting Help

- **Questions?** Check [Troubleshooting Guide](troubleshooting.md)
- **How do I?** Check [Configuration Reference](configuration.md)
- **API docs?** Check [API Reference](../api/endpoints.md)
- **CI issues?** Check [CI/CD Guide](ci-cd-pipeline.md)

---

## Related Resources

- [MLflow Documentation](https://mlflow.org/docs/latest/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Pytest Documentation](https://docs.pytest.org/)
- [Kubernetes Documentation](https://kubernetes.io/docs/)
- [Prometheus Documentation](https://prometheus.io/docs/)

Happy coding! 🚀
