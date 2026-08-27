"""
Módulo para análisis espacial, generación de buffers e intersecciones.
"""
import geopandas as gpd
from shapely.geometry import base
from typing import Tuple

def create_buffer_layer(gdf_ref: gpd.GeoDataFrame, buffer_distance_m: float) -> Tuple[base.BaseGeometry, gpd.GeoDataFrame]:
    """
    Genera el buffer métrico sobre la capa de referencia.
    
    Retorna:
        - Geometría disuelta única (Polygon/MultiPolygon) para prueba binaria rápida de intersección.
        - GeoDataFrame con las geometrías de buffer individuales para visualización y exportación.
    """
    if gdf_ref is None or len(gdf_ref) == 0:
        raise ValueError("El GeoDataFrame de referencia está vacío.")
        
    if buffer_distance_m < 0:
        raise ValueError("La distancia de buffer debe ser mayor o igual a 0 metros.")
        
    # Buffer disuelto/unificado único (merge de todas las entidades de referencia)
    dissolved_geom = gdf_ref.geometry.unary_union.buffer(buffer_distance_m)
    
    # GeoDataFrame con la entidad de buffer unificado disuelto
    gdf_buffer = gpd.GeoDataFrame(
        [{"id_buffer": 1, "distancia_buffer_m": buffer_distance_m, "geometry": dissolved_geom}],
        crs=gdf_ref.crs
    )
    
    return dissolved_geom, gdf_buffer
