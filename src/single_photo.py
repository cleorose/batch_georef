from pathlib import Path

import geopandas as gpd
import numpy as np
from PIL import Image

from qgis.core import QgsRectangle, QgsCoordinateReferenceSystem
from qgis.core import QgsVectorLayer, QgsField
from qgis.PyQt.QtCore import QVariant


def select_photo(tracker_path, source_id, layer="photos"):
    """Select one prepared photo from the tracker."""

    tracker = gpd.read_file(tracker_path, layer=layer)

    matches = tracker.loc[
        tracker["source_id"].astype(str) == str(source_id)
    ]

    if len(matches) != 1:
        raise ValueError(
            f"Expected one photo with source_id={source_id}, "
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

def update_match_metrics(tracker_path, source_id, metrics):
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
            if str(f["source_id"]) == str(source_id)
        ]

        if len(features) != 1:
            raise ValueError(
                f"Expected one photo for {source_id}, found {len(features)}"
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

    print(f"Updated tracker metrics for photo {source_id}")