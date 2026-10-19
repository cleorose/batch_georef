from qgis.core import Qgis, QgsApplication, QgsProject

print("QGIS version:", Qgis.QGIS_VERSION)
print("QGIS install path:", QgsApplication.prefixPath())
print("Active project layers:", [layer.name() for layer in QgsProject.instance().mapLayers().values()])