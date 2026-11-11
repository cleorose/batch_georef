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
from magic_georeferencer.core.model_manager import ModelManager
from magic_georeferencer.core.matcher import Matcher
from magic_georeferencer.core.gcp_generator import GCPGenerator
from magic_georeferencer.core.georeferencer import Georeferencer

from qgis.core import QgsCoordinateReferenceSystem

# Import project functions
from src.georeferencing import (
    select_photo,
    load_photo_image,
    get_reference_image,
    initialize_matcher,
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

# some checks
print(cfg["paths"])
print(photo["cty_year_id"])
print(paths)
print(jpeg_path.is_file())

# 2. Load historical JPEG

image_src = load_photo_image(jpeg_path)

print(f"Photo: {photo['cty_year_id']}")
print(f"Historical image: {image_src.shape}")

# 3. Retrieve reference imagery
fetcher = TileFetcher()

image_ref, ref_extent = get_reference_image(
    photo,
    fetcher,
    source_name=cfg["matching"]["reference_source"],
    target_size=cfg["matching"]["reference_size"],
)

print(f"Reference image: {image_ref.shape}")
print(f"Reference extent: {ref_extent.toString()}")

#-------
# VISUAL CHECK
# --------

# import matplotlib.pyplot as plt

# fig, axes = plt.subplots(1, 2, figsize=(14, 7))

# axes[0].imshow(image_src)
# axes[0].set_title("Historical photograph")
# axes[0].axis("off")

# axes[1].imshow(image_ref)
# axes[1].set_title("Esri World Imagery")
# axes[1].axis("off")

# plt.tight_layout()
# plt.show()

# 4. Initialize matching model if needed
if "matcher" not in globals() or matcher.model_manager.model is None:
    matcher = initialize_matcher()
else:
    print("Reusing existing matching model")

# 5. Match historical and reference imagery
match_result = matcher.match_single_scale(
    image_src,
    image_ref,
    size=cfg["matching"]["match_size"],
)

print("\nMATCHING RESULTS")
print("Matches:", match_result.num_matches())
print("Mean confidence:", match_result.mean_confidence())
print("Geometric score:", match_result.geometric_score)
print("Distribution quality:", match_result.distribution_quality)
print("Processing time:", match_result.processing_time)
print("Homography found:", match_result.transform_matrix is not None)

# 6. Filter matches using the permissive threshold
filtered_result = matcher.filter_matches(
    match_result,
    confidence_threshold=cfg["matching"]["confidence_threshold"],
)

print("Filtered matches:", filtered_result.num_matches())

# 7. Save experiment metrics to tracker
metrics = {
    "match_count": match_result.num_matches(),
    "inlier_count": filtered_result.num_matches(),
    "confidence": match_result.mean_confidence(),
    "geometric_score": match_result.geometric_score,
    "distribution_quality": match_result.distribution_quality,
    "match_seconds": match_result.processing_time,
}

update_match_metrics(
    TRACKER_PATH,
    CTY_YEAR_ID,
    metrics,
)

# 8. Generate GCPs

generator = GCPGenerator()

gcps = generator.matches_to_gcps(
    match_result=filtered_result,
    ref_extent=ref_extent,
    ref_crs=QgsCoordinateReferenceSystem("EPSG:3857"),
    ref_image_size=(image_ref.shape[1], image_ref.shape[0]),
    src_image_size=(image_src.shape[1], image_src.shape[0]),
    downsample_factor=1.0,
)

print("Generated GCPs:", len(gcps))

if len(gcps) < cfg["matching"]["min_gcps"]:
    raise RuntimeError(
        f"Insufficient GCPs for georeferencing: {len(gcps)}"
    )

print("First GCP:", gcps[0])

# 9. Georeference the image. 

output_path.parent.mkdir(parents=True, exist_ok=True)

georeferencer = Georeferencer(iface=iface)

success, message = georeferencer.georeference_image(
    source_image_path=jpeg_path,
    gcps=gcps,
    output_path=output_path,
    target_crs=QgsCoordinateReferenceSystem(cfg["georeferencing"]["target_crs"]),
    transform_type=cfg["georeferencing"]["transform"],
    resampling=cfg["georeferencing"]["resampling"],
    compression=cfg["georeferencing"]["compression"],
)

print("Success:", success)
print(message)