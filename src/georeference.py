import sys
from pathlib import Path

PLUGIN_PARENT_DIR = "/Users/eu01251115/LocalProjects/georefio"

sys.path.insert(0, PLUGIN_PARENT_DIR)

try:
    from magic_georeferencer.core.model_manager import ModelManager
    print("Successfully imported ModelManager")
except ImportError as e:
    print("Import failed:", e)