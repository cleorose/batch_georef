import geopandas as gpd
import sys
from pathlib import Path
import numpy as np
from osgeo import gdal, osr
from qgis.core import QgsRasterLayer, QgsProject

# Project root (contains src/)
PROJECT_ROOT = Path(
    r"C:\Users\eu01251115\LocalProjects\batch_georef"
)

# Magic Georeferencer modules
MG_MODULES = Path(
    r"C:\Users\eu01251115\LocalProjects\georefio\magic_georeferencer\core"
)

# Make both importable
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(MG_MODULES))

# Imports
from tile_fetcher import TileFetcher
from src.ref_imagery import get_reference_image


tracker_path = r"C:\Users\eu01251115\LocalProjects\batch_georef\data\historic_airphoto_index\subsets\subset_20000_carver_37_38_40_51_57_63_tracker.gpkg"

# Read tracker
tracker = gpd.read_file(tracker_path, layer="photos")

# Select prepared photographs
ready = tracker.loc[
    tracker["wm_width"].notna()
    & tracker["wm_height"].notna()
    & tracker["error"].isna()
]

# Select one photo
photo = ready.iloc[0]

# Initialize Magic Georeferencer tile fetcher
fetcher = TileFetcher()

# Fetch reference imagery
image, actual_extent = get_reference_image(
    photo,
    fetcher=fetcher,
    source_name="esri_world_imagery",
    target_size=832,
)

print("Photo:", photo["source_id"])
print("Image shape:", image.shape)
print("Actual extent:", actual_extent.toString())

# -------------------------------

# Output location
output_path = (
    PROJECT_ROOT / "data" / "reference"
    / f"{photo['source_id']}_reference.tif"
)

output_path.parent.mkdir(parents=True, exist_ok=True)

height, width, bands = image.shape

# Create GeoTIFF
driver = gdal.GetDriverByName("GTiff")

dataset = driver.Create(
    str(output_path),
    width,
    height,
    3,
    gdal.GDT_Byte,
    options=["COMPRESS=DEFLATE", "PHOTOMETRIC=RGB"],
)

if dataset is None:
    raise RuntimeError("Failed to create GeoTIFF")

# Set geographic extent
pixel_width = actual_extent.width() / width
pixel_height = actual_extent.height() / height

dataset.SetGeoTransform([
    actual_extent.xMinimum(),
    pixel_width,
    0,
    actual_extent.yMaximum(),
    0,
    -pixel_height,
])

# Set CRS
srs = osr.SpatialReference()
srs.ImportFromEPSG(3857)
dataset.SetProjection(srs.ExportToWkt())

# Write RGB bands
for i in range(3):
    dataset.GetRasterBand(i + 1).WriteArray(image[:, :, i])

# Close file
dataset = None

# Load into QGIS
raster_layer = QgsRasterLayer(
    str(output_path),
    f"Reference {photo['source_id']}",
)

if not raster_layer.isValid():
    raise RuntimeError("Failed to load reference raster")

QgsProject.instance().addMapLayer(raster_layer)

iface.mapCanvas().setExtent(actual_extent)
iface.mapCanvas().refresh()

print(f"Saved reference image: {output_path}")