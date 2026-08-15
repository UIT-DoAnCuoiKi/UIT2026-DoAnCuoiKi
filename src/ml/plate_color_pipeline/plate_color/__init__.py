"""plate_color — Vietnamese plate background classification and crop enhancement."""
from __future__ import annotations

from .types import PlateAppearance
from .pipeline import process_plate

__all__ = ["PlateAppearance", "process_plate"]
