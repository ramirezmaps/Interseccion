import geopandas as gpd
from shapely.geometry import Point, LineString, Polygon
import pandas as pd

# Create mixed geometries
gdf = gpd.GeoDataFrame({
    'id': [1, 2, 3],
    'geometry': [
        Point(0, 0),
        LineString([(0, 0), (1, 1)]),
        Polygon([(0, 0), (1, 0), (1, 1), (0, 1), (0, 0)])
    ]
}, crs="EPSG:4326")

try:
    gdf.to_file("test_mixed.gpkg", driver="GPKG", layer="mixed")
    print("Success without explicit engine/type")
except Exception as e:
    print("Error:", e)
