"""
Módulo de utilidades auxiliares, formateo y registro de errores.
"""
import time
import logging
import traceback
from typing import Dict, Any

# Configuración básica de logger
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("GIS_App")

def format_meters(val: float) -> str:
    """Formatea distancias en metros con unidades legibles."""
    if val is None or val < 0:
        return "N/A"
    if val >= 1000:
        return f"{val / 1000:.2f} km"
    return f"{val:.2f} m"

def format_percentage(val: float) -> str:
    """Formatea porcentajes."""
    if val is None:
        return "0.0%"
    return f"{val:.1f}%"

def log_error(file_path: str, error: Exception) -> Dict[str, Any]:
    """Genera un registro estructurado de error para el reporte."""
    error_msg = str(error)
    tb = traceback.format_exc()
    logger.error(f"Error procesando {file_path}: {error_msg}")
    return {
        "archivo": file_path,
        "tipo_error": type(error).__name__,
        "mensaje": error_msg,
        "traceback": tb
    }
