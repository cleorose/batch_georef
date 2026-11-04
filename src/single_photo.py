from pathlib import Path

import geopandas as gpd
import numpy as np
from PIL import Image

from qgis.core import QgsRectangle, QgsCoordinateReferenceSystem


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


def load_photo_image(photo, download_dir):
    """Load an existing historical JPEG as an RGB NumPy array."""

    image_path = (
        Path(download_dir)
        / f"{photo['cty_year_id']}_original.jpg"
    )

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