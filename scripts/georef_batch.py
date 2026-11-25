import sys
from pathlib import Path
import geopandas as gpd

# for suppressing Magic Georeferencer's internal debugging statements
from contextlib import redirect_stdout
from io import StringIO

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
    initialize_matcher,
    process_one_photo,
    update_match_metrics,
    update_georef_status
)

# Paths
TRACKER_PATH = cfg["paths"]["tracker"]

# ----------
# Batch workflow
# ----------

tracker = gpd.read_file(TRACKER_PATH, layer="photos")

chunk_size = cfg["chunk_size"]

if chunk_size is not None:
    chunk_size = int(chunk_size)
    if chunk_size < 1:
        raise ValueError("chunk size must be positive or null")

# Check for duplicate IDs before processing.
if not tracker["cty_year_id"].is_unique:
    raise ValueError("Duplicate cty_year_id values in tracker")

print(f"Photographs in tracker: {len(tracker)}")
print(f"Chunk size: {cfg['chunk_size']}")

# Initialize processing objects once.
fetcher = TileFetcher()
generator = GCPGenerator()
georeferencer = Georeferencer(iface=iface)
matcher = initialize_matcher()

succeeded = 0
skipped = 0
failed = 0
attempted = 0
failures = []

for _, photo in tracker.iterrows():
    photo_id = str(photo["cty_year_id"])
    paths = photo_paths(photo, cfg)

    jpeg_path = paths["jpeg"]
    output_path = paths["geotiff"]

    # Skip photographs with existing outputs.
    if output_path.is_file():
        print(f"SKIP: {photo_id} (output exists)")
        skipped += 1
        continue

    # Stop after attempting the configured number of photographs.
    if chunk_size is not None and attempted >= chunk_size:
        print(f"Reached processing limit: {chunk_size}")
        break

    attempted += 1

    print(f"\n{'=' * 60}")
    print(f"Processing {photo_id}")

    try:
        # suppresses excess debugging
        # but save it to a variable for future use
        debug_output = StringIO()

        with redirect_stdout(StringIO()):
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

        # print just the useful metrics
        print(
            f"Matches: {metrics['match_count']} | "
            f"GCPs: {metrics['gcp_count']} | "
            f"Confidence: {metrics['confidence']:.3f} | "
            f"Matching time: {metrics['match_seconds']:.1f}s"
        )        

        # Update matching metrics.
        tracker_metrics = metrics

        update_match_metrics(
            TRACKER_PATH,
            photo_id,
            tracker_metrics,
        )

        update_georef_status(
            TRACKER_PATH,
            photo_id,
            status="success",
        )

        succeeded += 1
        print(f"SUCCESS: {photo_id}")

    except Exception as exc:
        failed += 1
        print(f"FAILED: {photo_id}: {exc}")

        failures.append({
            "photo_id": photo_id,
            "error": str(exc),
        })

        try:
            update_georef_status(
                TRACKER_PATH,
                photo_id,
                status="failed",
                error=str(exc),
            )
        except Exception as tracking_exc:
            print(f"Could not record failure: {tracking_exc}")

print(f"\n{'=' * 60}")
print("BATCH COMPLETE")
print(f"Batch:     {cfg['batch_name']}")
print(f"Attempted: {attempted}")
print(f"Succeeded: {succeeded}")
print(f"Skipped:   {skipped}")
print(f"Failed:    {failed}")

if attempted > 0:
    print(f"Success rate: {succeeded / attempted:.1%}")

if failures:
    print(f"\n{'-' * 60}")
    print("FAILURE REPORT")

    for failure in failures:
        print(f"\nPhoto: {failure['photo_id']}")
        print(f"Error: {failure['error']}")

print(f"\n{'=' * 60}")