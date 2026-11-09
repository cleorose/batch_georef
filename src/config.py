
from pathlib import Path
import yaml


def load_config(config_path=None):
    """Load project settings and construct batch paths."""

    project_root = Path(__file__).resolve().parents[1]

    if config_path is None:
        config_path = project_root / "config.yml"

    with open(config_path, encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    # Resolve data directory
    data_dir = Path(cfg["data_dir"]).expanduser()

    if not data_dir.is_absolute():
        data_dir = project_root / data_dir

    # Generate batch name
    county = cfg["county"].lower().replace(" ", "_")
    years = "_".join(str(y) for y in cfg["years"])
    scale = cfg["scale"]

    batch_name = f"{county}_{years}_{scale}"

    # Generate paths
    cfg["paths"] = {
        "data_dir": data_dir,
        "tracker": (
            data_dir
            / "historic_airphoto_index"
            / "subsets"
            / f"{batch_name}_tracker.gpkg"
        ),
        "downloads": data_dir / "downloads" / batch_name,
        "outputs": data_dir / "georeferenced" / batch_name,
    }

    cfg["batch_name"] = batch_name

    return cfg
