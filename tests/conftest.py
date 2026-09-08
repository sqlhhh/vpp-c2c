"""Put src/ on the import path so tests import modules by name, not by file path."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
