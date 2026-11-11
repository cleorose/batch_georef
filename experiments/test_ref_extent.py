import geopandas as gpd

from qgis.core import (
    QgsRectangle,
    QgsGeometry,
    QgsVectorLayer,
    QgsFeature,
    QgsField,
    QgsProject,
)
from qgis.PyQt.QtCore import QVariant

# Configuration
tracker_path = r"C:\Users\eu01251115\LocalProjects\batch_georef\data\historic_airphoto_index\subsets\subset_20000_carver_37_38_40_51_57_63_tracker.gpkg"

n_photos = 5
random_seed = 42

# Read tracker
tracker = gpd.read_file(tracker_path, layer="photos")

# Select successfully prepared photos
ready = tracker.loc[
    tracker["wm_width"].notna()
    & tracker["wm_height"].notna()
    & tracker["error"].isna()
    & tracker.geometry.notna()
]

# Random sample
sample = ready.sample(
    n=min(n_photos, len(ready)),
    random_state=random_seed,
)

# Create temporary polygon layer
layer = QgsVectorLayer(
    "Polygon?crs=EPSG:3857",
    "Test Reference Extents",
    "memory",
)

provider = layer.dataProvider()

provider.addAttributes([
    QgsField("source_id", QVariant.String),
    QgsField("url", QVariant.String),
])

layer.updateFields()

# Create one extent polygon per photo
features = []

for _, photo in sample.iterrows():

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

    feature = QgsFeature(layer.fields())
    feature.setGeometry(QgsGeometry.fromRect(extent))

    feature.setAttributes([
        str(photo["source_id"]),
        str(photo["url"]),
    ])

    features.append(feature)

    # Print information for browser inspection
    print(f"\nPhoto: {photo['source_id']}")
    print(f"URL: {photo['url']}")
    print(f"Extent: {extent.toString()}")
    print(f"Width: {extent.width():.1f} m")
    print(f"Height: {extent.height():.1f} m")

# Add features and display in QGIS
provider.addFeatures(features)
layer.updateExtents()

QgsProject.instance().addMapLayer(layer)

# Zoom to all selected photo extents
iface.mapCanvas().setExtent(layer.extent())
iface.mapCanvas().refresh()

print(f"\nCreated {len(features)} reference extents.")