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

import json

def convert_gdf_to_geojson_str(gdf: Optional[gpd.GeoDataFrame], max_features: int = 2000) -> Optional[str]:
    """Convierte un GeoDataFrame en un string GeoJSON ligero y 100% serializable para session_state."""
    if gdf is None or len(gdf) == 0:
        return None
    try:
        df_c = gdf.copy()
        if "linea_conexion" in df_c.columns:
            df_c = df_c.drop(columns=["linea_conexion"])
        if len(df_c) > max_features:
            df_c = df_c.iloc[:max_features]
        df_4326 = df_c.to_crs("EPSG:4326")
        try:
            df_4326["geometry"] = df_4326.geometry.simplify(0.00005, preserve_topology=True)
        except Exception:
            pass
        return df_4326.to_json()
    except Exception:
        return None

def create_folium_map(
    gdf_ref: Any = None,
    gdf_buffer: Any = None,
    gdf_intersected: Any = None,
    gdf_non_intersected: Any = None,
    gdf_lines: Any = None
) -> folium.Map:
    """
    Crea un mapa interactivo de Folium recibiendo GeoDataFrames o strings GeoJSON serializados.
    """
    def _to_geojson_dict(data: Any) -> Optional[Dict[str, Any]]:
        if data is None:
            return None
        if isinstance(data, str):
            try:
                return json.loads(data)
            except Exception:
                return None
        if isinstance(data, gpd.GeoDataFrame) and len(data) > 0:
            json_str = convert_gdf_to_geojson_str(data)
            return json.loads(json_str) if json_str else None
        return None

    geo_ref = _to_geojson_dict(gdf_ref)
    geo_buf = _to_geojson_dict(gdf_buffer)
    geo_int = _to_geojson_dict(gdf_intersected)
    geo_nint = _to_geojson_dict(gdf_non_intersected)
    geo_lines = _to_geojson_dict(gdf_lines)

    # Calcular centro del mapa a partir de bounding box
    center_lat, center_lon = -33.45, -70.66
    for gdict in [geo_buf, geo_ref, geo_int, geo_nint]:
        if gdict and "features" in gdict and gdict["features"]:
            try:
                coords = []
                for feat in gdict["features"][:50]:
                    g = feat.get("geometry", {})
                    g_type = g.get("type", "")
                    g_coords = g.get("coordinates", [])
                    if g_type == "Point":
                        coords.append(g_coords)
                    elif g_type in ["LineString", "MultiPoint"]:
                        coords.extend(g_coords)
                    elif g_type in ["Polygon", "MultiLineString"]:
                        for poly in g_coords:
                            coords.extend(poly)
                if coords:
                    lons = [c[0] for c in coords if isinstance(c, (list, tuple)) and len(c) >= 2]
                    lats = [c[1] for c in coords if isinstance(c, (list, tuple)) and len(c) >= 2]
                    if lons and lats:
                        center_lon = sum(lons) / len(lons)
                        center_lat = sum(lats) / len(lats)
                        break
            except Exception:
                pass

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

    # Capa 1: Referencia
    if geo_ref:
        fg_ref = folium.FeatureGroup(name="1. SHP Referencia", show=True)
        folium.GeoJson(
            geo_ref,
            style_function=lambda x: {
                "color": "#1f77b4",
                "weight": 3,
                "fillColor": "#1f77b4",
                "fillOpacity": 0.4
            }
        ).add_to(fg_ref)
        fg_ref.add_to(m)

    # Capa 2: Buffer
    if geo_buf:
        fg_buf = folium.FeatureGroup(name="2. Buffer", show=True)
        folium.GeoJson(
            geo_buf,
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

    # Capa 3: Intersectados (Verde)
    if geo_int:
        fg_int = folium.FeatureGroup(name="3. Intersectados (Verde)", show=True)
        folium.GeoJson(
            geo_int,
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

    # Capa 4: No Intersectados (Rojo)
    if geo_nint:
        fg_nint = folium.FeatureGroup(name="4. No Intersectados (Rojo)", show=True)
        folium.GeoJson(
            geo_nint,
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

    # Capa 5: Conectores
    if geo_lines:
        fg_lines = folium.FeatureGroup(name="5. Líneas de Conexión y Distancia", show=True)
        folium.GeoJson(
            geo_lines,
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

    # Controles
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
    """Genera gráficos interactivos con Plotly reflejando siempre la intersección y proximidad."""
    charts = {}

    # Gráfico 1: Dona Intersectados vs No Intersectados
    if not df_results.empty:
        state_counts = df_results["estado"].value_counts().reset_index()
        state_counts.columns = ["Estado", "Cantidad"]
        
        fig1 = px.pie(
            state_counts,
            names="Estado",
            values="Cantidad",
            hole=0.45,
            title="Proporción Total: Intersectan vs No Intersectan",
            color="Estado",
            color_discrete_map={"INTERSECTA": "#2ca02c", "NO INTERSECTA": "#d62728"}
        )
        fig1.update_traces(textposition='inside', textinfo='percent+value+label', hovertemplate='%{label}: %{value} entidades (%{percent})')
        fig1.update_layout(showlegend=True)
        charts["fig_donut"] = fig1

    # Gráfico 2: Histograma de distancias (Incluyendo 0 m de Intersectados)
    if not df_results.empty:
        fig2 = px.histogram(
            df_results,
            x="distancia_m",
            color="estado",
            nbins=30,
            title="Distribución Global de Distancias en Metros",
            labels={"distancia_m": "Distancia al Buffer (m)", "estado": "Estado"},
            color_discrete_map={"INTERSECTA": "#2ca02c", "NO INTERSECTA": "#d62728"},
            barmode="overlay"
        )
        fig2.update_layout(xaxis_title="Distancia (m)", yaxis_title="Cantidad de Entidades")
        charts["fig_hist"] = fig2

    # Gráfico 3: Entidades por Archivo (Intersectadas vs No Intersectadas)
    if not df_summary.empty:
        df_melt = df_summary.melt(
            id_vars=["archivo"],
            value_vars=["intersectan", "no_intersectan"],
            var_name="Estado",
            value_name="Cantidad"
        )
        df_melt["Estado"] = df_melt["Estado"].replace({"intersectan": "INTERSECTA", "no_intersectan": "NO INTERSECTA"})
        
        fig3 = px.bar(
            df_melt,
            x="archivo",
            y="Cantidad",
            color="Estado",
            text="Cantidad",
            title="Entidades por Archivo Shapefile (Intersectadas vs No Intersectadas)",
            barmode="stack",
            color_discrete_map={"INTERSECTA": "#2ca02c", "NO INTERSECTA": "#d62728"}
        )
        fig3.update_layout(xaxis_title="Archivo Shapefile", yaxis_title="Cantidad de Entidades")
        charts["fig_bar_files"] = fig3

    # Gráfico 4: Cantidad por Rango de Distancia (Incluye 0 m Intersecta)
    if not df_ranges.empty:
        color_map = {
            "0 m (Intersecta)": "#2ca02c",
            "0.1 - 50 m": "#ffbb78",
            "50 - 100 m": "#ff7f0e",
            "100 - 250 m": "#e377c2",
            "250 - 500 m": "#d62728",
            "> 500 m": "#8c564b"
        }
        
        fig4 = px.bar(
            df_ranges,
            x="rango_distancia",
            y="cantidad",
            text="cantidad",
            title="Clasificación General por Rangos de Distancia",
            color="rango_distancia",
            color_discrete_map=color_map
        )
        fig4.update_layout(xaxis_title="Rango de Distancia", yaxis_title="Cantidad de Entidades", showlegend=False)
        charts["fig_ranges"] = fig4

    return charts
