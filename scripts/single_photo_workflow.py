import sys
from pathlib import Path

# Paths
PROJECT_ROOT = Path(
    r"C:\Users\eu01251115\LocalProjects\batch_georef"
)

MG_MODULES = Path(
    r"C:\Users\eu01251115\LocalProjects\georefio\magic_georeferencer\core"
)

TRACKER_PATH = (
    PROJECT_ROOT
    / "data/historic_airphoto_index/subsets"
    / "subset_20000_carver_37_38_40_51_57_63_tracker.gpkg"
)

GEOREFIO_ROOT = Path(
    r"C:\Users\eu01251115\LocalProjects\georefio"
)

download_dir = r"C:\Users\eu01251115\LocalProjects\batch_georef\data\downloads\subset_20000_carver_37_38_40_51_57_63"

SOURCE_ID = "92366"

# Imports
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(MG_MODULES))
sys.path.insert(0, str(GEOREFIO_ROOT))

from tile_fetcher import TileFetcher
from magic_georeferencer.core.model_manager import ModelManager
from magic_georeferencer.core.matcher import Matcher
from src.single_photo import (
    select_photo,
    load_photo_image,
    get_reference_image,
    update_match_metrics
)

# 1. Select prepared photo
photo = select_photo(TRACKER_PATH, SOURCE_ID)

# 2. Load historical JPEG
image_src = load_photo_image(photo, download_dir)

print(f"Photo: {photo['source_id']}")
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
    SOURCE_ID,
    metrics,
)