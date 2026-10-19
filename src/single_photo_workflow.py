"""Prepare one historical air photo for Magic Georeferencer.

GeoPandas reads/selects records; requests downloads JPGs; Pillow reads dimensions.
SQLite is used ONLY to update one existing GeoPackage record.

The worldfile_params field must already contain JSON with A, D, B, E, C, F.
The world file's coordinate system must be verified separately (expected EPSG:3857).
No ML matching or GeoTIFF writing is performed here.
"""

import json
import math
import sqlite3
from pathlib import Path
from urllib.parse import urlsplit

import geopandas as gpd
import requests
from PIL import Image

# Change these to match your project and actual GeoPackage schema.
GPKG_PATH = Path("data/historic_airphoto_index/main_airphoto_index.gpkg")
LAYER_NAME = "photos"
ID_COLUMN = "filename"
URL_COLUMN = "url"
WORLD_FILE_COLUMN = "worldfile_params"
INPUT_DIR = Path("data/input_images")
OUTPUT_DIR = Path("outputs/georeferenced")


def load_photo(gpkg_path, layer_name, filename, id_column=ID_COLUMN):
    """Read one matching photo as a pandas Series using GeoPandas."""
    gdf = gpd.read_file(gpkg_path, layer=layer_name)
    matches = gdf.loc[gdf[id_column] == filename]
    if len(matches) != 1:
        raise ValueError(f"Expected exactly one photo for {filename!r}; found {len(matches)}")
    return matches.iloc[0]


def local_paths(filename, input_dir, output_dir):
    """Construct local JPG and output GeoTIFF paths from the unique filename."""
    if not isinstance(filename, str) or not filename or Path(filename).name != filename or "\\" in filename or filename in {".", ".."}:
        raise ValueError(f"Invalid filename: {filename!r}")
    input_dir = Path(input_dir)
    output_dir = Path(output_dir)
    input_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)
    return input_dir / f"{filename}.jpg", output_dir / f"{filename}.tif"


def download_jpg(url, destination, timeout=30):
    """Reuse a valid local JPG; otherwise download it safely."""
    destination = Path(destination)
    if destination.is_file():
        try:
            with Image.open(destination) as image:
                image.verify()
            return destination
        except (OSError, ValueError):
            pass  # Existing file is corrupt; download again.

    if not isinstance(url, str) or urlsplit(url).scheme not in {"http", "https"}:
        raise ValueError(f"Expected an HTTP(S) JPG URL; got {url!r}")

    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(destination.name + ".part")
    try:
        with requests.get(url, stream=True, timeout=timeout) as response:
            response.raise_for_status()
            with temporary.open("wb") as file:
                for chunk in response.iter_content(chunk_size=1024 * 1024):
                    if chunk:
                        file.write(chunk)
        with Image.open(temporary) as image:
            image.verify()
        temporary.replace(destination)
    finally:
        temporary.unlink(missing_ok=True)
    return destination


def image_dimensions(image_path):
    """Return (width, height) of the JPG in pixels."""
    with Image.open(image_path) as image:
        return image.size


def parse_worldfile(stored_json):
    """Convert the existing GeoPackage JSON string to affine parameters."""
    if not isinstance(stored_json, str) or not stored_json.strip():
        raise ValueError("World-file JSON is missing")
    parameters = json.loads(stored_json)
    names = ("A", "D", "B", "E", "C", "F")
    if not isinstance(parameters, dict) or any(name not in parameters for name in names):
        raise ValueError("World-file JSON must contain A, D, B, E, C, F")
    result = {name: float(parameters[name]) for name in names}