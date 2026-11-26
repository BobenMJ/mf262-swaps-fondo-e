# -*- coding: utf-8 -*-
"""Lectura de los datos originales guardados en data/raw/ (no usa internet).

Cada función lee un archivo tal como lo entrega su fuente y devuelve un
DataFrame de pandas listo para usar. Los formatos están descritos en
docs/supuestos.md.
"""
from __future__ import annotations

import re
from pathlib import Path

import numpy as np
import pandas as pd

from . import config

MESES_ES = {"Ene": 1, "Feb": 2, "Mar": 3, "Abr": 4, "May": 5, "Jun": 6,
            "Jul": 7, "Ago": 8, "Sep": 9, "Oct": 10, "Nov": 11, "Dic": 12}


def numero_cl(texto):
    """Convierte un número con formato chileno ('$ 40.875,09', '-16.333') a float."""
    t = re.sub(r"<[^>]+>", "", str(texto)).replace("&nbsp;", " ").replace("\xa0", " ")
    t = t.replace("$", "").strip()
    if t in ("", "-", "ND", "N.D.", "n.d."):
        return np.nan
    return float(t.replace(".", "").replace(",", "."))


# ----------------------------------------------------------------------------
# Módulo I
# ----------------------------------------------------------------------------
def cargar_cmt_diario(ruta=None):
    """Tasas CMT diarias de FRED, en porcentaje. Índice: fecha; columnas: códigos DGS."""
    tabla = pd.read_csv(ruta or config.RAW_FRED, index_col="fecha", parse_dates=True)
    return tabla[list(config.SERIES_CMT)].sort_index()


def cargar_gsw(ruta=None):
    """Curva de Gürkaynak, Sack y Wright (Fed). Incluye las columnas SVENPY01..SVENPY30."""
    ruta = Path(ruta or config.RAW_FED)
    with open(ruta, encoding="utf-8", errors="replace") as f:
        for n, linea in enumerate(f):
            if linea.startswith("Date,"):
                break
        else:
            raise ValueError("No encontré el encabezado 'Date,' en {}".format(ruta))
    tabla = pd.read_csv(ruta, skiprows=n, index_col="Date", parse_dates=True, na_values=["NA"])
    return tabla.sort_index()


# ----------------------------------------------------------------------------
# Módulo II
# ----------------------------------------------------------------------------
def cargar_valores_cuota(ruta=None):
    """Valor cuota y patrimonio diarios del Fondo E, todas las AFP (formato largo).

    El CSV de la SP viene en bloques (uno por año de valores confirmados y uno
    final de valores provisorios), cada uno con su propio encabezado de AFP.
    Columnas: fecha, afp, valor_cuota ($), patrimonio ($), confirmado (bool).
    """
    ruta = Path(ruta or config.RAW_SP_CUOTAS)
    afps, confirmado, filas = [], True, []
    for linea in ruta.read_text(encoding="latin-1").splitlines():
        if linea.startswith("Valores"):
            confirmado = "Confirmados" in linea
        elif linea.startswith("Fecha;"):
            afps = [x.strip() for x in linea.split(";")[1:] if x.strip()]
        elif re.match(r"\d{4}-\d{2}-\d{2};", linea):
            partes = linea.split(";")
            for i, afp in enumerate(afps):
                if 2 + 2 * i < len(partes):
                    filas.append((partes[0], afp, numero_cl(partes[1 + 2 * i]),
                                  numero_cl(partes[2 + 2 * i]), confirmado))
    tabla = pd.DataFrame(filas, columns=["fecha", "afp", "valor_cuota", "patrimonio", "confirmado"])
    tabla["fecha"] = pd.to_datetime(tabla["fecha"])
    tabla = tabla.drop_duplicates(["fecha", "afp"], keep="first")
    return tabla.sort_values(["afp", "fecha"]).reset_index(drop=True)


