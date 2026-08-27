"""
Módulo para análisis espacial, generación de buffers e intersecciones.
"""
import geopandas as gpd
from shapely.geometry import base
from typing import Tuple


# Número máximo de vértices del buffer disuelto antes de simplificar.
# Polígonos con más vértices ralentizan enormemente las pruebas de intersección.
_MAX_BUFFER_COORDS = 2000


def create_buffer_layer(gdf_ref: gpd.GeoDataFrame, buffer_distance_m: float) -> Tuple[base.BaseGeometry, gpd.GeoDataFrame]:
    """
    Genera el buffer métrico sobre la capa de referencia.
    Simplifica automáticamente geometrías complejas de buffer para acelerar
    la prueba de intersección cuando se usan polígonos de referencia.

    Retorna:
        - Geometría disuelta única simplificada (Polygon/MultiPolygon) para prueba binaria rápida.
        - GeoDataFrame con la geometría de buffer para visualización y exportación.
    """
    if gdf_ref is None or len(gdf_ref) == 0:
        raise ValueError("El GeoDataFrame de referencia está vacío.")

    if buffer_distance_m < 0:
        raise ValueError("La distancia de buffer debe ser mayor o igual a 0 metros.")

    # 1. Simplificar las geometrías de referencia antes de bufferizar
    #    (reduce vértices de polígonos complejos sin cambiar el shape significativamente)
    try:
        # Tolerancia de simplificación: 0.5m — imperceptible en análisis métrico
        ref_union = gdf_ref.geometry.simplify(0.5, preserve_topology=True).unary_union
    except Exception:
        ref_union = gdf_ref.geometry.unary_union

    # 2. Aplicar buffer con resolución de cuadratura reducida para polígonos complejos
    #    resolution=8 (defecto=16) reduce vértices del arco de buffer a la mitad
    dissolved_geom = ref_union.buffer(buffer_distance_m, resolution=8)

    # 3. Simplificar el resultado del buffer si sigue siendo muy complejo
    try:
        num_coords = len(dissolved_geom.exterior.coords) if hasattr(dissolved_geom, 'exterior') else 0
        if num_coords > _MAX_BUFFER_COORDS:
            # Tolerancia adaptativa: 10% de la distancia de buffer
            tol = max(0.5, buffer_distance_m * 0.05)
            dissolved_geom_simple = dissolved_geom.simplify(tol, preserve_topology=True)
            if not dissolved_geom_simple.is_empty and dissolved_geom_simple.is_valid:
                dissolved_geom = dissolved_geom_simple
    except Exception:
        pass

    # 4. GeoDataFrame con la entidad de buffer unificado disuelto (para visualización)
    gdf_buffer = gpd.GeoDataFrame(
        [{"id_buffer": 1, "distancia_buffer_m": buffer_distance_m, "geometry": dissolved_geom}],
        crs=gdf_ref.crs
    )

    return dissolved_geom, gdf_buffer
