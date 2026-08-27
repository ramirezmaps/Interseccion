"""
Módulo para diagnóstico, limpieza y reparación de geometrías.
"""
import geopandas as gpd
import shapely
from shapely.validation import make_valid
from typing import Tuple, Dict, Any

def clean_and_validate_geometries(gdf: gpd.GeoDataFrame) -> Tuple[gpd.GeoDataFrame, Dict[str, int]]:
    """
    Inspecciona y repara geometrías inválidas, vacías o nulas.
    
    Retorna:
        - GeoDataFrame limpio
        - Diccionario con estadísticas de geometrías: total, validas, reparadas, vacias_eliminadas.
    """
    if gdf is None or len(gdf) == 0:
        return gdf, {"total": 0, "validas": 0, "reparadas": 0, "vacias_eliminadas": 0}
        
    gdf_clean = gdf.copy()
    total_original = len(gdf_clean)
    
    # 1. Eliminar geometrías nulas o NaN
    gdf_clean = gdf_clean[gdf_clean.geometry.notna()].copy()
    
    # 2. Conteo inicial de válidas
    is_valid_initial = gdf_clean.geometry.is_valid
    count_valid_initial = int(is_valid_initial.sum())
    count_invalid = total_original - count_valid_initial
    
    # 3. Reparar geometrías inválidas si existen
    repaired_count = 0
    if count_invalid > 0:
        def repair_geom(geom):
            nonlocal repaired_count
            if geom is None or geom.is_empty:
                return geom
            if not geom.is_valid:
                try:
                    repaired = make_valid(geom)
                    repaired_count += 1
                    return repaired
                except Exception:
                    return geom
            return geom
            
        gdf_clean['geometry'] = gdf_clean['geometry'].apply(repair_geom)
        
    # 4. Eliminar geometrías vacías despuès de reparación
    gdf_clean = gdf_clean[~gdf_clean.geometry.is_empty].copy()
    final_valid_count = len(gdf_clean)
    dropped_empty = total_original - final_valid_count
    
    stats = {
        "total": total_original,
        "validas": final_valid_count,
        "reparadas": repaired_count,
        "vacias_eliminadas": dropped_empty
    }
    
    return gdf_clean, stats
