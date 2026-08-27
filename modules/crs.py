"""
Módulo para gestión, detección y reproyección de Sistemas de Referencia de Coordenadas (CRS).
"""
import pyproj
import geopandas as gpd
from typing import Tuple, Dict, Any, Optional

def get_crs_info(gdf: gpd.GeoDataFrame) -> Dict[str, Any]:
    """Obtiene información resumida del CRS de un GeoDataFrame."""
    if gdf.crs is None:
        return {
            "crs_str": "Sin CRS definido",
            "epsg": None,
            "is_geographic": True,
            "is_projected": False,
            "unit_name": "desconocido"
        }
    
    crs = gdf.crs
    epsg = crs.to_epsg()
    is_geo = crs.is_geographic
    
    # Determinar unidades del CRS
    try:
        axis_info = crs.axis_info
        unit_name = axis_info[0].unit_name if axis_info else "desconocido"
    except Exception:
        unit_name = "grado" if is_geo else "metro"
        
    return {
        "crs_str": crs.name or str(crs),
        "epsg": epsg,
        "is_geographic": is_geo,
        "is_projected": crs.is_projected,
        "unit_name": unit_name
    }

def suggest_utm_epsg(gdf: gpd.GeoDataFrame) -> Tuple[int, str]:
    """
    Sugiére un código EPSG UTM en metros basado en el centroide del Bounding Box.
    Si el CRS ya es proyectado métrico, sugiere mantener su EPSG.
    """
    crs_info = get_crs_info(gdf)
    
    # Si ya está en un CRS proyectado métrico, lo mantiene
    if crs_info["is_projected"] and crs_info["epsg"] is not None:
        return crs_info["epsg"], f"CRS proyectado existente (EPSG:{crs_info['epsg']})"
    
    # Convertir temporalmente a WGS84 (EPSG:4326) para calcular lon/lat si no lo está
    if gdf.crs is None:
        # Asumir WGS84 por defecto si no tiene CRS
        gdf_wgs84 = gdf.set_crs("EPSG:4326")
    elif not crs_info["is_geographic"]:
        gdf_wgs84 = gdf.to_crs("EPSG:4326")
    else:
        gdf_wgs84 = gdf
        
    minx, miny, maxx, maxy = gdf_wgs84.total_bounds
    lon_center = (minx + maxx) / 2.0
    lat_center = (miny + maxy) / 2.0
    
    # Cálculo estándar de zona UTM
    utm_zone = int((lon_center + 180) / 6) + 1
    
    if lat_center >= 0:
        epsg_code = 32600 + utm_zone
        hemisphere = "Norte"
    else:
        epsg_code = 32700 + utm_zone
        hemisphere = "Sur"
        
    description = f"UTM Zona {utm_zone} {hemisphere} (WGS84) - EPSG:{epsg_code}"
    return epsg_code, description

def reproject_gdf(gdf: gpd.GeoDataFrame, target_crs: Any) -> gpd.GeoDataFrame:
    """Reproyecta un GeoDataFrame al CRS objetivo de forma segura."""
    if gdf is None or len(gdf) == 0:
        return gdf
        
    if gdf.crs is None:
        # Si no tiene CRS, asignar por defecto EPSG:4326 antes de reproyectar
        gdf = gdf.set_crs("EPSG:4326")
        
    if gdf.crs.equals(target_crs):
        return gdf
        
    return gdf.to_crs(target_crs)
