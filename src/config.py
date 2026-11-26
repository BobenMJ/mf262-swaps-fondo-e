# -*- coding: utf-8 -*-
"""Parámetros del proyecto: rutas, ventanas de fechas y fuentes de datos.

Todo lo que el enunciado fija (fechas, madureces, AFP asignada) vive aquí para
que el resto del código no tenga números sueltos.
"""
from pathlib import Path

# --- Rutas (relativas a la raíz del proyecto) --------------------------------
RAIZ = Path(__file__).resolve().parents[1]
DATA_RAW = RAIZ / "data" / "raw"
DATA_PROC = RAIZ / "data" / "processed"
OUT_FIG = RAIZ / "output" / "figuras"
OUT_TAB = RAIZ / "output" / "tablas"

RAW_FRED = DATA_RAW / "fred" / "cmt_diario.csv"
RAW_FED = DATA_RAW / "fed" / "feds200628.csv"
RAW_SP_CUOTAS = DATA_RAW / "sp" / "vcfE_2023-2026.csv"
RAW_SP_MONETARIOS = DATA_RAW / "sp" / "valores_monetarios"   # un AAAA-MM.html por mes
RAW_BDE = DATA_RAW / "siid_bde"                               # un <codigo>.html por cuadro
RAW_CARTERAS = DATA_RAW / "sp_carteras"                       # descarga manual (reCAPTCHA)
REGISTRO_DESCARGAS = DATA_RAW / "registro_descargas.csv"

# --- Grupo ---------------------------------------------------------------------
AFP = "CAPITAL"   # ID 0 según la suma de dígitos verificadores (mod 7)
FONDO = "E"

# --- Ventanas del enunciado --------------------------------------------------
CMT_INICIO = "2016-10-01"        # Módulo I: octubre 2016 ...
CMT_FIN = "2026-09-30"           # ... a septiembre 2026
CIERRE_ANALISIS = "2026-09-30"   # cierre de todo el análisis
BASE_RENTABILIDAD = "2025-12-31" # P8: base de las rentabilidades acumuladas
FECHAS_SVENPY = ["2023-12", "2024-12", "2025-12", "2026-09"]  # P7: último día hábil de cada mes

# --- Módulo I: series CMT de FRED (código -> madurez en años) ---------------
SERIES_CMT = {
    "DGS1MO": 1 / 12,
    "DGS3MO": 3 / 12,
    "DGS6MO": 6 / 12,
    "DGS1": 1.0,
    "DGS2": 2.0,
    "DGS3": 3.0,
    "DGS5": 5.0,
    "DGS7": 7.0,
    "DGS10": 10.0,
    "DGS20": 20.0,
    "DGS30": 30.0,
}

# --- Fuentes (URL usadas por scripts/descargar_datos.py) --------------------
URL_FED_GSW = "https://www.federalreserve.gov/data/yield-curve-tables/feds200628.csv"

URL_SP_VC = "https://www.spensiones.cl/apps/valoresCuotaFondo/vcfAFP.php"
URL_SP_VC_CSV = "https://www.spensiones.cl/apps/valoresCuotaFondo/vcfAFPxls.php"
SP_VC_ANIO_INI = 2023
SP_VC_ANIO_FIN = 2026

URL_SP_MONETARIOS = "https://www.spensiones.cl/apps/vMonetarios.php"
SP_MONETARIOS_INI = (2023, 12)   # (año, mes) inclusive
SP_MONETARIOS_FIN = (2026, 9)

# Estadísticas del SIID para Fondos de Pensiones, publicadas en la Base de Datos
# Estadísticos (BDE) del Banco Central. Unidad: millones de USD, fin de mes.
URL_BDE = "https://si3.bcentral.cl/Siete/ES/Siete/Cuadro/CAP_DERYSPOT/MN_DERYSPOT"
CUADROS_BDE = {
    # Montos vigentes totales en derivados por tipo de subyacente (P9)
    "DER_RES_POS_02": URL_BDE + "/DER_RES_POS_02/638670943827780640",
    # Swaps de tasas de interés extranjeras: total, compra, venta y neto (P9 y P12)
    "DER_TAS_FP_STO_01": URL_BDE + "/DER_TAS_FP_STO_01/638690071945166200",
}
BDE_PARAMS = {
    "cbFechaInicio": "2022",
    "cbFechaTermino": "2026",
    "cbFrecuencia": "MONTHLY",
    "cbCalculo": "NONE",
    "cbFechaBase": "",
}
BDE_ULTIMO_MES = "Sep.2026"   # etiqueta que debe aparecer en el cuadro descargado

# Series del cuadro DER_TAS_FP_STO_01. OJO: el SIID habla de tasa VARIABLE.
# Comprar tasa variable = pagar fija = "venta fija" del enunciado, y viceversa.
BDE_SWAP_EXT_TOTAL = "F099.DER.STO.Z.42.Z.Z.TOT.SWP.MMUSD.EXT.Z.Z.0.M"
BDE_SWAP_EXT_COMPRA_VARIABLE = "F099.DER.STO.Z.42.Z.Z.COM.SWP.MMUSD.EXT.Z.Z.0.M"  # = venta fija
BDE_SWAP_EXT_VENTA_VARIABLE = "F099.DER.STO.Z.42.Z.Z.VTA.SWP.MMUSD.EXT.Z.Z.0.M"   # = compra fija
BDE_SWAP_EXT_NETO_VARIABLE = "F099.DER.STO.Z.42.Z.Z.NET.SWP.MMUSD.EXT.Z.Z.0.M"

URL_SP_BASES = "https://www.spensiones.cl/portal/institucional/594/w3-propertyname-621.html"

# --- Módulo II: carteras históricas -------------------------------------------
ZIP_CARTERAS = RAW_CARTERAS / "chistAFP.zip"
AFP_CODIGO = "cap"                      # código de AFP Capital en las carteras
DESCRIPTOR_SWAP = "SFRUS$360"           # swaps SOFR en dólares
CARTERAS_DESDE = "2024-01"              # P11: desde enero de 2024
# Extractos de las carteras (lo único de la base de la SP que se distribuye con el proyecto)
EXTRACTO_FONDO = DATA_PROC / "swaps_sofr_fondo_e_capital.csv"
EXTRACTO_SISTEMA = DATA_PROC / "swaps_sofr_sistema_agregado.csv"
TRAMOS = {"3m": 0.25, "6m": 0.5, "9m": 0.75, "12m": 1.0, "18m": 1.5, "2y": 2.0, "5y": 5.0, "10y": 10.0}
