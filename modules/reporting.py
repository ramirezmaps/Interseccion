"""
Módulo para consolidación de reportes, estadísticas KPI y categorización por rangos de distancia.
"""
import pandas as pd
import numpy as np
from typing import List, Dict, Any, Tuple, Optional

DEFAULT_DISTANCE_BINS = [0, 50, 100, 250, 500, np.inf]
DEFAULT_BIN_LABELS = ["0 - 50 m", "50 - 100 m", "100 - 250 m", "250 - 500 m", "> 500 m"]

def generate_summary_reports(
    results_records: List[Dict[str, Any]]
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, Dict[str, Any]]:
    """
    Procesa la lista de registros de entidades y genera:
        - DataFrame consolidado de resultados
        - DataFrame resumen por archivo
        - DataFrame específico de no intersectados ordenado por distancia
        - Diccionario de métricas KPI globales
    """
    if not results_records:
        empty_df = pd.DataFrame()
        empty_kpis = {
            "total_archivos": 0,
            "total_entidades": 0,
            "total_intersectan": 0,
            "total_no_intersectan": 0,
            "pct_intersectan": 0.0,
            "pct_no_intersectan": 0.0,
            "dist_min": 0.0,
            "dist_avg": 0.0,
            "dist_max": 0.0
        }
        return empty_df, empty_df, empty_df, empty_kpis
        
    df_results = pd.DataFrame(results_records)
    
    # 1. Resumen por archivo
    summary_rows = []
    for (archivo, subcarpeta), group in df_results.groupby(["archivo", "subcarpeta"]):
        total = len(group)
        intersectan = (group["estado"] == "INTERSECTA").sum()
        no_intersectan = (group["estado"] == "NO INTERSECTA").sum()
        
        pct_int = (intersectan / total) * 100.0 if total > 0 else 0.0
        pct_no_int = (no_intersectan / total) * 100.0 if total > 0 else 0.0
        
        non_int_group = group[group["estado"] == "NO INTERSECTA"]
        if len(non_int_group) > 0:
            dist_min = non_int_group["distancia_m"].min()
            dist_max = non_int_group["distancia_m"].max()
            dist_avg = non_int_group["distancia_m"].mean()
        else:
            dist_min = 0.0
            dist_max = 0.0
            dist_avg = 0.0
            
        summary_rows.append({
            "archivo": archivo,
            "subcarpeta": subcarpeta,
            "total_entidades": total,
            "intersectan": intersectan,
            "no_intersectan": no_intersectan,
            "porcentaje_intersectan": round(pct_int, 1),
            "porcentaje_no_intersectan": round(pct_no_int, 1),
            "distancia_min_m": round(dist_min, 2),
            "distancia_max_m": round(dist_max, 2),
            "distancia_promedio_m": round(dist_avg, 2)
        })
        
    df_summary = pd.DataFrame(summary_rows)
    
    # 2. Elementos que NO intersectan ordenados por distancia ascendente
    df_non_intersected = df_results[df_results["estado"] == "NO INTERSECTA"].copy()
    if not df_non_intersected.empty:
        df_non_intersected.sort_values(by="distancia_m", ascending=True, inplace=True)
        
    # 3. Métricas Globales (KPIs)
    total_archivos = df_results["archivo"].nunique()
    total_entidades = len(df_results)
    total_int = (df_results["estado"] == "INTERSECTA").sum()
    total_no_int = (df_results["estado"] == "NO INTERSECTA").sum()
    
    pct_global_int = (total_int / total_entidades) * 100.0 if total_entidades > 0 else 0.0
    pct_global_no_int = (total_no_int / total_entidades) * 100.0 if total_entidades > 0 else 0.0
    
    if total_no_int > 0:
        g_min = df_non_intersected["distancia_m"].min()
        g_avg = df_non_intersected["distancia_m"].mean()
        g_max = df_non_intersected["distancia_m"].max()
    else:
        g_min, g_avg, g_max = 0.0, 0.0, 0.0
        
    global_kpis = {
        "total_archivos": total_archivos,
        "total_entidades": total_entidades,
        "total_intersectan": total_int,
        "total_no_intersectan": total_no_int,
        "pct_intersectan": round(pct_global_int, 1),
        "pct_no_intersectan": round(pct_global_no_int, 1),
        "dist_min": round(g_min, 2),
        "dist_avg": round(g_avg, 2),
        "dist_max": round(g_max, 2)
    }
    
    return df_results, df_summary, df_non_intersected, global_kpis

def classify_distance_ranges(
    df_non_intersected: pd.DataFrame,
    custom_bins: Optional[List[float]] = None,
    custom_labels: Optional[List[str]] = None
) -> pd.DataFrame:
    """Clasifica los elementos no intersectados en rangos de distancia configurables."""
    if df_non_intersected is None or df_non_intersected.empty:
        return pd.DataFrame(columns=["rango_distancia", "cantidad", "porcentaje"])
        
    bins = custom_bins or DEFAULT_DISTANCE_BINS
    labels = custom_labels or DEFAULT_BIN_LABELS
    
    df_copy = df_non_intersected.copy()
    df_copy["rango_distancia"] = pd.cut(
        df_copy["distancia_m"],
        bins=bins,
        labels=labels,
        include_lowest=True
    )
    
    counts = df_copy["rango_distancia"].value_counts().reindex(labels, fill_value=0).reset_index()
    counts.columns = ["rango_distancia", "cantidad"]
    total = counts["cantidad"].sum()
    counts["porcentaje"] = ((counts["cantidad"] / total) * 100.0).round(1) if total > 0 else 0.0
    
    return counts
