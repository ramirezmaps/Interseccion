"""
Módulo para cálculo de distancias mínimas exactas y generación de geometrías de conexión.
"""
import geopandas as gpd
from shapely.strtree import STRtree
from shapely.ops import nearest_points
from shapely.geometry import LineString, base
from typing import List, Dict, Any, Tuple, Optional
import pandas as pd

def build_spatial_index(gdf_ref: gpd.GeoDataFrame) -> STRtree:
    """Construye un índice espacial STRtree sobre las geometrías de la capa de referencia."""
    # Filtrar geometrías válidas no nulas
    geoms = [g for g in gdf_ref.geometry if g is not None and not g.is_empty]
    return STRtree(geoms)

def analyze_proximity_batch(
    gdf_layer: gpd.GeoDataFrame,
    gdf_ref: gpd.GeoDataFrame,
    strtree_ref: STRtree,
    buffer_dissolved: base.BaseGeometry,
    file_info: Dict[str, str],
    crs_analysis: Any
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Analiza entidad por entidad en un GeoDataFrame objetivo.
    
    Retorna:
        - Lista de diccionarios de resultados tabulares por entidad.
        - Lista de registros geográficos para conectores LineString (elementos NO INTERSECTAN).
    """
    results = []
    lines_records = []
    
    ref_geoms_list = list(gdf_ref.geometry)
    
    for idx, row in gdf_layer.iterrows():
        geom = row.geometry
        if geom is None or geom.is_empty:
            continue
            
        # Determinar ID de entidad
        id_entidad = row.get("FID", row.get("OBJECTID", row.get("id", idx)))
        tipo_geom = geom.geom_type
        
        # 1. Evaluar si intersecta el buffer disuelto
        if buffer_dissolved.intersects(geom):
            estado = "INTERSECTA"
            distancia_m = 0.0
            
            # Buscar el elemento de referencia más cercano de todos modos para reporte informativo
            nearest_idx = strtree_ref.nearest(geom)
            ref_row = gdf_ref.iloc[nearest_idx]
            id_ref_cercana = ref_row.get("FID", ref_row.get("OBJECTID", ref_row.get("id", nearest_idx)))
            
            record = {
                "archivo": file_info["archivo"],
                "subcarpeta": file_info["subcarpeta"],
                "ruta_relativa": file_info["ruta_relativa"],
                "id_entidad": id_entidad,
                "tipo_geometria": tipo_geom,
                "estado": estado,
                "id_referencia_mas_cercana": id_ref_cercana,
                "distancia_m": distancia_m,
                "geometry": geom,
                "linea_conexion": None
            }
        else:
            estado = "NO INTERSECTA"
            
            # Buscar el elemento de referencia geométricamente más cercano
            nearest_idx = strtree_ref.nearest(geom)
            ref_row = gdf_ref.iloc[nearest_idx]
            ref_geom = ref_geoms_list[nearest_idx]
            id_ref_cercana = ref_row.get("FID", ref_row.get("OBJECTID", ref_row.get("id", nearest_idx)))
            
            # Distancia mínima entre geometrías reales
            distancia_m = float(geom.distance(ref_geom))
            
            # Generar conector LineString entre los puntos más cercanos
            p1, p2 = nearest_points(geom, ref_geom)
            linea_conn = LineString([p1, p2])
            
            record = {
                "archivo": file_info["archivo"],
                "subcarpeta": file_info["subcarpeta"],
                "ruta_relativa": file_info["ruta_relativa"],
                "id_entidad": id_entidad,
                "tipo_geometria": tipo_geom,
                "estado": estado,
                "id_referencia_mas_cercana": id_ref_cercana,
                "distancia_m": round(distancia_m, 2),
                "geometry": geom,
                "linea_conexion": linea_conn
            }
            
            lines_records.append({
                "archivo": file_info["archivo"],
                "id_entidad": id_entidad,
                "id_referencia_mas_cercana": id_ref_cercana,
                "distancia_m": round(distancia_m, 2),
                "geometry": linea_conn
            })
            
        results.append(record)
        
    return results, lines_records
