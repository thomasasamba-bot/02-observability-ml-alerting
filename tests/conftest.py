"""
tests/conftest.py

Pytest configuration — adds project root to sys.path so local imports work.
"""

import sys
from pathlib import Path

# Add project root to sys.path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
