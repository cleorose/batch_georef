from pathlib import Path
import requests
from PIL import Image
import math
from numbers import Real
import sqlite3

# download a photo
def download_photo(url, output_path, timeout=60):
    """Download a JPEG, skipping existing valid files."""

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if output_path.exists():
        try:
            with Image.open(output_path) as img:
                if img.format != "JPEG":
                    raise ValueError("Not a JPEG")
                img.verify()
            return output_path
        except (OSError, ValueError):
            print(f"Invalid JPEG, redownloading: {output_path.name}")

    temp_path = output_path.with_suffix(".part")

    try:
        with requests.get(url, stream=True, timeout=timeout) as response:
            response.raise_for_status()

            with open(temp_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=1024 * 1024):
                    if chunk:
                        f.write(chunk)

        with Image.open(temp_path) as img:
            if img.format != "JPEG":
                raise ValueError(f"Downloaded file is not a JPEG: {url}")
            img.verify()

        temp_path.replace(output_path)

    finally:
        temp_path.unlink(missing_ok=True)

    return output_path


def get_image_metadata(image_path):
    """Read image width and horizontal DPI."""

    with Image.open(image_path) as img:
        width_px = img.width
        dpi = img.info.get("dpi")

    dpi_x = dpi[0] if dpi else None

    return {
        "width_px": width_px,
        "dpi_x": dpi_x,
    }

def calculate_horizontal_extent(width_px, dpi_x, scale):
    """Calculate approximate ground width in meters."""

    try:
        width_px = float(width_px)
        dpi_x = float(dpi_x)
        scale = float(scale)
    except (TypeError, ValueError):
        raise ValueError(
            "Width, DPI, and scale must be numeric."
        )

    if not all(
        math.isfinite(v) and v > 0
        for v in (width_px, dpi_x, scale)
    ):
        raise ValueError(
            "Width, DPI, and scale must be positive numbers."
        )

    return (width_px / dpi_x) * 0.0254 * scale

def ground_to_mercator_extent(ground_extent_m, latitude):
    """Approximate Web Mercator extent from ground distance."""
    return ground_extent_m / math.cos(math.radians(latitude))

def update_tracker(tracker_path, results_df, layer="photos"):
    """Update preparation results in a tracker GeoPackage."""

    tracker = gpd.read_file(tracker_path, layer=layer)

    successful = results_df.loc[
        results_df["error"].isna()
    ].copy()

    if successful.empty:
        return 0

    if not tracker["source_id"].is_unique:
        raise ValueError("Tracker source_id values must be unique")

    if not successful["source_id"].is_unique:
        raise ValueError("Result source_id values must be unique")