import sys
from pathlib import Path

# Paths
PROJECT_ROOT = Path(
    r"C:\Users\eu01251115\LocalProjects\batch_georef"
)

from src.config import load_config

cfg = load_config()

GEOREFIO_ROOT = cfg["mg_root"]

TRACKER_PATH = cfg["paths"]["tracker"]

DOWNLOADS = cfg["paths"]["downloads"]

CTY_YEAR_ID = cfg["single_photo_id"]

# Imports
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(GEOREFIO_ROOT))

from magic_georeferencer.core.tile_fetcher import TileFetcher
from magic_georeferencer.core.model_manager import ModelManager
from magic_georeferencer.core.matcher import Matcher
from magic_georeferencer.core.gcp_generator import GCPGenerator
from magic_georeferencer.core.georeferencer import Georeferencer

from qgis.core import QgsCoordinateReferenceSystem

from georeferencing import (
    select_photo,
    load_photo_image,
    get_reference_image,
    initialize_matcher,
    update_match_metrics
)

# 1. Select and locate the prepared photo
photo = select_photo(TRACKER_PATH, CTY_YEAR_ID)

jpeg_path = (
        Path(DOWNLOADS)
        / f"{photo['cty_year_id']}_original.jpg"
    )

if not jpeg_path.is_file():
    raise FileNotFoundError(jpeg_path)

# 2. Load historical JPEG

image_src = load_photo_image(jpeg_path)

print(f"Photo: {photo['cyt_year_id']}")
print(f"Historical image: {image_src.shape}")

# 3. Retrieve reference imagery
fetcher = TileFetcher()

image_ref, ref_extent = get_reference_image(
    photo,
    fetcher,
    source_name="esri_world_imagery",
    target_size=832,
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

# 4. Initialize and load the matching model
# only if it isn't loaded already
if "matcher" not in globals() or matcher.model_manager.model is None:
    print("Loading matching model...")

    model_manager = ModelManager()

    print("Model weights available:", model_manager.weights_exist())
    print("Device info:", model_manager.get_device_info())

    success, message = model_manager.load_model()
    print(message)

    if not success:
        raise RuntimeError(message)

    matcher = Matcher(model_manager)

    print("Matcher initialized successfully")
    print("Matching configuration:", matcher.config)
else:
    print("Reusing existing matching model")

# 5. Match historical and reference imagery
match_result = matcher.match_single_scale(
    image_src,
    image_ref,
    size=512,
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
    confidence_threshold=0.20,
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
print("First GCP:", gcps[0])

if len(gcps) < 6:
    raise RuntimeError(
        f"Insufficient GCPs for georeferencing: {len(gcps)}"
    )

# 9. Georeference the image. 

output_path = (
    PROJECT_ROOT
    / "data"
    / "georeferenced"
    / f"{CTY_YEAR_ID}_esri_affine_test.tif"
)

output_path.parent.mkdir(parents=True, exist_ok=True)

georeferencer = Georeferencer(iface=iface)

success, message = georeferencer.georeference_image(
    source_image_path=jpeg_path,
    gcps=gcps,
    output_path=output_path,
    target_crs=QgsCoordinateReferenceSystem("EPSG:3857"),
    transform_type="polynomial_1",
    resampling="cubic",
    compression="LZW",
)

print("Success:", success)
print(message)