# -*- coding: utf-8 -*-
"""Módulo III: PV01, mark-to-market y contribución de los swaps (P17 a P20).

Valorización (supuestos en docs/supuestos.md):
  - Un swap en que el fondo recibe fija equivale a comprar un bono de tasa fija y vender uno
    de tasa flotante por el mismo nocional. La pata flotante (SOFR) vale par, de modo que
        V = N * [precio limpio del bono fijo - 1],
    con signo contrario si el fondo paga fija.
  - Pata fija: cupón anual con base ACT/360 (tasa pactada * 365/360), pagado en los
    aniversarios del vencimiento; los contratos de hasta un año pagan una sola vez, al vencer.
  - Descuento: todos los flujos de un contrato se descuentan a la tasa par de Nelson y Siegel
    (módulo I) correspondiente a su plazo residual, llevada a composición anual.
  - Se usan precios limpios: el interés devengado se excluye (el mark-to-market no incluye carry).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import config, datos, modulo1, modulo2
from .formato import FIN, es, macros, pct, tex
from .graficos import AZUL, NARANJA, SUPERFICIE, TEXTO, TEXTO_2, VERDE, guardar, plt

PB = 0.01  # un punto base, en puntos porcentuales


def tasa_par(betas, tau, plazo):
    """Tasa par anual efectiva (decimal) para un plazo residual en años."""
    plazo = np.maximum(np.asarray(plazo, dtype=float), 1 / 12)      # la curva parte en 1 mes
    bey = modulo1.curva(betas, plazo, tau) / 100                     # semestral, como las CMT
    return (1 + bey / 2) ** 2 - 1


def valor_unitario(tasa_fija, residual, plazo_original, y):
    """Valor limpio, por dólar de nocional, de RECIBIR fija. Vectorizado sobre contratos.

    tasa_fija en %, residual y plazo_original en años, y = tasa de descuento anual (decimal).
    """
    c = np.asarray(tasa_fija, dtype=float) / 100 * 365 / 360
    T = np.asarray(residual, dtype=float)
    L = np.asarray(plazo_original, dtype=float)
    y = np.asarray(y, dtype=float)
    valor = np.zeros_like(T)
    vivo = T > 0
    # Contratos de hasta un año: un solo pago de intereses al vencimiento
    corto = vivo & (L <= 1.0 + 1e-9)
    valor[corto] = (1 + c[corto] * L[corto]) / (1 + y[corto]) ** T[corto] - c[corto] * (L[corto] - T[corto]) - 1
    # Contratos largos: cupones anuales en los aniversarios del vencimiento
    for i in np.where(vivo & ~corto)[0]:
        tiempos = np.arange(T[i], 0, -1.0)[::-1]                    # T-n, ..., T-1, T
        devengado = c[i] * (1 - tiempos[0])
        sucio = (c[i] / (1 + y[i]) ** tiempos).sum() + 1 / (1 + y[i]) ** T[i]
        valor[i] = sucio - devengado - 1
    return valor


def valorizar(contratos, fecha, betas, tau, desplazamiento_pb=0.0):
    """Valor en USD de un conjunto de contratos en `fecha` (positivo = a favor del fondo)."""
    residual = (contratos["vencimiento"] - fecha).dt.days.to_numpy() / 365.25
    original = ((contratos["vencimiento"] - contratos["inicio"]).dt.days / 365.25).fillna(np.inf).to_numpy()
    y = tasa_par(betas, tau, residual) + desplazamiento_pb / 10000
    signo = np.where(contratos["sentido"] == "compra_fija", 1.0, -1.0)
    return signo * contratos["nocional_usd"].to_numpy() * valor_unitario(contratos["tasa_fija"], residual, original, y)


def cargar_contratos():
    t = pd.read_csv(config.DATA_PROC / "posiciones_contratos.csv",
                    parse_dates=["fecha", "vencimiento", "inicio", "fecha_valor"])
    t["mes"] = pd.PeriodIndex(t["mes"], freq="M")
    # Meses estimados: se mantienen las duraciones de la cartera base (P12), es decir,
    # las fechas de los contratos se desplazan junto con la fecha de la cartera.
    est = t["origen"] != "Cartera"
    corrimiento = t.loc[est, "fecha_valor"] - t.loc[est, "fecha"]
    t.loc[est, "vencimiento"] = t.loc[est, "vencimiento"] + corrimiento
    t.loc[est, "inicio"] = t.loc[est, "inicio"] + corrimiento
    return t


def ejecutar():
    tab, fig = config.OUT_TAB, config.OUT_FIG
    _, par = modulo1.ejecutar()
    tau = par.attrs["tau"]
    par = par.set_index(par.index.to_period("M"))[["beta0", "beta1", "beta2"]]
    fecha_curva = pd.Series(modulo1.datos.ultimo_dato_del_mes(datos.cargar_cmt_diario()).index)
    fecha_curva.index = fecha_curva.dt.to_period("M")
    contratos = cargar_contratos()
    origen = contratos.groupby("mes")["origen"].first()
    fecha_valor = contratos.groupby("mes")["fecha_valor"].first()
    r = {"tau": tau}

    # ---------------------------------------------------------------- P17: PV01
    base = origen[origen == "Cartera"].index.max()
    cb = contratos[contratos["mes"] == base].copy()
    fb = fecha_valor[base]
    cb["valor"] = valorizar(cb, fb, par.loc[base], tau)
    cb["pv01"] = valorizar(cb, fb, par.loc[base], tau, +1.0) - cb["valor"]      # USD por +1 pb
    pv = cb.pivot_table(index="anio_madurez", columns="sentido", values="pv01", aggfunc="sum", fill_value=0.0)
    pv = pv.reindex(columns=modulo2.SENTIDOS, fill_value=0.0)
    pv["neto"] = pv.sum(axis=1)
    noc = cb.pivot_table(index="anio_madurez", columns="sentido", values="nocional_usd", aggfunc="sum", fill_value=0.0)
    pv["nocional_neto"] = noc.get("compra_fija", 0) - noc.get("venta_fija", 0)
    pv.to_csv(tab / "p17_pv01.csv", float_format="%.0f")
    filas = ["{} & {} & {} & {} & {}".format(a, tex(x.nocional_neto / 1e6, 1), tex(x.compra_fija / 1e3, 1),
                                           tex(x.venta_fija / 1e3, 1), tex(x.neto / 1e3, 1)) + FIN for a, x in pv.iterrows()]
    filas.append("\\midrule\nTotal & {} & {} & {} & {}".format(tex(pv["nocional_neto"].sum() / 1e6, 1),
                 *[tex(pv[c].sum() / 1e3, 1) for c in ["compra_fija", "venta_fija", "neto"]]) + FIN)
    (tab / "p17_pv01.tex").write_text("".join(filas), encoding="utf-8")

    fondo, mon = datos.cargar_fondo(), datos.cargar_monetarios()
    pat_usd = fondo.loc[fb, "patrimonio"] / mon.loc[fb, "dolar"]
    pv01 = pv["neto"].sum()
    informado = pd.read_csv(config.EXTRACTO_FONDO, sep=";", dtype=str)
    informado = informado.assign(v=informado["inversion"].astype(float)).groupby("fecha")["v"].sum()
    r.update(base=base, pv01=pv01, pv01_compra=pv["compra_fija"].sum(), pv01_venta=pv["venta_fija"].sum(),
             pat_usd=pat_usd, duracion=-pv01 * 10000 / pat_usd, valor_base=cb["valor"].sum(),
             valor_base_sp=informado[fb.strftime("%Y%m%d")] / mon.loc[fb, "dolar"],
             perdida_100pb=pv01 * 100, perdida_100pb_pat=pv01 * 100 / pat_usd,
             pv01_5a10=pv.loc[(pv.index >= 2029) & (pv.index <= 2037), "neto"].sum() / pv01,
             dur_compra=-pv["compra_fija"].sum() * 10000 / noc["compra_fija"].sum(),
             dur_venta=pv["venta_fija"].sum() * 10000 / noc["venta_fija"].sum())

    f, ax = plt.subplots(figsize=(8.5, 4))
    x = np.arange(len(pv))
    ax.bar(x - 0.2, pv["compra_fija"] / 1e3, width=0.4, color=AZUL, label="Compra fija (recibe fija)")
    ax.bar(x + 0.2, pv["venta_fija"] / 1e3, width=0.4, color=NARANJA, label="Venta fija (paga fija)")
    ax.axhline(0, color=TEXTO, linewidth=0.8)
    ax.set_xticks(x); ax.set_xticklabels(pv.index, rotation=45)
    ax.set_title("PV01 por año de madurez, cartera de {}".format(modulo2.mes_largo(base)))
    ax.set_ylabel("Miles de USD por +1 punto base")
    ax.grid(axis="x", visible=False); ax.legend(fontsize=8, loc="lower right")
    guardar(f, fig / "p17_pv01.png")

    # ------------------------------------------------- P19: mark-to-market mensual
    meses = sorted(origen.index)
    filas = []
    for previo, mes in zip(meses[:-1], meses[1:]):
        c = contratos[contratos["mes"] == previo]
        v0 = valorizar(c, fecha_valor[previo], par.loc[previo], tau).sum()
        v1 = valorizar(c, fecha_valor[mes], par.loc[mes], tau).sum()
        filas.append({"mes": mes, "fecha_inicio": fecha_valor[previo], "fecha_cierre": fecha_valor[mes],
                      "valor_inicio": v0, "valor_cierre": v1, "mtm_usd": v1 - v0, "posicion": origen[previo],
                      "pv01_inicio": (valorizar(c, fecha_valor[previo], par.loc[previo], tau, 1.0).sum() - v0)})
    mtm = pd.DataFrame(filas).set_index("mes")
    mtm["mtm_acum_usd"] = mtm["mtm_usd"].cumsum()
    # Contraste: variación del valor de mercado informado por la AFP (incluye operaciones nuevas y devengo)
    inf = informado.copy(); inf.index = pd.to_datetime(inf.index).to_period("M")
    dolar_cierre = mon["dolar"].reindex(fecha_valor.reindex(inf.index).values).to_numpy()
    mtm["valor_informado_usd"] = (inf / dolar_cierre).reindex(mtm.index)
    mtm.to_csv(tab / "p19_mtm_mensual.csv", float_format="%.0f")

    f, ejes = plt.subplots(2, 1, figsize=(9, 6.2), sharex=True)
    xs = np.arange(len(mtm))
    est = (mtm["posicion"] != "Cartera").to_numpy()
    for ax in ejes:
        if est.any():
            ax.axvspan(xs[est][0] - 0.5, xs[-1] + 0.5, color="#e4e3df", zorder=0, label="Posición inicial estimada con el SIID")
    ejes[0].bar(xs, mtm["mtm_usd"] / 1e6, color=np.where(mtm["mtm_usd"] >= 0, AZUL, NARANJA), width=0.75)
    ejes[0].axhline(0, color=TEXTO, linewidth=0.8)
    ejes[0].set_title("Cambio mensual de valor (mark-to-market, sin carry)", loc="left")
    ejes[0].set_ylabel("Millones de USD"); ejes[0].grid(axis="x", visible=False); ejes[0].legend(fontsize=8, loc="lower left")
    ejes[1].plot(xs, mtm["mtm_acum_usd"] / 1e6, color=AZUL, marker="o", markersize=3)
    ejes[1].axhline(0, color=TEXTO, linewidth=0.8)
    ejes[1].set_title("Suma acumulada desde febrero de 2024", loc="left"); ejes[1].set_ylabel("Millones de USD")
    ejes[1].set_xticks(xs[::3]); ejes[1].set_xticklabels([modulo2.mes_txt(m) for m in mtm.index[::3]])
    f.suptitle("Fondo E de AFP Capital: mark-to-market de los swaps SOFR", fontweight="bold")
    f.tight_layout()
    guardar(f, fig / "p19_mtm.png")

    a25, a26 = mtm.loc["2025-01":"2025-12", "mtm_usd"].sum(), mtm.loc["2026-01":, "mtm_usd"].sum()
    r.update(mtm_total=mtm["mtm_usd"].sum(), mtm_2024=mtm.loc[:"2024-12", "mtm_usd"].sum(), mtm_2025=a25, mtm_2026=a26,
             peor=mtm["mtm_usd"].idxmin(), peor_usd=mtm["mtm_usd"].min(), mejor=mtm["mtm_usd"].idxmax(), mejor_usd=mtm["mtm_usd"].max(),
             meses_est=[m for m in mtm.index if mtm.loc[m, "posicion"] != "Cartera"],
             meses_neg_2026=int((mtm.loc["2026-01":, "mtm_usd"] < 0).sum()),
             corr_informado=np.corrcoef(mtm["mtm_usd"].iloc[:-3], mtm["valor_informado_usd"].diff().iloc[:-3].fillna(0))[0, 1],
             valor_informado_jun=mtm.loc[base, "valor_informado_usd"], valor_modelo_jun=mtm.loc[base, "valor_cierre"])

    # ------------------------------------------- P20: contribución a la rentabilidad
    rent = modulo2.rentabilidades()
    rent.index = rent.index.to_period("M")
    c20 = mtm.loc["2026-01":, ["mtm_usd", "posicion"]].copy()
    c20["dolar"] = rent["dolar"].reindex(c20.index)
    c20["mtm_clp"] = c20["mtm_usd"] * c20["dolar"]
    c20["patrimonio_inicio"] = rent["patrimonio"].shift(1).reindex(c20.index)
    c20["r_swaps"] = c20["mtm_clp"] / c20["patrimonio_inicio"]
    c20["r_swaps_acum"] = (1 + c20["r_swaps"]).cumprod() - 1
    c20["r_fondo"] = rent["rent_nominal"].reindex(c20.index)
    c20["r_fondo_acum"] = rent["acum_nominal"].reindex(c20.index)
    c20["r_resto_acum"] = (1 + c20["r_fondo_acum"]) / (1 + c20["r_swaps_acum"]) - 1
    c20.to_csv(tab / "p20_contribucion.csv", float_format="%.6f")
    filas = ["{} & {} & {} & {} & {} & {} & {} & {}".format(
        modulo2.mes_txt(m, True) + ("*" if x.posicion != "Cartera" else ""), tex(x.mtm_usd / 1e6, 1), es(x.dolar), tex(x.mtm_clp / 1e9, 1),
        es(x.patrimonio_inicio / 1e9, 0), pct(x.r_swaps), pct(x.r_swaps_acum), pct(x.r_fondo_acum)) + FIN for m, x in c20.iterrows()]
    (tab / "p20_contribucion.tex").write_text("".join(filas), encoding="utf-8")

    f, ax = plt.subplots(figsize=(8.5, 4))
    xs = ["dic-25"] + [modulo2.mes_txt(m) for m in c20.index]
    for serie, nombre, color in [("r_fondo_acum", "Fondo E de AFP Capital (valor cuota, nominal)", AZUL),
                                 ("r_swaps_acum", "Contribución estimada de los swaps SOFR", NARANJA),
                                 ("r_resto_acum", "Resto de la cartera (diferencia)", VERDE)]:
        y = np.r_[0, 100 * c20[serie].to_numpy()]
        ax.plot(xs, y, color=color, marker="o", markersize=4, label=nombre, linestyle="--" if serie == "r_resto_acum" else "-")
        ax.annotate(es(y[-1]) + "%", (xs[-1], y[-1]), xytext=(6, -3), textcoords="offset points", fontsize=9)
    ax.axhline(0, color=TEXTO, linewidth=0.8)
    ax.set_title("Rentabilidad nominal acumulada en 2026 y contribución de los swaps")
    ax.set_ylabel("%"); ax.legend(fontsize=8, loc="lower left"); ax.margins(x=0.09)
    guardar(f, fig / "p20_contribucion.png")
    r.update(swaps_acum=c20["r_swaps_acum"].iloc[-1], fondo_acum=c20["r_fondo_acum"].iloc[-1], resto_acum=c20["r_resto_acum"].iloc[-1],
             peor20=c20["r_swaps"].idxmin(), peor20_r=c20["r_swaps"].min(), mtm_clp_2026=c20["mtm_clp"].sum(),
             swaps_sep=c20["r_swaps"].iloc[-1], fondo_sep=c20["r_fondo"].iloc[-1],
             corr20=np.corrcoef(c20["r_swaps"], c20["r_fondo"])[0, 1],
             dif_10a=modulo1.curva(par.loc["2026-09"], [10], tau)[0] - modulo1.curva(par.loc["2025-12"], [10], tau)[0],
             dif_5a=modulo1.curva(par.loc["2026-09"], [5], tau)[0] - modulo1.curva(par.loc["2025-12"], [5], tau)[0])

    m = lambda x, d=1: tex(x / 1e6, d)
    macros(tab / "m3_macros.tex", {
        "MIIIpv": tex(r["pv01"] / 1e3, 0), "MIIIpvAbs": es(abs(r["pv01"]) / 1e6, 2), "MIIIpvCompra": tex(r["pv01_compra"] / 1e3, 0),
        "MIIIpvVenta": tex(r["pv01_venta"] / 1e3, 0), "MIIIduracion": es(r["duracion"], 1),
        "MIIIcienPb": es(abs(r["perdida_100pb"]) / 1e6, 0), "MIIIcienPbPat": es(100 * abs(r["perdida_100pb_pat"]), 1) + "\\%",
        "MIIIpvLargo": pct(r["pv01_5a10"], 0), "MIIIdurCompra": es(r["dur_compra"], 1), "MIIIdurVenta": es(r["dur_venta"], 2),
        "MIIIvalorBase": m(r["valor_base"], 0), "MIIIvalorBaseSP": m(r["valor_base_sp"], 0),
        "MIIImtmTotal": m(r["mtm_total"], 0), "MIIImtmVeinticuatro": m(r["mtm_2024"], 0), "MIIImtmVeinticinco": m(r["mtm_2025"], 0),
        "MIIImtmVeintiseis": m(r["mtm_2026"], 0), "MIIIpeorMes": modulo2.mes_largo(r["peor"]), "MIIIpeorUsd": m(r["peor_usd"], 0),
        "MIIImejorMes": modulo2.mes_largo(r["mejor"]), "MIIImejorUsd": m(r["mejor_usd"], 0),
        "MIIImesesNeg": str(r["meses_neg_2026"]), "MIIIcorrInformado": es(r["corr_informado"], 2),
        "MIIIswapsAcum": pct(r["swaps_acum"]), "MIIIfondoAcum": pct(r["fondo_acum"]), "MIIIrestoAcum": pct(r["resto_acum"]),
        "MIIIpeorContribMes": modulo2.mes_largo(r["peor20"]), "MIIIpeorContrib": pct(r["peor20_r"]),
        "MIIImtmClp": tex(r["mtm_clp_2026"] / 1e9, 0), "MIIIswapsSep": pct(r["swaps_sep"]), "MIIIfondoSep": pct(r["fondo_sep"]),
        "MIIIcorrVeinte": es(r["corr20"], 2), "MIIIdifDiez": es(100 * r["dif_10a"], 0), "MIIIdifCinco": es(100 * r["dif_5a"], 0),
        "MIIIparticipacion": pct(r["swaps_acum"] / r["fondo_acum"], 0),
    })
    return r, mtm, c20
