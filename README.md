# GIS Spatial Intersection & Proximity Analyzer (Streamlit)

Aplicación GIS profesional en Python y Streamlit diseñada para realizar análisis espacial batch de intersección con buffer y cálculo de distancias mínimas reales al elemento de referencia más cercano sobre estructuras de carpetas con múltiples archivos Shapefile (.shp).

---

## 🏛️ Arquitectura del Sistema

El proyecto sigue una arquitectura modular y desacoplada:

```text
gis_intersection_app/
│
├── app.py                       # Interfaz Streamlit principal (UI, tabs, session state)
│
├── modules/
│   ├── __init__.py
│   ├── io.py                    # Carga de ZIPs, escaneo recursivo (.rglob) y exportaciones (Excel, CSV, GPKG)
│   ├── crs.py                   # Detección de CRS, deducción de Zona UTM métrica y reproyección
│   ├── geometry.py              # Diagnóstico y reparación de geometrías (make_valid)
│   ├── spatial_analysis.py      # Generación de buffer e intersecciones espaciales
│   ├── distance.py              # Optimización STRtree, distancias mínimas y conectores LineString
│   ├── reporting.py             # DataFrames resumidos, tablas KPI y binned distance ranges
│   ├── visualization.py         # Mapa interactivo Folium y gráficos Plotly
│   └── utils.py                 # Manejo de excepciones, formateo y logging
│
├── generate_test_data.py        # Script generador de datos geográficos de prueba
├── requirements.txt             # Dependencias Python
└── README.md                    # Documentación del proyecto
```

---

## 🔧 Fase 4 — Instalación y Ejecución

### 1. Requisitos Previos
* Python 3.11 o superior.
* Entorno virtual recomendado (`venv` o `conda`).

### 2. Crear Entorno Virtual e Instalar Dependencias

En PowerShell o Terminal:

```bash
# Crear entorno virtual
python -m venv venv

# Activar entorno virtual (Windows PowerShell)
.\venv\Scripts\Activate.ps1

# Actualizar pip
python -m pip install --upgrade pip

# Instalar dependencias requeridas
pip install -r requirements.txt
```

### 3. Ejecutar la Aplicación Streamlit

```bash
streamlit run app.py
```

La interfaz se abrirá automáticamente en su navegador web en `http://localhost:8501`.

---

## 🧪 Fase 5 — Guía de Pruebas

Para validar el correcto funcionamiento con un conjunto de datos sintéticos:

1. **Generar los datos de prueba**:
   ```bash
   python generate_test_data.py
   ```
   Esto creará la carpeta `datos_prueba/` que contiene:
   - `referencia_eje.zip`: Shapefile de referencia en formato ZIP.
   - `SUBCARPETA_01/puntos_interes.shp`: 4 puntos (2 dentro del buffer, 2 fuera).
   - `SUBCARPETA_02/caminos.shp`: Líneas de caminera.

2. **Probar en la Aplicación Streamlit**:
   - Suba el archivo `datos_prueba/referencia_eje.zip` en el panel lateral.
   - Copie la ruta absoluta de la carpeta `datos_prueba` en el campo *Carpeta de Análisis*.
   - Ingrese `150` metros de buffer.
   - Haga clic en **`🚀 EJECUTAR ANÁLISIS`**.

3. **Resultados Esperados a Verificar**:
   - **CRS de Análisis**: Se detectará automáticamente **EPSG:32719** (UTM Zona 19 Sur) o la proyección métrica correspondiente.
   - **Intersección**: Los puntos 101 y 102 se clasificarán como `INTERSECTA` con distancia 0.0 m.
   - **No Intersección y Proximidad**: Los puntos 103 y 104 se clasificarán como `NO INTERSECTA` indicando la distancia exacta en metros al eje de referencia más cercano y su conector.
   - **Exportación**: Podrá descargar el reporte multi-hoja en Excel, los CSVs y el GeoPackage `.gpkg` listo para abrir en QGIS.

---

## ⚡ Fase 6 — Optimización y Escalabilidad para Grandes Volúmenes de Datos

Para escalar este sistema a cientos de miles de entidades o terabytes de Shapefiles:

1. **Motor de Lectura de Almacenamiento**:
   Se utiliza `pyogrio` como motor preferente en `geopandas.read_file()`, el cual aprovecha C/GDAL de forma nativa proporcionando lecturas de 4x a 10x más rápidas que Fiona.

2. **Indexación Espacial `STRtree`**:
   Se utiliza `shapely.strtree.STRtree` nativo en C (libgeos). En lugar de comparar $N \times M$ combinaciones, la complejidad se reduce a $O(N \log M)$, reduciendo el tiempo de procesamiento de horas a segundos.

3. **Procesamiento Multiproceso Parcial (Parallel Batch Processing)**:
   Si la cantidad de Shapefiles en subcarpetas supera los 500 archivos, el bucle `for shp_file in scanned_shps` en `spatial_analysis.py` puede paralelizarse utilizando `concurrent.futures.ProcessPoolExecutor()` asignando un proceso por subcarpeta.

4. **Migración a DuckDB / Spatial Extension o Parquet**:
   Para conjuntos masivos de datos que superan la memoria RAM disponible, se recomienda convertir los Shapefiles a formato **GeoParquet** y utilizar **DuckDB con la extensión espacial (`ST_Buffer`, `ST_Intersects`, `ST_Distance`)**, ejecutando consultas en streaming directamente sobre disco.
