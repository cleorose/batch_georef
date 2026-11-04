import geopandas as gpd
import sys
from pathlib import Path
import numpy as np
import rasterio
from rasterio.transform import from_bounds
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