def cargar_fondo(afp=None, ruta=None):
    """Valor cuota y patrimonio diarios de una AFP (por defecto, la asignada). Índice: fecha."""
    tabla = cargar_valores_cuota(ruta)
    afp = afp or config.AFP
    sub = tabla[tabla["afp"] == afp].set_index("fecha")[["valor_cuota", "patrimonio", "confirmado"]]
    if sub.empty:
        raise ValueError("La AFP {} no aparece en el archivo de valores cuota".format(afp))
    return sub


def cargar_monetarios(carpeta=None):
    """UF y dólar diarios publicados por la SP. Índice: fecha; columnas: dolar, uf (en $)."""
    carpeta = Path(carpeta or config.RAW_SP_MONETARIOS)
    archivos = sorted(carpeta.glob("????-??.html"))
    if not archivos:
        raise FileNotFoundError("No hay archivos AAAA-MM.html en {}".format(carpeta))
    filas = []
    for archivo in archivos:
        anio, mes = int(archivo.stem[:4]), int(archivo.stem[5:7])
        html = archivo.read_text(encoding="latin-1")
        for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", html, flags=re.S | re.I):
            celdas = re.findall(r"<td[^>]*>(.*?)</td>", tr, flags=re.S | re.I)
            if len(celdas) >= 3 and re.fullmatch(r"\s*\d{2}\s*", celdas[0]):
                filas.append((pd.Timestamp(anio, mes, int(celdas[0])),
                              numero_cl(celdas[1]), numero_cl(celdas[2])))
    tabla = pd.DataFrame(filas, columns=["fecha", "dolar", "uf"]).set_index("fecha").sort_index()
    return tabla


def cargar_cuadro_bde(codigo, carpeta=None):
    """Cuadro mensual de la BDE (estadísticas del SIID), en millones de USD.

    Devuelve (tabla, nombres): tabla con índice = fin de mes y una columna por
    código de serie; nombres = {código: nombre de la serie en el cuadro}.
    """
    archivo = Path(carpeta or config.RAW_BDE) / (codigo + ".html")
    html = archivo.read_text(encoding="utf-8", errors="replace")
    inicio = html.find('id="grilla"')
    if inicio < 0:
        raise ValueError("{} no contiene la tabla de datos (id='grilla')".format(archivo))
    grilla = html[inicio:html.find("</table>", inicio)]

    etiquetas = [re.sub(r"<[^>]+>", "", e).strip()
                 for e in re.findall(r"<th[^>]*>(.*?)</th>", grilla, flags=re.S | re.I)]
    fechas = []
    for e in etiquetas:
        m = re.fullmatch(r"([A-Za-z]{3})\.(\d{4})", e)
        if m and m.group(1) in MESES_ES:
            fechas.append(pd.Timestamp(int(m.group(2)), MESES_ES[m.group(1)], 1) + pd.offsets.MonthEnd(0))
    if not fechas:
        raise ValueError("{}: no reconocí columnas de fecha".format(archivo))

    series, nombres = {}, {}
    for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", grilla, flags=re.S | re.I):
        cod = re.search(r'data-serie="([^"]+)"', tr)
        if not cod:
            continue
        valores = [numero_cl(v) for v in
                   re.findall(r'<td class="ar col"[^>]*>(.*?)</td>', tr, flags=re.S | re.I)]
        if len(valores) != len(fechas) or np.all(np.isnan(valores)):
            continue  # filas de título (p. ej. "Sectores") no traen datos
        nombre = re.search(r'class="sname"[^>]*>(.*?)</span>', tr, flags=re.S | re.I)
        nombres[cod.group(1)] = re.sub(r"\s+", " ", nombre.group(1).replace("&nbsp;", " ")).strip() if nombre else ""
        series[cod.group(1)] = valores
    tabla = pd.DataFrame(series, index=pd.DatetimeIndex(fechas, name="fecha"))
    return tabla, nombres


