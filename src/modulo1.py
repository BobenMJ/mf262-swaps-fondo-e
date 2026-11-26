# -*- coding: utf-8 -*-
"""Módulo I: estructura de tasas en dólares con Nelson y Siegel sobre las CMT (P2 a P7).

Especificación del enunciado (m y tau en años, y en %):
    y(m) = b0 + b1 * (1 - e^(-m/tau)) / (m/tau)
              + b2 * [ (1 - e^(-m/tau)) / (m/tau) - e^(-m/tau) ]
Las CMT son tasas al valor par, así que la curva ajustada es una curva par.
tau es único para toda la muestra; b0, b1 y b2 se estiman cada mes por MCO.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import config, datos
from .graficos import AMARILLO, AZUL, NARANJA, TEXTO_2, VERDE, guardar, plt

TAU_VALIDACION = 1.0
GRILLA_TAU = np.round(np.arange(0.05, 15.0001, 0.001), 3)   # años
REPRESENTATIVAS = {"DGS3MO": "Corto plazo: 3 meses", "DGS5": "Mediano plazo: 5 años",
                   "DGS10": "Largo plazo: 10 años"}          # P3


def factores(m, tau):
    """Matriz de regresores [1, pendiente, curvatura] para madureces m (años)."""
    x = np.asarray(m, dtype=float) / tau
    f1 = (1 - np.exp(-x)) / x
    return np.column_stack([np.ones_like(x), f1, f1 - np.exp(-x)])


def ajustar(tasas, tau):
    """MCO mes a mes para un tau dado. Devuelve (betas [meses x 3], SCR por mes)."""
    X = factores(list(config.SERIES_CMT.values()), tau)
    Y = tasas.to_numpy(dtype=float)                      # meses x madureces
    betas = np.linalg.lstsq(X, Y.T, rcond=None)[0].T     # meses x 3
    residuos = Y - betas @ X.T
    return betas, (residuos ** 2).sum(axis=1)


def curva(betas, m, tau):
    return factores(m, tau) @ np.asarray(betas, dtype=float)


def ejecutar():
    tab, fig = config.OUT_TAB, config.OUT_FIG
    tab.mkdir(parents=True, exist_ok=True)
    resumen = {}

    # P2: último dato disponible de cada mes -------------------------------
    tasas = datos.ultimo_dato_del_mes(datos.cargar_cmt_diario())
    tasas.index.name = "fecha"
    tasas.to_csv(tab / "p2_cmt_mensual.csv", float_format="%.2f")
    resumen["meses"], resumen["madureces"], resumen["n_obs"] = tasas.shape[0], tasas.shape[1], tasas.size

    # P3: corto, mediano y largo plazo --------------------------------------
    f, ax = plt.subplots(figsize=(8, 4))
    for (codigo, etiqueta), color in zip(REPRESENTATIVAS.items(), [AZUL, NARANJA, VERDE]):
        ax.plot(tasas.index, tasas[codigo], color=color, label=etiqueta)
    ax.set_title("Tasas CMT de corto, mediano y largo plazo (fin de mes)")
    ax.set_ylabel("Tasa (%)")
    ax.legend(loc="upper left")
    f.text(0.01, -0.02, "Fuente: FRED, tasas Constant Maturity Treasury. Octubre 2016 a septiembre 2026.",
           fontsize=8, color=TEXTO_2)
    guardar(f, fig / "p3_tasas_representativas.png")

    # P4: validación con tau = 1 --------------------------------------------
    _, scr_1 = ajustar(tasas, TAU_VALIDACION)
    resumen["scr_tau_1"] = float(scr_1.sum())

    # P5: tau óptimo por grilla ---------------------------------------------
    scr_grilla = np.array([ajustar(tasas, t)[1].sum() for t in GRILLA_TAU])
    i = int(scr_grilla.argmin())
    tau_opt = float(GRILLA_TAU[i])
    resumen["tau_optimo"], resumen["scr_minimo"] = tau_opt, float(scr_grilla[i])
    pd.DataFrame({"tau": GRILLA_TAU, "scr_total": scr_grilla}).to_csv(
        tab / "p5_grilla_tau.csv", index=False, float_format="%.6f")
    pd.DataFrame([
        {"caso": "P4: tau = 1", "tau": TAU_VALIDACION, "scr_total_pp2": resumen["scr_tau_1"], "n_obs": tasas.size},
        {"caso": "P5: tau óptimo", "tau": tau_opt, "scr_total_pp2": resumen["scr_minimo"], "n_obs": tasas.size},
    ]).to_csv(tab / "p4_p5_ajuste.csv", index=False, float_format="%.6f")

    f, ax = plt.subplots(figsize=(8, 4))
    ax.plot(GRILLA_TAU, scr_grilla, color=AZUL)
    ax.scatter([tau_opt], [scr_grilla[i]], color=NARANJA, s=50, zorder=3)
    ax.annotate("mínimo: τ = {:.3f}\nSCR = {:.2f}".format(tau_opt, scr_grilla[i]).replace(".", ","),
                (tau_opt, scr_grilla[i]), xytext=(25, 35), textcoords="offset points",
                arrowprops={"arrowstyle": "-", "color": TEXTO_2})
    ax.set_title("Suma total de cuadrados de los residuos según τ")
    ax.set_xlabel("τ (años)")
    ax.set_ylabel("SCR total (puntos porcentuales²)")
    ax.set_ylim(0, min(scr_grilla.max(), 6 * scr_grilla[i]))
    guardar(f, fig / "p5_scr_por_tau.png")

    # P6: evolución de los parámetros ---------------------------------------
    betas, scr_mes = ajustar(tasas, tau_opt)
    par = pd.DataFrame(betas, index=tasas.index, columns=["beta0", "beta1", "beta2"])
    par["scr"] = scr_mes
    par.to_csv(tab / "p6_betas.csv", float_format="%.6f")
    f, ejes = plt.subplots(3, 1, figsize=(8, 7), sharex=True)
    for ax, col, titulo, color in zip(ejes, ["beta0", "beta1", "beta2"],
                                      ["β₀: nivel", "β₁: pendiente", "β₂: curvatura"],
                                      [AZUL, NARANJA, VERDE]):
        ax.plot(par.index, par[col], color=color)
        ax.axhline(0, color=TEXTO_2, linewidth=0.8)
        ax.set_title(titulo, loc="left")
        ax.set_ylabel("%")
    f.suptitle("Parámetros de Nelson y Siegel, τ = {:.3f} años".format(tau_opt).replace(".", ","),
               fontweight="bold")
    f.tight_layout()
    guardar(f, fig / "p6_betas.png")

    # P7: comparación con las SVENPY de la Fed -------------------------------
    gsw = datos.cargar_gsw()
    plazos = np.arange(1, 31)
    cols = ["SVENPY{:02d}".format(k) for k in plazos]
    fino = np.linspace(1 / 12, 30, 300)
    filas = []
    f, ejes = plt.subplots(2, 2, figsize=(10, 7), sharey=True)
    for ax, mes in zip(ejes.ravel(), config.FECHAS_SVENPY):
        fecha = par.loc[mes].index[-1]                     # último día hábil del mes (el de las CMT)
        fed = gsw.loc[fecha, cols].astype(float).to_numpy()
        propia = curva(par.loc[fecha, ["beta0", "beta1", "beta2"]], plazos, tau_opt)
        for k, a, b in zip(plazos, propia, fed):
            filas.append({"fecha": fecha.date(), "madurez_anios": k, "ns_propia": a, "svenpy_fed": b, "diferencia_pb": 100 * (a - b)})
        ax.plot(fino, curva(par.loc[fecha, ["beta0", "beta1", "beta2"]], fino, tau_opt), color=AZUL,
                label="Nelson y Siegel propia")
        ax.plot(plazos, fed, color=NARANJA, linestyle="--", label="SVENPY (Fed, Svensson)")
        ax.scatter(list(config.SERIES_CMT.values()), tasas.loc[fecha], color=TEXTO_2, s=18, zorder=3,
                   label="CMT observadas")
        ax.set_title("{:%d-%m-%Y}".format(fecha), loc="left")
    for ax in ejes[-1]:
        ax.set_xlabel("Madurez (años)")
    for ax in ejes[:, 0]:
        ax.set_ylabel("Tasa par (%)")
    ejes[0, 0].legend(loc="lower right", fontsize=8)
    f.suptitle("Curva par estimada y curva par de la Reserva Federal", fontweight="bold")
    f.tight_layout()
    guardar(f, fig / "p7_comparacion_svenpy.png")
    comp = pd.DataFrame(filas)
    comp.to_csv(tab / "p7_comparacion_svenpy.csv", index=False, float_format="%.4f")
    resumen["p7_dif_abs_media_pb"] = comp.groupby("fecha")["diferencia_pb"].apply(lambda s: s.abs().mean()).round(1).to_dict()
    resumen["p7_dif_max_pb"] = comp.loc[comp["diferencia_pb"].abs().idxmax(), ["fecha", "madurez_anios", "diferencia_pb"]].to_dict()

    _tablas_latex(tasas, par, comp, resumen)
    par.attrs["tau"] = tau_opt
    return resumen, par


def _es(x, dec=2):
    """Número con coma decimal y punto de miles, para el informe."""
    return "{:,.{}f}".format(x, dec).replace(",", "X").replace(".", ",").replace("X", ".")


def _tablas_latex(tasas, par, comp, r):
    """Fragmentos .tex que el informe incluye con \\input (cifras siempre sincronizadas)."""
    tab = config.OUT_TAB
    nombres = {"DGS1MO": "1m", "DGS3MO": "3m", "DGS6MO": "6m", "DGS1": "1a", "DGS2": "2a", "DGS3": "3a",
               "DGS5": "5a", "DGS7": "7a", "DGS10": "10a", "DGS20": "20a", "DGS30": "30a"}
    fin = " \\\\\n"

    # Cifras sueltas usadas en el texto
    macros = {"MIobs": _es(r["n_obs"], 0), "MImeses": str(r["meses"]), "MImadureces": str(r["madureces"]),
              "MIscrUno": _es(r["scr_tau_1"], 4), "MItau": _es(r["tau_optimo"], 3), "MIscrMin": _es(r["scr_minimo"], 4),
              "MIbetaCeroMin": _es(par["beta0"].min()), "MIbetaCeroMax": _es(par["beta0"].max()),
              "MIbetaCeroFin": _es(par["beta0"].iloc[-1])}
    (tab / "m1_macros.tex").write_text(
        "".join("\\newcommand{{\\{}}}{{{}}}\n".format(k, v) for k, v in macros.items()), encoding="utf-8")

    # P2: extracto de la tabla de tasas
    filas = ["Fecha & " + " & ".join(nombres[c] for c in tasas.columns) + fin + "\\midrule\n"]
    extracto = pd.concat([tasas.head(3), tasas.tail(3)])
    for i, (fecha, fila) in enumerate(extracto.iterrows()):
        if i == 3:
            filas.append("$\\vdots$ & " + " & ".join(["$\\vdots$"] * tasas.shape[1]) + fin)
        filas.append("{:%d-%m-%Y} & ".format(fecha) + " & ".join(_es(v) for v in fila) + fin)
    (tab / "p2_extracto.tex").write_text("".join(filas), encoding="utf-8")

    # P4 y P5: ajuste
    (tab / "p4_p5_ajuste.tex").write_text(
        "$\\tau = 1$ (validación, P4) & {} & {} & {}".format(_es(1, 3), _es(r["scr_tau_1"], 4), _es(r["n_obs"], 0)) + fin
        + "$\\tau$ óptimo (P5) & {} & {} & {}".format(_es(r["tau_optimo"], 3), _es(r["scr_minimo"], 4), _es(r["n_obs"], 0)) + fin,
        encoding="utf-8")

    # P7: diferencias con las SVENPY en madureces seleccionadas
    sel = [1, 2, 5, 10, 20, 30]
    filas = []
    for fecha, g in comp.groupby("fecha"):
        g = g.set_index("madurez_anios")
        filas.append("{:%d-%m-%Y} & ".format(pd.Timestamp(fecha))
                     + " & ".join(_es(g.loc[k, "diferencia_pb"], 1).replace("-", "$-$") for k in sel)
                     + " & {}".format(_es(g["diferencia_pb"].abs().mean(), 1)) + fin)
    (tab / "p7_diferencias.tex").write_text("".join(filas), encoding="utf-8")
