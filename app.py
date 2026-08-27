"""
Aplicación GIS Profesional en Streamlit para Análisis Espacial de Intersección y Proximidad.
"""
import os
import tempfile
import time
from pathlib import Path
import streamlit as st
import geopandas as gpd
import pandas as pd
from streamlit_folium import st_folium

# Importación de módulos locales
from modules.io import (
    extract_zip_shapefile,
    read_shapefile,
    scan_directory_for_shapefiles,
    export_to_excel,
    export_to_gpkg
)
from modules.crs import (
    get_crs_info,
    suggest_utm_epsg,
    reproject_gdf
)
from modules.geometry import clean_and_validate_geometries
from modules.spatial_analysis import create_buffer_layer
from modules.distance import (
    build_spatial_index,
    analyze_proximity_batch
)
from modules.reporting import (
    generate_summary_reports,
    classify_distance_ranges
)
from modules.visualization import (
    create_folium_map,
    create_plotly_charts
)
from modules.utils import format_meters, format_percentage, log_error

# Configuración de página Streamlit
st.set_page_config(
    page_title="GIS Spatial Intersection & Proximity Analyzer",
    page_icon="🗺️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Estilo personalizado CSS para UI moderna y pulida
st.markdown("""
<style>
    .main-header {
        font-size: 2.2rem;
        font-weight: 700;
        color: #1E293B;
        margin-bottom: 0.2rem;
    }
    .sub-header {
        font-size: 1.05rem;
        color: #64748B;
        margin-bottom: 1.5rem;
    }
    .metric-card {
        background-color: #F8FAFC;
        border: 1px solid #E2E8F0;
        border-radius: 8px;
        padding: 1rem;
        text-align: center;
    }
    .stButton>button {
        width: 100%;
        background-color: #2563EB;
        color: white;
        font-weight: 600;
        border-radius: 6px;
        padding: 0.6rem;
    }
    .stButton>button:hover {
        background-color: #1D4ED8;
    }
</style>
""", unsafe_allow_html=True)

def initialize_session_state():
    """Inicializa las variables de estado de sesión de Streamlit."""
    defaults = {
        "analysis_executed": False,
        "df_results": None,
        "df_summary": None,
        "df_non_intersected": None,
        "global_kpis": None,
        "df_ranges": None,
        "df_errors": None,
        "gdf_ref_proj": None,
        "gdf_buffer_proj": None,
        "gdf_int_proj": None,
        "gdf_nint_proj": None,
        "gdf_lines_proj": None,
        "excel_bytes": None,
        "gpkg_bytes": None,
        "scanned_shps": []
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val

def main():
    initialize_session_state()

    st.markdown('<div class="main-header">🗺️ GIS Spatial Intersection & Proximity Analyzer</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Análisis espacial robusto de intersección con buffer y distancias mínimas reales sobre archivos Shapefile recursivos.</div>', unsafe_allow_html=True)

    # =========================================================================
    # SIDEBAR: CONFIGURACIÓN Y PARÁMETROS
    # =========================================================================
    st.sidebar.header("⚙️ Configuración del Análisis")

    # 1. Carga de SHP de Referencia (ZIP)
    st.sidebar.subheader("1. Shapefile de Referencia")
    uploaded_zip = st.sidebar.file_uploader(
        "Cargar archivo .ZIP con el Shapefile completo (.shp, .shx, .dbf, .prj)",
        type=["zip"],
        help="El archivo comprimido debe incluir al menos los archivos .shp, .shx, .dbf y .prj."
    )

    # 2. Ruta Carpeta Raíz de Análisis
    st.sidebar.subheader("2. Carpeta de Análisis")
    root_folder_input = st.sidebar.text_input(
        "Ruta a la carpeta principal en disco:",
        value=os.getcwd(),
        help="Ruta completa de la carpeta que contiene los subdirectorios con archivos .shp a analizar."
    )

    # 3. Parámetro de Buffer
    st.sidebar.subheader("3. Parámetros Espaciales")
    buffer_meters = st.sidebar.number_input(
        "Distancia de Buffer (Metros reales):",
        min_value=0.0,
        max_value=100000.0,
        value=100.0,
        step=10.0,
        help="Distancia de buffer métrico a aplicar alrededor del Shapefile de referencia."
    )

    # Opción de CRS
    override_crs = st.sidebar.checkbox("Configurar EPSG manualmente", value=False)
    manual_epsg = None
    if override_crs:
        manual_epsg = st.sidebar.number_input("Código EPSG proyectado métrico:", value=32719, step=1)

    # Botón de ejecución
    execute_button = st.sidebar.button("🚀 EJECUTAR ANÁLISIS")

    # =========================================================================
    # LÓGICA DE EJECUCIÓN DE ANÁLISIS
    # =========================================================================
    if execute_button:
        if not uploaded_zip:
            st.error("❌ Debe cargar un archivo ZIP con el Shapefile de referencia.")
            return

        if not os.path.exists(root_folder_input) or not os.path.isdir(root_folder_input):
            st.error(f"❌ La ruta especificada '{root_folder_input}' no existe o no es un directorio válido.")
            return

        with st.spinner("⏳ Preparando y procesando capas geográficas..."):
            start_time = time.time()
            progress_bar = st.progress(0)
            status_text = st.empty()

            try:
                # 1. Extraer ZIP de referencia en directorio temporal
                with tempfile.TemporaryDirectory() as temp_dir:
                    status_text.text("📦 Extrayendo y leyendo Shapefile de referencia...")
                    ref_shp_path = extract_zip_shapefile(uploaded_zip, temp_dir)
                    gdf_ref_raw = read_shapefile(ref_shp_path)

                    # Validar y reparar geometrías de referencia
                    gdf_ref_clean, ref_geom_stats = clean_and_validate_geometries(gdf_ref_raw)
                    if len(gdf_ref_clean) == 0:
                        st.error("❌ El Shapefile de referencia no contiene geometrías válidas.")
                        return

                    # 2. Determinar CRS proyectado métrico
                    if manual_epsg:
                        target_crs = f"EPSG:{manual_epsg}"
                        crs_desc = f"EPSG:{manual_epsg} (Ingresado manualmente)"
                    else:
                        target_epsg, crs_desc = suggest_utm_epsg(gdf_ref_clean)
                        target_crs = f"EPSG:{target_epsg}"

                    # Reproyectar referencia a CRS proyectado métrico
                    gdf_ref_proj = reproject_gdf(gdf_ref_clean, target_crs)

                    # 3. Generar Buffer e Índice Espacial STRtree
                    status_text.text("🌐 Generando buffer métrico e índice espacial STRtree...")
                    buffer_dissolved, gdf_buffer_proj = create_buffer_layer(gdf_ref_proj, buffer_meters)
                    strtree_ref = build_spatial_index(gdf_ref_proj)

                    # 4. Escanear carpeta de análisis recursivamente
                    status_text.text("🔍 Escaneando archivos Shapefile en subcarpetas...")
                    scanned_shps = scan_directory_for_shapefiles(root_folder_input)
                    st.session_state["scanned_shps"] = scanned_shps

                    if not scanned_shps:
                        st.warning("⚠️ No se encontraron archivos .shp en la carpeta especificada.")
                        return

                    # 5. Procesar batch de archivos SHP encontrando intersecciones y distancias
                    all_results = []
                    all_lines = []
                    error_logs = []

                    total_shps = len(scanned_shps)
                    int_records_list = []
                    nint_records_list = []

                    for idx_file, shp_info in enumerate(scanned_shps):
                        progress_val = int(((idx_file + 1) / total_shps) * 100)
                        progress_bar.progress(progress_val)
                        status_text.text(f"⚡ Procesando archivo {idx_file + 1} de {total_shps}: {shp_info['archivo']}")

                        try:
                            gdf_layer_raw = read_shapefile(shp_info["ruta_absoluta"])
                            if gdf_layer_raw is None or len(gdf_layer_raw) == 0:
                                continue

                            # Validar/Reparar geometrías
                            gdf_layer_clean, _ = clean_and_validate_geometries(gdf_layer_raw)
                            if len(gdf_layer_clean) == 0:
                                continue

                            # Reproyectar al CRS métrico de análisis
                            gdf_layer_proj = reproject_gdf(gdf_layer_clean, target_crs)

                            # Ejecutar proximidad entidad por entidad
                            results_batch, lines_batch = analyze_proximity_batch(
                                gdf_layer_proj,
                                gdf_ref_proj,
                                strtree_ref,
                                buffer_dissolved,
                                shp_info,
                                target_crs
                            )

                            all_results.extend(results_batch)
                            all_lines.extend(lines_batch)

                        except Exception as e:
                            err_entry = log_error(shp_info["ruta_relativa"], e)
                            error_logs.append(err_entry)

                    # 6. Generar DataFrames de Reporte
                    status_text.text("📊 Compilando estadísticas y reportes finales...")
                    df_results, df_summary, df_non_intersected, global_kpis = generate_summary_reports(all_results)
                    df_ranges = classify_distance_ranges(df_non_intersected)
                    df_errors = pd.DataFrame(error_logs)

                    # 7. Reconstruir GeoDataFrames para Mapa y Exportación
                    gdf_int_proj = None
                    gdf_nint_proj = None
                    gdf_lines_proj = None

                    if not df_results.empty:
                        df_int = df_results[df_results["estado"] == "INTERSECTA"].drop(columns=["linea_conexion"], errors="ignore")
                        df_nint = df_results[df_results["estado"] == "NO INTERSECTA"].drop(columns=["linea_conexion"], errors="ignore")

                        if not df_int.empty:
                            gdf_int_proj = gpd.GeoDataFrame(df_int, geometry="geometry", crs=target_crs)
                        if not df_nint.empty:
                            gdf_nint_proj = gpd.GeoDataFrame(df_nint, geometry="geometry", crs=target_crs)

                    if all_lines:
                        gdf_lines_proj = gpd.GeoDataFrame(all_lines, geometry="geometry", crs=target_crs)

                    # 8. Exportar descargas en memoria (Excel y GPKG)
                    status_text.text("💾 Generando archivos de exportación (Excel & GeoPackage)...")
                    excel_bytes = export_to_excel(df_summary, df_results, gdf_int_proj, gdf_nint_proj, df_ranges, df_errors)
                    gpkg_bytes = export_to_gpkg(gdf_ref_proj, gdf_buffer_proj, gdf_int_proj, gdf_nint_proj, gdf_lines_proj)

                    # Guardar todo en Session State
                    st.session_state["analysis_executed"] = True
                    st.session_state["df_results"] = df_results
                    st.session_state["df_summary"] = df_summary
                    st.session_state["df_non_intersected"] = df_non_intersected
                    st.session_state["global_kpis"] = global_kpis
                    st.session_state["df_ranges"] = df_ranges
                    st.session_state["df_errors"] = df_errors
                    st.session_state["gdf_ref_proj"] = gdf_ref_proj
                    st.session_state["gdf_buffer_proj"] = gdf_buffer_proj
                    st.session_state["gdf_int_proj"] = gdf_int_proj
                    st.session_state["gdf_nint_proj"] = gdf_nint_proj
                    st.session_state["gdf_lines_proj"] = gdf_lines_proj
                    st.session_state["excel_bytes"] = excel_bytes
                    st.session_state["gpkg_bytes"] = gpkg_bytes
                    st.session_state["crs_desc"] = crs_desc

                    elapsed = round(time.time() - start_time, 2)
                    status_text.success(f"✅ ¡Análisis completado exitosamente en {elapsed} segundos!")
                    progress_bar.progress(100)

            except Exception as ex:
                st.error(f"❌ Error crítico en el análisis: {str(ex)}")
                return

    # =========================================================================
    # ÁREA PRINCIPAL: PESTAÑAS DE RESULTADOS
    # =========================================================================
    if not st.session_state["analysis_executed"]:
        st.info("👈 Por favor, cargue el Shapefile de referencia en la barra lateral y presione 'EJECUTAR ANÁLISIS' para comenzar.")
        return

    # Recuperar de session state
    df_results = st.session_state["df_results"]
    df_summary = st.session_state["df_summary"]
    df_non_intersected = st.session_state["df_non_intersected"]
    kpis = st.session_state["global_kpis"]
    df_ranges = st.session_state["df_ranges"]
    df_errors = st.session_state["df_errors"]
    crs_desc = st.session_state.get("crs_desc", "N/A")

    # Información de CRS en encabezado principal
    st.caption(f"🎯 **CRS de Análisis Utilizado**: `{crs_desc}` | **Unidades**: Metros reales (m)")

    # Definición de pestañas
    tab_summary, tab_map, tab_results, tab_non_int, tab_charts, tab_files, tab_errors, tab_downloads = st.tabs([
        "📊 Resumen",
        "🗺️ Mapa Interactivo",
        "📋 Resultados",
        "🔴 No Intersectados",
        "📏 Distancias & Gráficos",
        "📁 Archivos",
        "⚠️ Errores",
        "📥 Descargas"
    ])

    # -------------------------------------------------------------------------
    # TAB 1: RESUMEN Y KPIS
    # -------------------------------------------------------------------------
    with tab_summary:
        st.subheader("Indicadores Clave de Desempeño (KPIs)")
        col1, col2, col3, col4, col5 = st.columns(5)
        col1.metric("Archivos Analizados", kpis["total_archivos"])
        col2.metric("Total Entidades", kpis["total_entidades"])
        col3.metric("Intersectan Buffer", f"{kpis['total_intersectan']} ({kpis['pct_intersectan']}%)")
        col4.metric("No Intersectan", f"{kpis['total_no_intersectan']} ({kpis['pct_no_intersectan']}%)")
        col5.metric("Dist. Promedio No Intersect.", format_meters(kpis["dist_avg"]))

        st.markdown("---")
        st.subheader("Resumen de Entidades por Archivo Shapefile")
        if not df_summary.empty:
            st.dataframe(df_summary, use_container_width=True)

    # -------------------------------------------------------------------------
    # TAB 2: MAPA INTERACTIVO (FOLIUM)
    # -------------------------------------------------------------------------
    with tab_map:
        st.subheader("Mapa Interactivo Espacial")
        st.markdown("Visualización con capas independientes: **Referencia (Azul)**, **Buffer (Naranja)**, **Intersectados (Verde)**, **No Intersectados (Rojo)** y **Conectores de Distancia (Púrpura)**.")
        
        map_folium = create_folium_map(
            st.session_state["gdf_ref_proj"],
            st.session_state["gdf_buffer_proj"],
            st.session_state["gdf_int_proj"],
            st.session_state["gdf_nint_proj"],
            st.session_state["gdf_lines_proj"]
        )
        st_folium(map_folium, width="100%", height=600)

    # -------------------------------------------------------------------------
    # TAB 3: RESULTADOS CONSOLIDADOS
    # -------------------------------------------------------------------------
    with tab_results:
        st.subheader("Resultados Detallados por Entidad")
        if not df_results.empty:
            cols_show = [c for c in df_results.columns if c not in ["geometry", "linea_conexion"]]
            
            # Filtro por estado
            filter_state = st.multiselect("Filtrar por Estado:", options=["INTERSECTA", "NO INTERSECTA"], default=["INTERSECTA", "NO INTERSECTA"])
            filtered_df = df_results[df_results["estado"].isin(filter_state)][cols_show]
            
            st.dataframe(filtered_df, use_container_width=True)

    # -------------------------------------------------------------------------
    # TAB 4: ELEMENTOS NO INTERSECTADOS
    # -------------------------------------------------------------------------
    with tab_non_int:
        st.subheader("Elementos fuera del Buffer (Ordenados por Distancia Ascendente)")
        st.markdown("Identificación rápida del elemento de referencia más cercano y distancia exacta en metros.")
        if not df_non_intersected.empty:
            cols_show = [c for c in df_non_intersected.columns if c not in ["geometry", "linea_conexion"]]
            st.dataframe(df_non_intersected[cols_show], use_container_width=True)
        else:
            st.success("🎉 Todos los elementos intersectan el buffer. No hay elementos fuera.")

    # -------------------------------------------------------------------------
    # TAB 5: DISTANCIAS Y GRÁFICOS INTERACTIVOS
    # -------------------------------------------------------------------------
    with tab_charts:
        st.subheader("Análisis Gráfico y Esquema de Distancias")
        charts = create_plotly_charts(df_results, df_summary, df_non_intersected, df_ranges)
        
        c1, c2 = st.columns(2)
        with c1:
            if "fig_donut" in charts:
                st.plotly_chart(charts["fig_donut"], use_container_width=True)
        with c2:
            if "fig_ranges" in charts:
                st.plotly_chart(charts["fig_ranges"], use_container_width=True)

        c3, c4 = st.columns(2)
        with c3:
            if "fig_hist" in charts:
                st.plotly_chart(charts["fig_hist"], use_container_width=True)
        with c4:
            if "fig_bar_files" in charts:
                st.plotly_chart(charts["fig_bar_files"], use_container_width=True)

    # -------------------------------------------------------------------------
    # TAB 6: ARCHIVOS ESCANEADOS
    # -------------------------------------------------------------------------
    with tab_files:
        st.subheader("Estructura de Archivos Escaneada")
        scanned = st.session_state["scanned_shps"]
        if scanned:
            df_files = pd.DataFrame(scanned)
            st.dataframe(df_files[["archivo", "subcarpeta", "ruta_relativa"]], use_container_width=True)

    # -------------------------------------------------------------------------
    # TAB 7: LOG DE ERRORES
    # -------------------------------------------------------------------------
    with tab_errors:
        st.subheader("Registro de Errores de Procesamiento")
        if df_errors is not None and not df_errors.empty:
            st.warning("⚠️ Se registraron advertencias o errores durante la lectura de algunos archivos:")
            st.dataframe(df_errors, use_container_width=True)
        else:
            st.success("✅ No se registraron errores durante el escaneo y procesamiento.")

    # -------------------------------------------------------------------------
    # TAB 8: DESCARGAS DE REPORTES Y DATOS ESPACIALES
    # -------------------------------------------------------------------------
    with tab_downloads:
        st.subheader("Exportación de Resultados")
        st.markdown("Descargue los reportes en formatos estándar para análisis posterior en Excel o SIG (QGIS / ArcGIS Pro).")

        col_d1, col_d2, col_d3 = st.columns(3)

        with col_d1:
            st.download_button(
                label="📊 Descargar Reporte Excel (.xlsx)",
                data=st.session_state["excel_bytes"],
                file_name="Reporte_GIS_Interseccion_Proximidad.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

        with col_d2:
            if not df_results.empty:
                cols_csv = [c for c in df_results.columns if c not in ["geometry", "linea_conexion"]]
                csv_data = df_results[cols_csv].to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="📄 Descargar Resultados CSV (.csv)",
                    data=csv_data,
                    file_name="Resultados_GIS.csv",
                    mime="text/csv"
                )

        with col_d3:
            if st.session_state["gpkg_bytes"]:
                st.download_button(
                    label="🗺️ Descargar GeoPackage SIG (.gpkg)",
                    data=st.session_state["gpkg_bytes"],
                    file_name="Capas_GIS_Interseccion_Buffer.gpkg",
                    mime="application/geopackage+sqlite3"
                )

if __name__ == "__main__":
    main()
