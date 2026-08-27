"""
Módulo para visualizaciones espacial (Folium) e interactiva (Plotly).
"""
import folium
from folium.plugins import MeasureControl, Fullscreen
import geopandas as gpd
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from typing import Optional, Dict, Any

def create_folium_map(
    gdf_ref: gpd.GeoDataFrame,
    gdf_buffer: gpd.GeoDataFrame,
    gdf_intersected: Optional[gpd.GeoDataFrame] = None,
    gdf_non_intersected: Optional[gpd.GeoDataFrame] = None,
    gdf_lines: Optional[gpd.GeoDataFrame] = None
) -> folium.Map:
    """
    Crea un mapa interactivo de Folium con capas independientes, popups y control de capas.
    """
    # Helper para eliminar columnas no serializables en JSON y optimizar payload de Folium
    def _clean_gdf(df: Optional[gpd.GeoDataFrame], max_features: int = 3000) -> Optional[gpd.GeoDataFrame]:
        if df is None or len(df) == 0:
            return None
        df_c = df.copy()
        if "linea_conexion" in df_c.columns:
            df_c = df_c.drop(columns=["linea_conexion"])
        
        # Limitar número de entidades para evitar saturación de memoria en navegador/servidor
        if len(df_c) > max_features:
            df_c = df_c.iloc[:max_features]
            
        df_4326 = df_c.to_crs("EPSG:4326")
        
        # Simplificación de geometrías complejas para renderizado ágil en la web
        try:
            df_4326["geometry"] = df_4326.geometry.simplify(0.00005, preserve_topology=True)
        except Exception:
            pass
            
        return df_4326

    # 1. Reproyectar a WGS84 (EPSG:4326) para Folium
    gdf_ref_4326 = _clean_gdf(gdf_ref, max_features=1000)
    gdf_buf_4326 = _clean_gdf(gdf_buffer, max_features=500)
    gdf_int_4326 = _clean_gdf(gdf_intersected, max_features=3000)
    gdf_nint_4326 = _clean_gdf(gdf_non_intersected, max_features=3000)
    gdf_lines_4326 = _clean_gdf(gdf_lines, max_features=3000)

    # Calcular centro del mapa
    if gdf_buf_4326 is not None:
        bounds = gdf_buf_4326.total_bounds
        center_lat = (bounds[1] + bounds[3]) / 2.0
        center_lon = (bounds[0] + bounds[2]) / 2.0
    elif gdf_ref_4326 is not None:
        bounds = gdf_ref_4326.total_bounds
        center_lat = (bounds[1] + bounds[3]) / 2.0
        center_lon = (bounds[0] + bounds[2]) / 2.0
    else:
        center_lat, center_lon = -33.45, -70.66 # Santiago de Chile por defecto

    # Inicializar mapa
    m = folium.Map(location=[center_lat, center_lon], zoom_start=12, tiles=None)

    # Añadir capas base
    folium.TileLayer("OpenStreetMap", name="OpenStreetMap").add_to(m)
    folium.TileLayer("CartoDB positron", name="CartoDB Positron").add_to(m)
    folium.TileLayer(
        tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
        attr="Esri World Imagery",
        name="Satélite (Esri)"
    ).add_to(m)

    # Capa 1: Shapefile de Referencia
    if gdf_ref_4326 is not None:
        fg_ref = folium.FeatureGroup(name="1. SHP Referencia", show=True)
        folium.GeoJson(
            gdf_ref_4326,
            style_function=lambda x: {
                "color": "#1f77b4",
                "weight": 3,
                "fillColor": "#1f77b4",
                "fillOpacity": 0.4
            },
            tooltip=folium.GeoJsonTooltip(fields=[c for c in gdf_ref_4326.columns if c != "geometry"][:5])
        ).add_to(fg_ref)
        fg_ref.add_to(m)

    # Capa 2: Buffer
    if gdf_buf_4326 is not None:
        fg_buf = folium.FeatureGroup(name="2. Buffer", show=True)
        folium.GeoJson(
            gdf_buf_4326,
            style_function=lambda x: {
                "color": "#ff7f0e",
                "weight": 2,
                "dashArray": "5, 5",
                "fillColor": "#ffbb78",
                "fillOpacity": 0.2
            },
            tooltip="Zona Buffer"
        ).add_to(fg_buf)
        fg_buf.add_to(m)

    # Capa 3: Elementos Intersectados (Verde)
    if gdf_int_4326 is not None:
        fg_int = folium.FeatureGroup(name="3. Intersectados (Verde)", show=True)
        folium.GeoJson(
            gdf_int_4326,
            style_function=lambda x: {
                "color": "#2ca02c",
                "weight": 3,
                "fillColor": "#2ca02c",
                "fillOpacity": 0.6
            },
            popup=folium.GeoJsonPopup(
                fields=["archivo", "id_entidad", "estado", "id_referencia_mas_cercana", "distancia_m"],
                aliases=["Archivo:", "ID Entidad:", "Estado:", "Ref Cercana:", "Distancia (m):"]
            )
        ).add_to(fg_int)
        fg_int.add_to(m)

    # Capa 4: Elementos No Intersectados (Rojo)
    if gdf_nint_4326 is not None:
        fg_nint = folium.FeatureGroup(name="4. No Intersectados (Rojo)", show=True)
        folium.GeoJson(
            gdf_nint_4326,
            style_function=lambda x: {
                "color": "#d62728",
                "weight": 3,
                "fillColor": "#d62728",
                "fillOpacity": 0.6
            },
            popup=folium.GeoJsonPopup(
                fields=["archivo", "id_entidad", "estado", "id_referencia_mas_cercana", "distancia_m"],
                aliases=["Archivo:", "ID Entidad:", "Estado:", "Ref Cercana:", "Distancia (m):"]
            )
        ).add_to(fg_nint)
        fg_nint.add_to(m)

    # Capa 5: Líneas de Distancia y Conexión
    if gdf_lines_4326 is not None:
        fg_lines = folium.FeatureGroup(name="5. Líneas de Conexión y Distancia", show=True)
        folium.GeoJson(
            gdf_lines_4326,
            style_function=lambda x: {
                "color": "#9467bd",
                "weight": 2,
                "dashArray": "4, 4",
                "opacity": 0.8
            },
            popup=folium.GeoJsonPopup(
                fields=["archivo", "id_entidad", "id_referencia_mas_cercana", "distancia_m"],
                aliases=["Archivo:", "ID Entidad:", "Ref Cercana:", "Distancia (m):"]
            )
        ).add_to(fg_lines)
        fg_lines.add_to(m)

    # Agregar plugins y controles
    folium.LayerControl(collapsed=False).add_to(m)
    MeasureControl(position="topright", primary_length_unit="meters").add_to(m)
    Fullscreen().add_to(m)

    return m

