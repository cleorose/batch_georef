from qgis.core import Qgis, QgsApplication, QgsProject

https://docs.qgis.org/3.44/en/docs/pyqgis_developer_cookbook/index.html?utm_source=chatgpt.comprint("QGIS version:", Qgis.QGIS_VERSION)
print("QGIS install path:", QgsApplication.prefixPath())
print("Active project layers:", [layer.name() for layer in QgsProject.instance().mapLayers().values()])