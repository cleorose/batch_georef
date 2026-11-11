from pathlib import Path
import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]

def load_config(config_path=None):
    """Load project settings and construct batch paths."""

    if config_path is None:
        config_path = PROJECT_ROOT / "config.yml"

    with open(config_path, encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    # Resolve data directory
    data_dir = Path(cfg["data_dir"]).expanduser()

    if not data_dir.is_absolute():
        data_dir = PROJECT_ROOT / data_dir

    data_dir = data_dir.resolve()

    batch_name = cfg["batch_name"]

    # Generate paths
    cfg["paths"] = {
        "data_dir": data_dir,
        "tracker": data_dir / "batches" / f"{batch_name}_tracker.gpkg",
        "downloads": data_dir / "downloads",
        "outputs": data_dir / "georeferenced",
    }

    cfg["batch_name"] = batch_name

    return cfg

def photo_paths(photo, cfg):
    """Construct file paths using each photo's own metadata."""

    photo_id = str(photo["cty_year_id"])

    county = str(photo["county"]).strip().lower().replace(" ", "_")
    year = str(int(photo["year"]))

    folder = f"{county}_{year}"

    return {
        "jpeg": (
            cfg["paths"]["downloads"]
            / f"{folder}_originals"
            / f"{photo_id}_original.jpg"
        ),
        "geotiff": (
            cfg["paths"]["outputs"]
            / f"{folder}_georef"
            / f"{photo_id}_georef.tif"
        ),
    }