def create_plotly_charts(
    df_results: pd.DataFrame,
    df_summary: pd.DataFrame,
    df_non_intersected: pd.DataFrame,
    df_ranges: pd.DataFrame
) -> Dict[str, go.Figure]:
    """Genera gráficos interactivos con Plotly para análisis de datos."""
    charts = {}

    # Gráfico 1: Dona Intersectados vs No Intersectados
    if not df_results.empty:
        state_counts = df_results["estado"].value_counts().reset_index()
        state_counts.columns = ["Estado", "Cantidad"]
        
        fig1 = px.pie(
            state_counts,
            names="Estado",
            values="Cantidad",
            hole=0.4,
            title="Distribución Total de Entidades Analyzadas",
            color="Estado",
            color_discrete_map={"INTERSECTA": "#2ca02c", "NO INTERSECTA": "#d62728"}
        )
        fig1.update_traces(textposition='inside', textinfo='percent+label')
        charts["fig_donut"] = fig1

    # Gráfico 2: Histograma de distancias (No Intersectados)
    if not df_non_intersected.empty:
        fig2 = px.histogram(
            df_non_intersected,
            x="distancia_m",
            nbins=30,
            title="Distribución de Distancias al Elemento de Referencia (Metros)",
            labels={"distancia_m": "Distancia (m)"},
            color_discrete_sequence=["#9467bd"]
        )
        fig2.update_layout(xaxis_title="Distancia (m)", yaxis_title="Frecuencia (Cantidad de Entidades)")
        charts["fig_hist"] = fig2

    # Gráfico 3: Entidades por Archivo (Intersectadas vs No Intersectadas)
    if not df_summary.empty:
        df_melt = df_summary.melt(
            id_vars=["archivo"],
            value_vars=["intersectan", "no_intersectan"],
            var_name="Estado",
            value_name="Cantidad"
        )
        df_melt["Estado"] = df_melt["Estado"].replace({"intersectan": "Intersecta", "no_intersectan": "No Intersecta"})
        
        fig3 = px.bar(
            df_melt,
            x="archivo",
            y="Cantidad",
            color="Estado",
            title="Entidades por Archivo de Análisis",
            barmode="stack",
            color_discrete_map={"Intersecta": "#2ca02c", "No Intersecta": "#d62728"}
        )
        fig3.update_layout(xaxis_title="Archivo Shapefile", yaxis_title="Cantidad de Entidades")
        charts["fig_bar_files"] = fig3

    # Gráfico 4: Cantidad por Rango de Distancia
    if not df_ranges.empty:
        fig4 = px.bar(
            df_ranges,
            x="rango_distancia",
            y="cantidad",
            text="cantidad",
            title="Clasificación de Elementos por Rango de Distancia",
            color="rango_distancia",
            color_discrete_sequence=px.colors.sequential.OrRd[::-1]
        )
        fig4.update_layout(xaxis_title="Rango de Distancia", yaxis_title="Cantidad de Entidades")
        charts["fig_ranges"] = fig4

    return charts
