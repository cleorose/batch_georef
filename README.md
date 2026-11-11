

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