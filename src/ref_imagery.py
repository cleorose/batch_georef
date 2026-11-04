from qgis.core import (
    QgsRectangle,
    QgsCoordinateReferenceSystem,
)

# ---------------------
# GET REFERENCE IMAGERY
# ---------------------
def get_reference_image(photo, fetcher, source_name="esri_world_imagery", target_size=832):
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

    image, actual_extent = fetcher.render_tiles_with_qgis(
        extent=extent,
        crs=QgsCoordinateReferenceSystem("EPSG:3857"),
        source_name=source_name,
        target_size=target_size,
    )

    return image, actual_extent