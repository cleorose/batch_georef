

In QGIS you can reload an edited module:

import importlib
import src.single_photo

importlib.reload(src.single_photo)