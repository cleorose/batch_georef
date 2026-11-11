from pathlib import Path

import geopandas as gpd
import numpy as np
from PIL import Image

from qgis.core import QgsRectangle, QgsCoordinateReferenceSystem
from qgis.core import QgsVectorLayer, QgsField
from qgis.PyQt.QtCore import QVariant

from magic_georeferencer.core.model_manager import ModelManager
from magic_georeferencer.core.matcher import Matcher


def select_photo(tracker_path, cty_year_id, layer="photos"):
    """Select one prepared photo from the tracker."""

    tracker = gpd.read_file(tracker_path, layer=layer)

    matches = tracker.loc[
        tracker["cty_year_id"].astype(str) == str(cty_year_id)
    ]

    if len(matches) != 1:
        raise ValueError(
            f"Expected one photo with cty_year_id={cty_year_id}, "
            f"found {len(matches)}"
        )

    photo = matches.iloc[0]

    if (
        photo["error"] is not None
        and not gpd.pd.isna(photo["error"])
    ):
        raise ValueError(f"Photo has preparation error: {photo['error']}")

    return photo


def load_photo_image(image_path):
    """Load an existing historical JPEG as an RGB NumPy array."""

    if not image_path.is_file():
        raise FileNotFoundError(image_path)

    with Image.open(image_path) as img:
        image = np.array(img.convert("RGB"))

    return image


def get_reference_image(
    photo,
    fetcher,
    source_name="esri_world_imagery",
    target_size=832,
):
    """Retrieve reference imagery using the prepared Web Mercator extent."""

    center_x = photo.geometry.x
    center_y = photo.geometry.y

    half_width = photo["wm_width"] / 2
    half_height = photo["wm_height"] / 2

    extent = QgsRectangle(
        center_x - half_width,
        center_y - half_height,
        center_x + half_width,
        center_y + half_height,
    )

    image, actual_extent = fetcher.render_tiles_with_qgis(
        extent=extent,
        crs=QgsCoordinateReferenceSystem("EPSG:3857"),
        source_name=source_name,
        target_size=target_size,
    )

    return image, actual_extent

def initialize_matcher():
    """Load the matching model and return a ready-to-use Matcher."""

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

    return matcher


def update_match_metrics(tracker_path, cty_year_id, metrics):
    """Add missing metric fields and update one tracker record."""

    layer = QgsVectorLayer(
        f"{tracker_path}|layername=photos",
        "tracker",
        "ogr",
    )

    if not layer.isValid():
        raise RuntimeError("Could not open tracker layer")

    # Add any missing columns
    field_types = {
        "match_count": QVariant.Int,
        "inlier_count": QVariant.Int,
        "confidence": QVariant.Double,
        "geometric_score": QVariant.Double,
        "distribution_quality": QVariant.Double,
        "match_seconds": QVariant.Double,
    }

    layer.startEditing()

    try:
        existing = set(layer.fields().names())

        for name, field_type in field_types.items():
            if name not in existing:
                if not layer.addAttribute(QgsField(name, field_type)):
                    raise RuntimeError(f"Could not add field: {name}")

        layer.updateFields()

        # Find the requested photograph
        features = [
            f for f in layer.getFeatures()
            if str(f["cty_year_id"]) == str(cty_year_id)
        ]

        if len(features) != 1:
            raise ValueError(
                f"Expected one photo for {cty_year_id}, found {len(features)}"
            )

        feature = features[0]

        # Update its metrics
        for name, value in metrics.items():
            if not layer.changeAttributeValue(
                feature.id(),
                layer.fields().indexFromName(name),
                value,
            ):
                raise RuntimeError(f"Could not update field: {name}")

        if not layer.commitChanges():
            raise RuntimeError(
                f"Could not save tracker: {layer.commitErrors()}"
            )

    except Exception:
        if layer.isEditable():
            layer.rollBack()
        raise

    print(f"Updated tracker metrics for photo {cty_year_id}")

# ---------
# wrapper functions
# ---------
def process_one_photo(
    photo,
    jpeg_path,
    output_path,
    matcher,
    fetcher,
    generator,
    georeferencer,
    cfg,
):
    """Georeference one prepared historical photograph.

    Returns a dictionary containing processing metrics.
    Does not update the tracker.
    """

    photo_id = photo["cty_year_id"]

    print(f"\nProcessing: {photo_id}")

    # 1. Load historical photograph.
    image_src = load_photo_image(jpeg_path)

    print(f"Historical image: {image_src.shape}")

    # 2. Retrieve reference imagery.
    image_ref, ref_extent = get_reference_image(
        photo,
        fetcher,
        source_name=cfg["matching"]["reference_source"],
        target_size=cfg["matching"]["reference_size"],
    )

    print(f"Reference image: {image_ref.shape}")
    print(f"Reference extent: {ref_extent.toString()}")

    # 3. Match historical and reference imagery.
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
    print(
        "Homography found:",
        match_result.transform_matrix is not None,
    )

    # 4. Filter matches.
    filtered_result = matcher.filter_matches(
        match_result,
        confidence_threshold=cfg["matching"]["confidence_threshold"],
    )

    print("Filtered matches:", filtered_result.num_matches())

    # 5. Generate GCPs.
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
            f"Insufficient GCPs for {photo_id}: {len(gcps)}"
        )

    print("First GCP:", gcps[0])

    # 6. Georeference photograph.
    output_path.parent.mkdir(parents=True, exist_ok=True)

    success, message = georeferencer.georeference_image(
        source_image_path=jpeg_path,
        gcps=gcps,
        output_path=output_path,
        target_crs=QgsCoordinateReferenceSystem(
            cfg["georeferencing"]["target_crs"]
        ),
        transform_type=cfg["georeferencing"]["transform"],
        resampling=cfg["georeferencing"]["resampling"],
        compression=cfg["georeferencing"]["compression"],
    )

    if not success:
        raise RuntimeError(
            f"Georeferencing failed for {photo_id}: {message}"
        )

    print("Success:", success)
    print(message)

    # 7. Return processing metrics.
    return {
        "match_count": match_result.num_matches(),
        "inlier_count": filtered_result.num_matches(),
        "confidence": match_result.mean_confidence(),
        "geometric_score": match_result.geometric_score,
        "distribution_quality": match_result.distribution_quality,
        "match_seconds": match_result.processing_time,
        "gcp_count": len(gcps),
    }