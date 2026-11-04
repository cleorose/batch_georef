from qgis.core import (
    QgsRectangle,
    QgsCoordinateReferenceSystem,
)

from tile_fetcher import TileFetcher


def get_reference_image(photo, source_name, target_size=832):
    """Fetch reference imagery for a prepared photo."""

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

    fetcher = TileFetcher()

    image, actual_extent = fetcher.render_tiles_with_qgis(
        extent=extent,
        crs=QgsCoordinateReferenceSystem("EPSG:3857"),
        source_name=source_name,
        target_size=target_size,
    )

    return image, actual_extent

photo = ready.iloc[0]

image, actual_extent = get_reference_image(
    photo,
    source_name="YOUR_ESRI_SOURCE_KEY",
    target_size=832,
)

print("Image shape:", image.shape)
print("Actual extent:", actual_extent.toString())