import sys
from pathlib import Path

# Locate project root for execution in QGIS Python console.
PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

#Load configuration.
from src.config import load_config, photo_paths
cfg = load_config()

# Make Magic Georeferencer importable
MG_ROOT = cfg["paths"]["mg_root"]

if str(MG_ROOT) not in sys.path:
    sys.path.insert(0, str(MG_ROOT))

# Import external dependencies
from magic_georeferencer.core.tile_fetcher import TileFetcher
from magic_georeferencer.core.gcp_generator import GCPGenerator
from magic_georeferencer.core.georeferencer import Georeferencer


# Import project functions
from src.georeferencing import (
    select_photo,
    initialize_matcher,
    process_one_photo,
    update_match_metrics
)

# Paths
TRACKER_PATH = cfg["paths"]["tracker"]
CTY_YEAR_ID = cfg["single_photo_id"]

# ----------
# Workflow
# ----------

# 1. Select and locate the prepared photo
photo = select_photo(TRACKER_PATH, CTY_YEAR_ID)

paths = photo_paths(photo, cfg)

jpeg_path = paths["jpeg"]
output_path = paths["geotiff"]

print("Tracker:", TRACKER_PATH)
print("JPEG:", jpeg_path)
print("Output:", output_path)

if not jpeg_path.is_file():
    raise FileNotFoundError(jpeg_path)

# Initialize reusable processing objects.
fetcher = TileFetcher()
generator = GCPGenerator()
georeferencer = Georeferencer(iface=iface)

# Load matching model if needed.
if "matcher" not in globals() or matcher.model_manager.model is None:
    matcher = initialize_matcher()
else:
    print("Reusing existing matching model")

# Process one photograph.
metrics = process_one_photo(
    photo=photo,
    jpeg_path=jpeg_path,
    output_path=output_path,
    matcher=matcher,
    fetcher=fetcher,
    generator=generator,
    georeferencer=georeferencer,
    cfg=cfg,
)

# Update the tracker after successful processing.
tracker_metrics = {
    key: value
    for key, value in metrics.items()
    if key != "gcp_count"
}

update_match_metrics(
    TRACKER_PATH,
    CTY_YEAR_ID,
    tracker_metrics,
)

print(f"\nFinished processing {CTY_YEAR_ID}")
print("Output:", output_path)
print("Metrics:", metrics)