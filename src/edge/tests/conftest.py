"""Đưa src/edge lên sys.path để test import được `worker`."""
import sys
from pathlib import Path

EDGE_DIR = Path(__file__).resolve().parents[1]  # src/edge/tests -> src/edge
if str(EDGE_DIR) not in sys.path:
    sys.path.insert(0, str(EDGE_DIR))
