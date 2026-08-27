"""
Módulo para operaciones de Entrada/Salida (I/O): Carga de ZIPs/SHP, escaneo de carpetas y exportaciones.
"""
import os
import zipfile
import tempfile
import io
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional
import pandas as pd
import geopandas as gpd

def extract_zip_shapefile(zip_bytes_or_file: Any, target_dir: str) -> str:
    """
    Extrae un archivo ZIP cargado por Streamlit y localiza el archivo .shp principal.
    Valida la existencia de los componentes mínimos (.shp, .dbf, .shx).
    """
    with zipfile.ZipFile(zip_bytes_or_file, 'r') as zip_ref:
        zip_ref.extractall(target_dir)
        
    shp_files = list(Path(target_dir).rglob("*.shp"))
    
    if not shp_files:
        raise FileNotFoundError("El archivo ZIP cargado no contiene ningún archivo de extensión '.shp'.")
        
    primary_shp = shp_files[0]
    shp_dir = primary_shp.parent
    base_name = primary_shp.stem
    
    # Validar archivos secundarios esenciales
    missing_files = []
    for ext in ['.dbf', '.shx']:
        required_file = shp_dir / f"{base_name}{ext}"
        if not required_file.exists():
            # Buscar en caso de insensibilidad a mayúsculas
            matching = list(shp_dir.glob(f"{base_name}*{ext.upper()}"))
            if not matching:
                missing_files.append(ext)
                
    if missing_files:
        raise FileNotFoundError(f"Al Shapefile '{primary_shp.name}' le faltan los archivos componentes obligatorios: {', '.join(missing_files)}")
        
    return str(primary_shp)

def extract_zip_analysis_folder(zip_bytes_or_file: Any, target_dir: str) -> str:
    """
    Extrae un archivo ZIP que contiene la estructura completa de subcarpetas y archivos Shapefile.
    Retorna la ruta al directorio extraído para su escaneo recursivo.
    """
    with zipfile.ZipFile(zip_bytes_or_file, 'r') as zip_ref:
        zip_ref.extractall(target_dir)
    return target_dir

def read_shapefile(shp_path: str) -> gpd.GeoDataFrame:
    """Lee un archivo Shapefile usando GeoPandas (con motor preferente Pyogrio o Fiona)."""
    try:
        return gpd.read_file(shp_path, engine="pyogrio")
    except Exception:
        # Fallback a motor estándar
        return gpd.read_file(shp_path)

def scan_directory_for_shapefiles(root_path: str) -> List[Dict[str, str]]:
    """
    Escanea recursivamente la carpeta raíz en búsqueda de todos los archivos .shp.
    Registra nombre de archivo, subcarpeta, ruta relativa y ruta absoluta.
    """
    root = Path(root_path)
    if not root.exists() or not root.is_dir():
        raise ValueError(f"La ruta especificada '{root_path}' no existe o no es un directorio válido.")
        
    shp_list = []
    for shp_file in root.rglob("*.shp"):
        # Ignorar archivos temporales de QGIS/ArcGIS (ej. que empiecen por ~ o .)
        if shp_file.name.startswith("~") or shp_file.name.startswith("."):
            continue
            
        rel_path = shp_file.relative_to(root)
        subfolder = str(rel_path.parent) if str(rel_path.parent) != "." else "Raíz"
        
        shp_list.append({
            "archivo": shp_file.name,
            "subcarpeta": subfolder,
            "ruta_relativa": str(rel_path),
            "ruta_absoluta": str(shp_file.resolve())
        })
        
    return sorted(shp_list, key=lambda x: x["ruta_relativa"])

def export_to_excel(
    df_summary: pd.DataFrame,
    df_results: pd.DataFrame,
    df_intersected: pd.DataFrame,
    df_non_intersected: pd.DataFrame,
    df_stats: pd.DataFrame,
    df_errors: pd.DataFrame
) -> bytes:
    """Genera un archivo Excel (.xlsx) con múltiples hojas de reporte."""
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        if df_summary is not None and not df_summary.empty:
            df_summary.to_excel(writer, sheet_name="Resumen_Archivos", index=False)
        if df_results is not None and not df_results.empty:
            # Excluir columnas geométricas complejas para Excel
            cols_to_export = [c for c in df_results.columns if c not in ["geometry", "linea_conexion"]]
            df_results[cols_to_export].to_excel(writer, sheet_name="Resultados_Todos", index=False)
        if df_intersected is not None and not df_intersected.empty:
            cols = [c for c in df_intersected.columns if c not in ["geometry", "linea_conexion"]]
            df_intersected[cols].to_excel(writer, sheet_name="Intersectados", index=False)
        if df_non_intersected is not None and not df_non_intersected.empty:
            cols = [c for c in df_non_intersected.columns if c not in ["geometry", "linea_conexion"]]
            df_non_intersected[cols].to_excel(writer, sheet_name="No_Intersectados", index=False)
        if df_stats is not None and not df_stats.empty:
            df_stats.to_excel(writer, sheet_name="Estadisticas_Distancia", index=False)
        if df_errors is not None and not df_errors.empty:
            df_errors.to_excel(writer, sheet_name="Errores", index=False)
            
    return output.getvalue()

def export_to_gpkg(
    gdf_ref: gpd.GeoDataFrame,
    gdf_buffer: gpd.GeoDataFrame,
    gdf_intersected: Optional[gpd.GeoDataFrame],
    gdf_non_intersected: Optional[gpd.GeoDataFrame],
    gdf_lines: Optional[gpd.GeoDataFrame]
) -> bytes:
    """Exporta las capas espaciales resultantes a un único GeoPackage (.gpkg)."""
    with tempfile.NamedTemporaryFile(suffix=".gpkg", delete=False) as tmp_gpkg:
        tmp_path = tmp_gpkg.name
        
    try:
        if gdf_ref is not None and len(gdf_ref) > 0:
            gdf_ref.to_file(tmp_path, layer="referencia", driver="GPKG")
        if gdf_buffer is not None and len(gdf_buffer) > 0:
            gdf_buffer.to_file(tmp_path, layer="buffer", driver="GPKG")
        if gdf_intersected is not None and len(gdf_intersected) > 0:
            # Eliminar columnas con objetos no serializables si existen
            gdf_clean = gdf_intersected.drop(columns=["linea_conexion"], errors="ignore")
            gdf_clean.to_file(tmp_path, layer="intersectados", driver="GPKG")
        if gdf_non_intersected is not None and len(gdf_non_intersected) > 0:
            gdf_clean = gdf_non_intersected.drop(columns=["linea_conexion"], errors="ignore")
            gdf_clean.to_file(tmp_path, layer="no_intersectados", driver="GPKG")
        if gdf_lines is not None and len(gdf_lines) > 0:
            gdf_lines.to_file(tmp_path, layer="lineas_distancia", driver="GPKG")
            
        with open(tmp_path, "rb") as f:
            data = f.read()
        return data
    finally:
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except Exception:
                pass
