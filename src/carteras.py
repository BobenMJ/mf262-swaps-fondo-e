# -*- coding: utf-8 -*-
"""Carteras históricas de la SP: extracción y lectura de los swaps SOFR en dólares.

La base completa (chistAFP.zip, 117 MB) no se distribuye con el proyecto. Si está en
data/raw/sp_carteras/, `extraer()` regenera dos extractos en data/processed/:
  - swaps_sofr_fondo_e_capital.csv: registros originales del Fondo E de AFP Capital;
  - swaps_sofr_sistema_agregado.csv: nocionales por fecha, AFP, fondo y sentido (control).
Si el ZIP no está, el resto del código trabaja con los extractos ya incluidos.
"""
from __future__ import annotations

import zipfile

import numpy as np
import pandas as pd

from . import config

COL_FONDO = "tasa_pactada_del_fondo_swap"
COL_CONTRA = "tasa_pactada_de_la_contraparte_swap"


def extraer(forzar=False):
    """Genera los extractos desde el ZIP de la SP. Devuelve True si los (re)generó."""
    if not config.ZIP_CARTERAS.exists():
        return False
    if (config.EXTRACTO_FONDO.exists() and config.EXTRACTO_SISTEMA.exists() and not forzar
            and config.EXTRACTO_FONDO.stat().st_mtime >= config.ZIP_CARTERAS.stat().st_mtime):
        return False
    partes = []
    with zipfile.ZipFile(config.ZIP_CARTERAS) as z:
        for nombre in sorted(z.namelist()):
            if int(nombre[-8:-4]) < int(config.CARTERAS_DESDE[:4]):
                continue
            with z.open(nombre) as f:
                for trozo in pd.read_csv(f, sep=";", dtype=str, keep_default_na=False,
                                         encoding="latin-1", chunksize=400000):
                    es_swap = (trozo[COL_FONDO].str.contains(config.DESCRIPTOR_SWAP, regex=False)
                               | trozo[COL_CONTRA].str.contains(config.DESCRIPTOR_SWAP, regex=False))
                    partes.append(trozo[es_swap])
    swaps = pd.concat(partes, ignore_index=True)
    swaps = swaps[swaps["fecha"] <= config.CIERRE_ANALISIS.replace("-", "")]

    config.DATA_PROC.mkdir(parents=True, exist_ok=True)
    fondo = swaps[(swaps["afp"] == config.AFP_CODIGO) & (swaps["tipo_de_fondo"] == config.FONDO)]
    fondo.to_csv(config.EXTRACTO_FONDO, sep=";", index=False)

    swaps = swaps.assign(sentido=np.where(swaps[COL_CONTRA].str.startswith("FIJA"), "compra_fija", "venta_fija"),
                         nocional_usd=swaps["unidades"].astype(float))
    agregado = (swaps.groupby(["fecha", "afp", "tipo_de_fondo", "sentido"])["nocional_usd"]
                .agg(["sum", "size"]).rename(columns={"sum": "nocional_usd", "size": "contratos"}).reset_index())
    agregado.to_csv(config.EXTRACTO_SISTEMA, index=False)
    return True


def tramo_mas_cercano(residual):
    """Tramo de plazo residual más cercano (años); en caso de empate, el mayor."""
    nombres, valores = list(config.TRAMOS), np.array(list(config.TRAMOS.values()))
    dist = np.abs(np.asarray(residual, dtype=float)[:, None] - valores[None, :])
    idx = dist.shape[1] - 1 - np.argmin(dist[:, ::-1], axis=1)   # el último mínimo = tramo mayor
    return np.array(nombres)[idx]


def cargar_swaps_fondo():
    """Contratos swap SOFR del Fondo E de AFP Capital, uno por fila y por cartera mensual.

    Sentido: si la contraparte paga tasa fija, el fondo recibe fija y paga SOFR (compra fija);
    si es el fondo el que paga fija, es una venta fija.
    El nemotécnico es <contraparte:3>US$<vencimiento:aammdd><inicio:aammdd>.
    """
    t = pd.read_csv(config.EXTRACTO_FONDO, sep=";", dtype=str, keep_default_na=False)
    fija_contra = t[COL_CONTRA].str.startswith("FIJA")
    fija_fondo = t[COL_FONDO].str.startswith("FIJA")
    if not (fija_contra ^ fija_fondo).all():
        raise ValueError("Hay swaps que no son fijo contra SOFR")
    nemo = t["nemotecnico_del_instrumento"]
    tasa = np.where(fija_contra, t[COL_CONTRA], t[COL_FONDO])
    out = pd.DataFrame({
        "fecha": pd.to_datetime(t["fecha"], format="%Y%m%d"),
        "nemotecnico": nemo,
        "contraparte": t["nombre_del_emisor"],
        "nacionalidad": np.where(t["nacionalidad_del_emisor"] == "E", "Extranjera", "Nacional"),
        "sentido": np.where(fija_contra, "compra_fija", "venta_fija"),
        "nocional_usd": t["unidades"].astype(float),
        "vencimiento": pd.to_datetime("20" + nemo.str[6:12], format="%Y%m%d"),
        "inicio": pd.to_datetime("20" + nemo.str[12:18], format="%Y%m%d", errors="coerce"),
        "tasa_fija": pd.Series(tasa).str.extract(r"FIJAUS\$\+(\d+,\d+)")[0].str.replace(",", ".").astype(float),
        "valor_clp": t["inversion"].astype(float),
    })
    out["mes"] = out["fecha"].dt.to_period("M")
    out["residual"] = (out["vencimiento"] - out["fecha"]).dt.days / 365.25
    out["tramo"] = tramo_mas_cercano(out["residual"])
    out["anio_madurez"] = out["vencimiento"].dt.year
    return out.sort_values(["fecha", "sentido", "vencimiento"]).reset_index(drop=True)


def cargar_sistema():
    t = pd.read_csv(config.EXTRACTO_SISTEMA, dtype={"fecha": str})
    t["mes"] = pd.to_datetime(t["fecha"], format="%Y%m%d").dt.to_period("M")
    return t
