"""
Script generador de datos sintéticos de prueba para el sistema GIS de Intersección y Proximidad.
Crea un archivo ZIP de referencia y una estructura de subcarpetas con Shapefiles.
"""
import os
import zipfile
import shutil
from pathlib import Path
import geopandas as gpd
from shapely.geometry import Point, LineString, Polygon

def create_synthetic_datasets(output_base_dir: str = "datos_prueba"):
    """Genera datos geográficos de prueba en EPSG:4326 y UTM 19S (EPSG:32719)."""
    base_path = Path(output_base_dir)
    if base_path.exists():
        shutil.rmtree(base_path)
    base_path.mkdir(parents=True, exist_ok=True)
    
    print(f"[+] Creando conjunto de datos de prueba en '{base_path.resolve()}'...")
    
    # -------------------------------------------------------------------------
    # 1. CAPA DE REFERENCIA (Línea de Eje / Infraestructura en Santiago de Chile)
    # Coordenadas aproximadas Santiago de Chile WGS84: Lon -70.65, Lat -33.44
    # -------------------------------------------------------------------------
    ref_line_1 = LineString([(-70.660, -33.450), (-70.650, -33.440), (-70.640, -33.430)])
    ref_line_2 = LineString([(-70.640, -33.430), (-70.630, -33.420)])
    
    gdf_ref = gpd.GeoDataFrame(
        [
            {"ID": "REF_001", "Nombre": "Eje Vial Principal Norte", "Tipo": "Avenida", "geometry": ref_line_1},
            {"ID": "REF_002", "Nombre": "Tramo Eje Vial Sur", "Tipo": "Autopista", "geometry": ref_line_2}
        ],
        crs="EPSG:4326"
    )
    
    # Guardar en directorio temporal de referencia y zip
    ref_dir = base_path / "referencia_temp"
    ref_dir.mkdir(exist_ok=True)
    ref_shp = ref_dir / "referencia_eje.shp"
    gdf_ref.to_file(ref_shp)
    
    zip_path = base_path / "referencia_eje.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
        for ext in [".shp", ".shx", ".dbf", ".prj", ".cpg"]:
            f = ref_dir / f"referencia_eje{ext}"
            if f.exists():
                zipf.write(f, arcname=f.name)
                
    shutil.rmtree(ref_dir)
    print(f"[OK] Shapefile de referencia comprimido creado en: {zip_path}")
    
    # -------------------------------------------------------------------------
    # 2. CAPAS PARA ANÁLISIS EN SUBCARPETAS
    # -------------------------------------------------------------------------
    sub1 = base_path / "SUBCARPETA_01"
    sub2 = base_path / "SUBCARPETA_02"
    sub1.mkdir(exist_ok=True)
    sub2.mkdir(exist_ok=True)
    
    # Archivo 1: Puntos de Interés en Subcarpeta 1 (Algunos dentro del buffer ~100m, otros lejos)
    # Distancia ~0.001 grados lon/lat es aprox 100 metros en Chile
    p1 = Point(-70.655, -33.445) # Muy cerca (Intersecta)
    p2 = Point(-70.645, -33.435) # Muy cerca (Intersecta)
    p3 = Point(-70.670, -33.460) # Alejado (~2 km, No Intersecta)
    p4 = Point(-70.610, -33.400) # Alejado (~4 km, No Intersecta)
    
    gdf_puntos = gpd.GeoDataFrame(
        [
            {"ID": 101, "Categoria": "Estación", "Estado_Esperado": "INTERSECTA", "geometry": p1},
            {"ID": 102, "Categoria": "Subestación", "Estado_Esperado": "INTERSECTA", "geometry": p2},
            {"ID": 103, "Categoria": "Torre Remota", "Estado_Esperado": "NO INTERSECTA", "geometry": p3},
            {"ID": 104, "Categoria": "Antena Rural", "Estado_Esperado": "NO INTERSECTA", "geometry": p4}
        ],
        crs="EPSG:4326"
    )
    gdf_puntos.to_file(sub1 / "puntos_interes.shp")
    print(f"[OK] SHP 1 creado: {sub1 / 'puntos_interes.shp'}")
    
    # Archivo 2: Rutas / Caminos en Subcarpeta 2
    camino_1 = LineString([(-70.652, -33.442), (-70.648, -33.438)]) # Intersecta
    camino_2 = LineString([(-70.680, -33.470), (-70.685, -33.475)]) # No Intersecta
    
    gdf_caminos = gpd.GeoDataFrame(
        [
            {"ID": 201, "Tipo_Via": "Secundaria", "geometry": camino_1},
            {"ID": 202, "Tipo_Via": "Camino Vecinal", "geometry": camino_2}
        ],
        crs="EPSG:4326"
    )
    gdf_caminos.to_file(sub2 / "caminos.shp")
    print(f"[OK] SHP 2 creado: {sub2 / 'caminos.shp'}")

    print(f"\n[OK] Datos sinteticos creados correctamente!")
    print(f"[*] Para probar la app:")
    print(f"   1. Use el ZIP: '{zip_path.resolve()}' como Shapefile de referencia.")
    print(f"   2. Ingrese la ruta: '{base_path.resolve()}' como carpeta de analisis.")
    print(f"   3. Defina un buffer de 150 metros.")

if __name__ == "__main__":
    create_synthetic_datasets()
