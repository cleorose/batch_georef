from pathlib import Path
import requests
from PIL import Image
import math

# download a photo
def download_photo(url, output_path, timeout=60):
    """Download a JPEG, skipping existing valid files."""

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if output_path.exists():
        with Image.open(output_path) as img:
            img.verify()
        return output_path

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

    values = (width_px, dpi_x, scale)

    if not all(
        isinstance(v, (int, float)) and
        math.isfinite(v) and v > 0
        for v in values
    ):
        raise ValueError(
            "Width, DPI, and scale must be positive numbers."
        )

    return (width_px / dpi_x) * 0.0254 * scale