# Batch Georeferencing Historic Airphotos

This repository integrates modules from the Magic Georeferencer QGIS plugin with additional code for preparing, processing, and tracking batches of historic airphotos stored in the Borchert Map Library's MHAPO collection. 

## Project structure
Notebooks for preparing tracker tables, caculating photo extents, and staging for batch processing are located in the notebooks folder. 
In the scripts folder, there are two python scripts meant to be run from within the QGIS editor console. One georeferences just a single photo (designed for testing), while the other georeferences a list of photos. 



## Tracker fields
Field	    Meaning
match_count	Number of feature correspondences the matching model initially identified between the historical photo and reference imagery.
inlier_count	In your current code, the number of matches remaining after applying the confidence threshold of 0.20.
geometric_score	A measure reported by the matcher of how geometrically consistent the matches are.
distribution_quality	A measure of how well the matches are distributed spatially across the imagery.
match_seconds	Time spent performing the matching operation.
gcp_count	Number of ground control points generated from the filtered matches.

In QGIS you can reload an edited module:

import importlib
import src.single_photo

importlib.reload(src.single_photo)



# Pseudocode — the interface we're building toward

cfg = load_config()

matcher = initialize_matcher()
fetcher = TileFetcher()
generator = GCPGenerator()
georeferencer = Georeferencer(iface=iface)

for photo in photos:
    process_one_photo(
        photo=photo,
        matcher=matcher,
        fetcher=fetcher,
        generator=generator,
        georeferencer=georeferencer,
        cfg=cfg,
    )