# ----------------------------------------------------------------------------
# Utilidades comunes
# ----------------------------------------------------------------------------
def ultimo_dato_del_mes(tabla):
    """Para cada mes, la fila del último día con todas las columnas informadas."""
    completas = tabla.dropna(how="any")
    return completas.groupby([completas.index.year, completas.index.month]).tail(1)


def estado_datos():
    """Revisa qué datos originales están disponibles. Lista de (fuente, ok, detalle)."""
    estado = []

    def revisar(nombre, funcion):
        try:
            estado.append((nombre, True, funcion()))
        except FileNotFoundError:
            estado.append((nombre, False, "falta el archivo (ejecuta scripts/descargar_datos.py)"))
        except Exception as e:
            estado.append((nombre, False, "{}: {}".format(type(e).__name__, e)))

    def _cmt():
        mensual = ultimo_dato_del_mes(cargar_cmt_diario())
        return "{} meses x {} madureces = {} observaciones ({} a {})".format(
            len(mensual), mensual.shape[1], mensual.size,
            mensual.index.min().date(), mensual.index.max().date())

    def _gsw():
        tabla = cargar_gsw()
        fila = tabla.loc[:config.CIERRE_ANALISIS].iloc[-1]
        return "hasta {}; SVENPY10 al {} = {:.4f}%".format(
            tabla.index.max().date(), fila.name.date(), fila["SVENPY10"])

    def _cuotas():
        fondo = cargar_fondo()
        a = fondo.loc[pd.Timestamp(config.BASE_RENTABILIDAD)]
        b = fondo.loc[pd.Timestamp(config.CIERRE_ANALISIS)]
        return "AFP {} Fondo {}: valor cuota {:,.2f} ({}) -> {:,.2f} ({}), nominal {:+.2%}".format(
            config.AFP, config.FONDO, a["valor_cuota"], config.BASE_RENTABILIDAD,
            b["valor_cuota"], config.CIERRE_ANALISIS, b["valor_cuota"] / a["valor_cuota"] - 1)

    def _monetarios():
        tabla = cargar_monetarios()
        a = tabla.loc[pd.Timestamp(config.BASE_RENTABILIDAD)]
        b = tabla.loc[pd.Timestamp(config.CIERRE_ANALISIS)]
        return "UF {:,.2f} -> {:,.2f} ({:+.2%}); dólar al cierre {:,.2f}".format(
            a["uf"], b["uf"], b["uf"] / a["uf"] - 1, b["dolar"])

    def _bde():
        swaps, _ = cargar_cuadro_bde("DER_TAS_FP_STO_01")
        resumen, _ = cargar_cuadro_bde("DER_RES_POS_02")
        ultima = swaps.iloc[-1]
        return ("hasta {:%Y-%m}; swaps tasas extranjeras FP: compra variable {:,.0f}, venta variable "
                "{:,.0f} MMUSD; {} series de resumen").format(
                    swaps.index.max(), ultima[config.BDE_SWAP_EXT_COMPRA_VARIABLE],
                    ultima[config.BDE_SWAP_EXT_VENTA_VARIABLE], resumen.shape[1])

    def _carteras():
        archivos = [p.name for p in config.RAW_CARTERAS.glob("*")
                    if p.is_file() and p.name.upper() not in ("LEEME.TXT", ".GITKEEP", ".DS_STORE")]
        if not archivos:
            raise FileNotFoundError
        return ", ".join(sorted(archivos))

    revisar("CMT (FRED)", _cmt)
    revisar("Curva GSW (Fed)", _gsw)
    revisar("Valor cuota (SP)", _cuotas)
    revisar("UF y dólar (SP)", _monetarios)
    revisar("SIID (BDE)", _bde)
    try:
        estado.append(("Carteras (SP)", True, _carteras()))
    except FileNotFoundError:
        estado.append(("Carteras (SP)", False, "falta la descarga manual (ver README, sección Datos)"))
    return estado
