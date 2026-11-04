
import geopandas as gpd

from qgis.core import (
    QgsRectangle,
    QgsCoordinateReferenceSystem,
    QgsGeometry,
    QgsVectorLayer,
    QgsFeature,
    QgsProject,
)

# Path to your prepared tracker
tracker_path = r"C:\Users\eu01251115\LocalProjects\batch_georef\data\historic_airphoto_index\subsets\subset_20000_carver_37_38_40_51_57_63_tracker.gpkg"

# Read the tracker
tracker = gpd.read_file(tracker_path, layer="photos")

# Select one successfully prepared photograph
ready = tracker.loc[
    tracker["wm_width"].notna()
    & tracker["wm_height"].notna()
    & tracker["error"].isna()
]

photo = ready.iloc[0]

# Center coordinates from the GeoPackage geometry
center_x = photo.geometry.x
center_y = photo.geometry.y

# Calculate the reference image extent
half_width = photo["wm_width"] / 2
half_height = photo["wm_height"] / 2

extent = QgsRectangle(
    center_x - half_width,
    center_y - half_height,
    center_x + half_width,
    center_y + half_height,
)

# Print results
print("Photo:", photo["source_id"])
print("Center:", center_x, center_y)
print("Extent:", extent.toString())
print("Width:", extent.width())
print("Height:", extent.height())

# Create a temporary polygon layer to visualize the extent
layer = QgsVectorLayer(
    "Polygon?crs=EPSG:3857",
    "Test Reference Extent",
    "memory",
)

feature = QgsFeature()
feature.setGeometry(QgsGeometry.fromRect(extent))

layer.dataProvider().addFeatures([feature])
layer.updateExtents()

# Add to QGIS and zoom to the rectangle
QgsProject.instance().addMapLayer(layer)

iface.mapCanvas().setExtent(extent)
iface.mapCanvas().refresh()
