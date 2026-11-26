# -*- coding: utf-8 -*-
"""Módulo II: posiciones en swaps de tasas en dólares del Fondo E de AFP Capital (P8 a P14)."""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import carteras, config, datos
from .formato import FIN, es, macros, pct, tex
from .graficos import AZUL, CATEGORICA, NARANJA, RAMPA_AZUL, SUPERFICIE, TEXTO, TEXTO_2, guardar, plt

MESES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]
SENTIDOS = ["compra_fija", "venta_fija"]


MESES_LARGO = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre",
               "octubre", "noviembre", "diciembre"]


def mes_largo(p):
    p = pd.Period(p, "M")
    return "{} de {}".format(MESES_LARGO[p.month - 1], p.year)


def mes_txt(p, largo=False):
    p = pd.Period(p, "M")
    return "{}-{}".format(MESES[p.month - 1], p.year if largo else str(p.year)[2:])


# ----------------------------------------------------------------------------
# P8: patrimonio, valor cuota y rentabilidades
# ----------------------------------------------------------------------------
def rentabilidades():
    fondo, mon = datos.cargar_fondo(), datos.cargar_monetarios()
    fechas = pd.period_range(config.BASE_RENTABILIDAD, config.CIERRE_ANALISIS, freq="M").to_timestamp(how="end").normalize()
    t = fondo.loc[fechas, ["valor_cuota", "patrimonio"]].join(mon.loc[fechas, ["uf", "dolar"]])
    t.index.name = "fecha"
    t["rent_nominal"] = t["valor_cuota"].pct_change()
    t["rent_real"] = (1 + t["rent_nominal"]) / (t["uf"] / t["uf"].shift(1)) - 1
    t["acum_nominal"] = t["valor_cuota"] / t["valor_cuota"].iloc[0] - 1
    t["acum_real"] = (1 + t["rent_real"].fillna(0)).cumprod() - 1
    return t


def p8(r):
    t = rentabilidades()
    t.to_csv(config.OUT_TAB / "p8_rentabilidades.csv", float_format="%.6f")
    filas = []
    for f, x in t.iterrows():
        filas.append("{:%d-%m-%Y} & {} & {} & {} & {} & {} & {} & {}".format(
            f, es(x.valor_cuota), es(x.patrimonio / 1e9, 0), es(x.uf),
            *["--" if pd.isna(v) else pct(v) for v in (x.rent_nominal, x.rent_real)],
            pct(x.acum_nominal), pct(x.acum_real)) + FIN)
    (config.OUT_TAB / "p8_tabla.tex").write_text("".join(filas), encoding="utf-8")

    etiquetas = [mes_txt(f.to_period("M")) for f in t.index]
    f, ax = plt.subplots(figsize=(8, 3.8))
    ax.bar(etiquetas, t["patrimonio"] / 1e12, color=AZUL, width=0.6)
    for x, v in zip(etiquetas, t["patrimonio"] / 1e12):
        ax.text(x, v + 0.05, es(v), ha="center", fontsize=8, color=TEXTO_2)
    ax.set_title("Patrimonio del Fondo E de AFP Capital al cierre de cada mes")
    ax.set_ylabel("Billones de pesos")
    ax.grid(axis="x", visible=False)
    guardar(f, config.OUT_FIG / "p8_patrimonio.png")

    f, ax = plt.subplots(figsize=(8, 3.8))
    for col, nombre, color in [("acum_nominal", "Nominal", AZUL), ("acum_real", "Real (deflactada por UF)", NARANJA)]:
        ax.plot(etiquetas, 100 * t[col], color=color, marker="o", markersize=4, label=nombre)
        ax.annotate(es(100 * t[col].iloc[-1]) + "%", (etiquetas[-1], 100 * t[col].iloc[-1]),
                    xytext=(6, -3), textcoords="offset points", fontsize=9)
    ax.axhline(0, color=TEXTO_2, linewidth=0.8)
    ax.set_title("Rentabilidad acumulada del Fondo E de AFP Capital desde el 31-12-2025")
    ax.set_ylabel("%")
    ax.legend(loc="lower left")
    ax.margins(x=0.08)
    guardar(f, config.OUT_FIG / "p8_rentabilidad_acumulada.png")

    r.update(nominal_acum=t["acum_nominal"].iloc[-1], real_acum=t["acum_real"].iloc[-1],
             uf_var=t["uf"].iloc[-1] / t["uf"].iloc[0] - 1, pat_ini=t["patrimonio"].iloc[0],
             pat_fin=t["patrimonio"].iloc[-1], dolar_fin=t["dolar"].iloc[-1],
             peor_mes=t["rent_nominal"].idxmin(), peor_mes_rent=t["rent_nominal"].min())
    return t


# ----------------------------------------------------------------------------
# P9: agregados del SIID
# ----------------------------------------------------------------------------
def siid_swaps():
    """Swaps de tasas extranjeras de los Fondos de Pensiones, en USD, por mes.

    El SIID informa compra y venta de tasa VARIABLE; aquí se traducen al sentido del
    enunciado: venta variable = compra fija; compra variable = venta fija.
    """
    t, _ = datos.cargar_cuadro_bde("DER_TAS_FP_STO_01")
    out = pd.DataFrame({"compra_fija": t[config.BDE_SWAP_EXT_VENTA_VARIABLE],
                        "venta_fija": t[config.BDE_SWAP_EXT_COMPRA_VARIABLE],
                        "total": t[config.BDE_SWAP_EXT_TOTAL]}) * 1e6
    out.index = out.index.to_period("M")
    return out


def p9(r):
    res, nombres = datos.cargar_cuadro_bde("DER_RES_POS_02")
    res = res.loc[res.index > pd.Timestamp(config.CIERRE_ANALISIS) - pd.DateOffset(years=3)]
    hojas = {"ME-ME": "Monedas: extranjera-extranjera", "ME-ML": "Monedas: extranjera-local",
             "Inflación CLF-CLP": "Inflación (UF-peso)", "SPC-CLP": "Tasas: swap promedio cámara",
             "Tasas extranjeras": "Tasas: extranjeras"}
    cod = {v: k for k, v in nombres.items()}
    datos_h = pd.DataFrame({hojas[n]: res[cod[n]] for n in hojas}) / 1e3     # miles de millones USD
    total = res[cod["Monto vigente total, total"]] / 1e3
    # Las categorías suman el total publicado salvo redondeos y una diferencia de 0,1% en sep-2025
    assert ((datos_h.sum(axis=1) - total).abs() / total).max() < 0.002, "las categorías no suman el total del SIID"
    datos_h.assign(total=total).to_csv(config.OUT_TAB / "p9_siid_subyacente.csv", float_format="%.3f")

    x = np.arange(len(datos_h))
    f, ax = plt.subplots(figsize=(9, 4.2))
    base = np.zeros(len(datos_h))
    for col, color in zip(datos_h.columns, CATEGORICA):
        ax.bar(x, datos_h[col], bottom=base, color=color, width=0.8, label=col, edgecolor=SUPERFICIE, linewidth=0.6)
        base += datos_h[col].to_numpy()
    ax.set_xticks(x[::3]); ax.set_xticklabels([mes_txt(p) for p in datos_h.index.to_period("M")[::3]])
    ax.set_title("Fondos de Pensiones: montos vigentes en derivados por subyacente")
    ax.set_ylabel("Miles de millones de USD (nocional)")
    ax.grid(axis="x", visible=False)
    ax.legend(loc="upper left", fontsize=8)
    guardar(f, config.OUT_FIG / "p9_siid_subyacente.png")

    sw = siid_swaps().loc[datos_h.index.to_period("M")] / 1e9
    f, ax = plt.subplots(figsize=(9, 4.2))
    xs = [mes_txt(p) for p in sw.index]
    ax.plot(xs, sw["total"], color=TEXTO_2, label="Total vigente")
    ax.plot(xs, sw["compra_fija"], color=AZUL, label="Venta de tasa variable (el fondo recibe fija)")
    ax.plot(xs, sw["venta_fija"], color=NARANJA, label="Compra de tasa variable (el fondo paga fija)")
    ax.set_xticks(xs[::3])
    ax.set_title("Fondos de Pensiones: montos vigentes en swaps de tasas de interés extranjeras")
    ax.set_ylabel("Miles de millones de USD (nocional)")
    ax.legend(loc="upper left", fontsize=8)
    guardar(f, config.OUT_FIG / "p9_siid_swaps_extranjeros.png")

    ult = datos_h.iloc[-1]
    r.update(siid_total_fin=total.iloc[-1], siid_ext_fin=ult["Tasas: extranjeras"],
             siid_ext_part=ult["Tasas: extranjeras"] / total.iloc[-1], siid_ext_ini=datos_h["Tasas: extranjeras"].iloc[0],
             siid_ext_max=sw["total"].max(), siid_ext_max_mes=sw["total"].idxmax(),
             siid_desde=datos_h.index[0].to_period("M"))


# ----------------------------------------------------------------------------
# P11 a P13: posiciones observadas y estimadas
# ----------------------------------------------------------------------------
def tabla_posiciones(swaps, por):
    """Nocional de compra y venta fija y neto, por mes y por `por` (año de madurez o tramo)."""
    t = swaps.pivot_table(index=["mes", por], columns="sentido", values="nocional_usd", aggfunc="sum", fill_value=0.0)
    t = t.reindex(columns=SENTIDOS, fill_value=0.0)
    t["neto"] = t["compra_fija"] - t["venta_fija"]
    return t


def completar(obs, siid, base):
    """P12: extiende la tabla hasta septiembre de 2026 con los agregados del SIID.

    Compras y ventas varían, por separado, en la proporción de su agregado del SIID
    respecto de la cartera base, manteniendo la composición de la cartera base.
    """
    fin = pd.Period(config.CIERRE_ANALISIS, "M")
    partes = [obs.assign(origen="Cartera")]
    b = obs.loc[base]
    for mes in pd.period_range(base + 1, fin, freq="M"):
        est = b[SENTIDOS] * (siid.loc[mes, SENTIDOS] / siid.loc[base, SENTIDOS])
        est["neto"] = est["compra_fija"] - est["venta_fija"]
        est = pd.concat({mes: est}, names=["mes"])
        partes.append(est.assign(origen="Estimado SIID"))
    return pd.concat(partes)


def p11_a_p13(r):
    swaps = carteras.cargar_swaps_fondo()
    swaps = swaps[swaps["nocional_usd"] > 0]
    siid = siid_swaps()
    base = swaps["mes"].max()
    r["base"], r["base_fecha"] = base, swaps["fecha"].max()
    r["primera"] = swaps["mes"].min()

    # P11: tabla observada por año de madurez
    obs = tabla_posiciones(swaps, "anio_madurez")
    # P12: tabla completada
    comp = completar(obs, siid, base)
    salida = comp.reset_index().rename(columns={"mes": "Mes", "anio_madurez": "Año de madurez",
        "compra_fija": "Nocional compra fija (USD)", "venta_fija": "Nocional venta fija (USD)",
        "neto": "Neto compra fija (USD)", "origen": "Origen"})
    salida[salida["Origen"] == "Cartera"].drop(columns="Origen").to_csv(
        config.OUT_TAB / "p11_posiciones_observadas.csv", index=False, float_format="%.0f")
    salida.to_csv(config.OUT_TAB / "p12_posiciones_completadas.csv", index=False, float_format="%.0f")

    # Tabla de la cartera base por año de madurez (informe)
    b = obs.loc[base]
    filas = ["{} & {} & {} & {}".format(a, tex(x.compra_fija / 1e6, 1), tex(x.venta_fija / 1e6, 1), tex(x.neto / 1e6, 1)) + FIN
             for a, x in b.iterrows()]
    filas.append("\\midrule\nTotal & {} & {} & {}".format(*[tex(b[c].sum() / 1e6, 1) for c in SENTIDOS + ["neto"]]) + FIN)
    (config.OUT_TAB / "p11_base_por_anio.tex").write_text("".join(filas), encoding="utf-8")

    # Totales mensuales (informe): observados y estimados
    tot = comp.groupby(level="mes")[SENTIDOS + ["neto"]].sum()
    tot["origen"] = comp.groupby(level="mes")["origen"].first()
    tot["contratos"] = swaps.groupby("mes").size().reindex(tot.index)
    filas = []
    for mes, x in tot.iterrows():
        if mes == base + 1:
            filas.append("\\midrule\n")
        filas.append("{} & {} & {} & {} & {} & {}".format(
            mes_txt(mes, True), tex(x.compra_fija / 1e6, 0), tex(x.venta_fija / 1e6, 0), tex(x.neto / 1e6, 0),
            "--" if pd.isna(x.contratos) else int(x.contratos), x.origen) + FIN)
    (config.OUT_TAB / "p12_totales_mensuales.tex").write_text("".join(filas), encoding="utf-8")
    tot.to_csv(config.OUT_TAB / "p12_totales_mensuales.csv", float_format="%.0f")

    # Factores del SIID usados en la extrapolación
    meses_est = pd.period_range(base, pd.Period(config.CIERRE_ANALISIS, "M"), freq="M")
    filas = ["{} & {} & {} & {} & {}".format(
        mes_txt(m, True), tex(siid.loc[m, "compra_fija"] / 1e9, 1), tex(siid.loc[m, "compra_fija"] / siid.loc[base, "compra_fija"], 4),
        tex(siid.loc[m, "venta_fija"] / 1e9, 1), tex(siid.loc[m, "venta_fija"] / siid.loc[base, "venta_fija"], 4)) + FIN
        for m in meses_est]
    (config.OUT_TAB / "p12_factores_siid.tex").write_text("".join(filas), encoding="utf-8")

    # Evaluación de la proporcionalidad: participaciones y composición por plazo
    totobs = tot[tot["origen"] == "Cartera"]
    part = (totobs[SENTIDOS] / siid.loc[totobs.index, SENTIDOS]).astype(float)
    tramos = tabla_posiciones(swaps, "tramo")
    pesos = {s: (tramos[s].unstack("tramo").reindex(columns=list(config.TRAMOS)).fillna(0)
                 .pipe(lambda d: d.div(d.sum(axis=1), axis=0))) for s in SENTIDOS}
    errores = {}
    for h in (1, 2, 3):   # error de haber aplicado la regla h meses hacia adelante en el pasado
        pred = totobs[SENTIDOS].shift(h) * (siid.loc[totobs.index, SENTIDOS] / siid.loc[totobs.index, SENTIDOS].shift(h).to_numpy())
        errores[h] = ((pred - totobs[SENTIDOS]).abs() / totobs[SENTIDOS]).astype(float).dropna().iloc[-12:].mean()
    part.assign(**{"peso_" + s + "_" + t: pesos[s][t] for s in SENTIDOS for t in config.TRAMOS}).to_csv(
        config.OUT_TAB / "p12_participaciones_y_pesos.csv", float_format="%.5f")

    f, ejes = plt.subplots(1, 2, figsize=(10, 3.8))
    xs = [mes_txt(m) for m in part.index]
    ejes[0].plot(xs, 100 * part["compra_fija"], color=AZUL, label="Compra fija")
    ejes[0].plot(xs, 100 * part["venta_fija"], color=NARANJA, label="Venta fija")
    ejes[0].set_title("Participación del fondo en el agregado del SIID", loc="left")
    ejes[0].set_ylabel("%"); ejes[0].set_ylim(0); ejes[0].legend(fontsize=8)
    base_y = np.zeros(len(xs))
    for t, color in zip(config.TRAMOS, RAMPA_AZUL):
        ejes[1].bar(xs, 100 * pesos["compra_fija"][t], bottom=base_y, color=color, width=0.9, label=t,
                    edgecolor=SUPERFICIE, linewidth=0.4)
        base_y += 100 * pesos["compra_fija"][t].to_numpy()
    ejes[1].set_title("Composición por plazo residual de la compra fija", loc="left")
    ejes[1].set_ylabel("%"); ejes[1].grid(axis="x", visible=False)
    ejes[1].legend(fontsize=7, ncol=8, loc="upper center", bbox_to_anchor=(0.5, -0.12), columnspacing=0.8, handlelength=1.2)
    for ax in ejes:
        ax.set_xticks(xs[::6])
    f.tight_layout()
    guardar(f, config.OUT_FIG / "p12_proporcionalidad.png")

    # P13: gráfico por tramo, observado y estimado
    tr = completar(tramos, siid, base)
    assert np.allclose(tr.groupby(level="mes")[SENTIDOS].sum(), tot[SENTIDOS]), "tramos y años no cuadran"
    tr.reset_index().to_csv(config.OUT_TAB / "p13_posiciones_por_tramo.csv", index=False, float_format="%.0f")
    meses = tot.index
    xs = np.arange(len(meses))
    f, ax = plt.subplots(figsize=(10, 5))
    n_est = int((tot["origen"] != "Cartera").sum())
    ax.axvspan(len(meses) - n_est - 0.5, len(meses) - 0.5, color="#e4e3df", zorder=0, label="Meses estimados con el SIID")
    arriba, abajo = np.zeros(len(meses)), np.zeros(len(meses))
    for t, color in zip(config.TRAMOS, RAMPA_AZUL):
        c = tr["compra_fija"].unstack("tramo").reindex(index=meses, columns=list(config.TRAMOS)).fillna(0)[t].to_numpy() / 1e9
        v = tr["venta_fija"].unstack("tramo").reindex(index=meses, columns=list(config.TRAMOS)).fillna(0)[t].to_numpy() / 1e9
        ax.bar(xs, c, bottom=arriba, color=color, width=0.8, label=t, edgecolor=SUPERFICIE, linewidth=0.5)
        ax.bar(xs, -v, bottom=abajo, color=color, width=0.8, edgecolor=SUPERFICIE, linewidth=0.5)
        arriba += c; abajo -= v
    ax.plot(xs, tot["neto"] / 1e9, color=NARANJA, marker="o", markersize=3, label="Neto compra fija")
    ax.axhline(0, color=TEXTO, linewidth=0.8)
    ax.set_xticks(xs[::3]); ax.set_xticklabels([mes_txt(m) for m in meses[::3]])
    ax.set_title("Fondo E de AFP Capital: nocional vigente en swaps SOFR por plazo residual")
    ax.set_ylabel("Miles de millones de USD\n(compra fija arriba, venta fija abajo)")
    ax.grid(axis="x", visible=False)
    ax.legend(fontsize=8, ncol=5, loc="upper left")
    guardar(f, config.OUT_FIG / "p13_posiciones_por_tramo.png")

    # Contratos (observados y estimados) para la valorización del módulo III
    contratos = [swaps.assign(origen="Cartera", fecha_valor=swaps["fecha"])]
    cb = swaps[swaps["mes"] == base]
    for mes in pd.period_range(base + 1, pd.Period(config.CIERRE_ANALISIS, "M"), freq="M"):
        e = cb.copy()
        e["nocional_usd"] = e["nocional_usd"] * e["sentido"].map((siid.loc[mes, SENTIDOS] / siid.loc[base, SENTIDOS]).to_dict())
        e["mes"], e["origen"], e["fecha_valor"] = mes, "Estimado SIID", mes.to_timestamp(how="end").normalize()
        contratos.append(e)
    pd.concat(contratos).drop(columns=["valor_clp"]).to_csv(config.DATA_PROC / "posiciones_contratos.csv", index=False)

    ub, pat = tot.loc[base], datos.cargar_fondo().loc[r["base_fecha"], "patrimonio"]
    dolar = datos.cargar_monetarios().loc[r["base_fecha"], "dolar"]
    pb = {s: pesos[s].loc[base] for s in SENTIDOS}
    cbase = swaps[swaps["mes"] == base]
    r.update(compra_base=ub.compra_fija, venta_base=ub.venta_fija, neto_base=ub.neto, contratos_base=len(cbase),
             pat_base_usd=pat / dolar, compra_sobre_pat=ub.compra_fija / (pat / dolar),
             compra_ini=tot["compra_fija"].iloc[0], venta_ini=tot["venta_fija"].iloc[0],
             compra_fin=tot["compra_fija"].iloc[-1], venta_fin=tot["venta_fija"].iloc[-1], neto_fin=tot["neto"].iloc[-1],
             neto_mar=tot.loc["2026-03", "neto"], neto_abr=tot.loc["2026-04", "neto"], venta_abr=tot.loc["2026-04", "venta_fija"],
             venta_max=tot["venta_fija"].max(), venta_max_mes=tot["venta_fija"].idxmax(),
             part_compra_base=part["compra_fija"].iloc[-1], part_venta_base=part["venta_fija"].iloc[-1],
             part_compra_min=part["compra_fija"].iloc[-12:].min(), part_compra_max=part["compra_fija"].iloc[-12:].max(),
             part_venta_min=part["venta_fija"].iloc[-12:].min(), part_venta_max=part["venta_fija"].iloc[-12:].max(),
             err=errores, peso_compra_largo=pb["compra_fija"][["5y", "10y"]].sum(), peso_venta_3m=pb["venta_fija"]["3m"],
             res_compra=np.average(cbase[cbase.sentido == "compra_fija"]["residual"], weights=cbase[cbase.sentido == "compra_fija"]["nocional_usd"]),
             res_venta=np.average(cbase[cbase.sentido == "venta_fija"]["residual"], weights=cbase[cbase.sentido == "venta_fija"]["nocional_usd"]),
             tasa_compra=np.average(cbase[cbase.sentido == "compra_fija"]["tasa_fija"], weights=cbase[cbase.sentido == "compra_fija"]["nocional_usd"]),
             tasa_venta=np.average(cbase[cbase.sentido == "venta_fija"]["tasa_fija"], weights=cbase[cbase.sentido == "venta_fija"]["nocional_usd"]))
    return swaps, tot


# ----------------------------------------------------------------------------
# P14: contrapartes
# ----------------------------------------------------------------------------
def p14(swaps, r):
    b = swaps[swaps["mes"] == r["base"]]
    t = b.pivot_table(index=["contraparte", "nacionalidad"], columns="sentido", values="nocional_usd",
                      aggfunc="sum", fill_value=0.0).reindex(columns=SENTIDOS, fill_value=0.0).reset_index()
    t["bruto"] = t["compra_fija"] + t["venta_fija"]
    t = t.sort_values("bruto", ascending=False).reset_index(drop=True)
    t["participacion"] = t["bruto"] / t["bruto"].sum()
    t.to_csv(config.OUT_TAB / "p14_contrapartes.csv", index=False, float_format="%.4f")
    top, resto = t.iloc[:5], t.iloc[5:]
    filas = ["{} & {} & {} & {} & {} & {}".format(x.contraparte.title().replace(" Plc", " PLC").replace(" Na", " NA").replace(" Sa", " SA").replace(" Co ", " \\& Co. ").replace(" Of ", " of ").replace("Bnp", "BNP"),
             x.nacionalidad, tex(x.compra_fija / 1e6, 0), tex(x.venta_fija / 1e6, 0), tex(x.bruto / 1e6, 0), pct(x.participacion, 1)) + FIN
             for x in top.itertuples()]
    filas.append("Otras ({}) & -- & {} & {} & {} & {}".format(len(resto), *[tex(resto[c].sum() / 1e6, 0) for c in SENTIDOS + ["bruto"]],
                                                           pct(resto["participacion"].sum(), 1)) + FIN)
    filas.append("\\midrule\nTotal & & {} & {} & {} & {}".format(*[tex(t[c].sum() / 1e6, 0) for c in SENTIDOS + ["bruto"]], pct(1, 1)) + FIN)
    (config.OUT_TAB / "p14_contrapartes.tex").write_text("".join(filas), encoding="utf-8")
    ext = t[t["nacionalidad"] == "Extranjera"]["bruto"].sum() / t["bruto"].sum()
    r.update(n_contrapartes=len(t), top1=t.loc[0, "participacion"], top3=t["participacion"].iloc[:3].sum(),
             top5=t["participacion"].iloc[:5].sum(), part_extranjeras=ext, hhi=(t["participacion"] ** 2).sum() * 10000,
             otras=", ".join(resto["contraparte"].str.title()))


def ejecutar():
    config.OUT_TAB.mkdir(parents=True, exist_ok=True)
    carteras.extraer()
    r = {}
    p8(r)
    p9(r)
    swaps, tot = p11_a_p13(r)
    p14(swaps, r)

    m = lambda x: es(x / 1e6, 0)          # millones de USD
    mm = lambda x: es(x / 1e9, 2)         # miles de millones de USD
    macros(config.OUT_TAB / "m2_macros.tex", {
        "MIInominal": pct(r["nominal_acum"]), "MIIreal": pct(r["real_acum"]), "MIIuf": pct(r["uf_var"]),
        "MIIpatIni": es(r["pat_ini"] / 1e12), "MIIpatFin": es(r["pat_fin"] / 1e12),
        "MIIpatVar": pct(r["pat_fin"] / r["pat_ini"] - 1, 1),
        "MIIpeorMes": mes_largo(r["peor_mes"].to_period("M")), "MIIpeorMesRent": pct(r["peor_mes_rent"]),
        "MIIsiidTotal": es(r["siid_total_fin"], 0), "MIIsiidExt": es(r["siid_ext_fin"], 0), "MIIsiidExtPart": pct(r["siid_ext_part"], 0),
        "MIIsiidExtIni": es(r["siid_ext_ini"], 0), "MIIsiidExtMax": es(r["siid_ext_max"], 0),
        "MIIsiidExtMaxMes": mes_largo(r["siid_ext_max_mes"]),
        "MIIsiidDesde": mes_largo(r["siid_desde"]),
        "MIIbase": mes_largo(r["base"]), "MIIbaseFecha": "{:%d-%m-%Y}".format(r["base_fecha"]),
        "MIIcontratosBase": str(r["contratos_base"]),
        "MIIcompraBase": m(r["compra_base"]), "MIIventaBase": m(r["venta_base"]), "MIInetoBase": m(r["neto_base"]),
        "MIIcompraBaseMM": mm(r["compra_base"]), "MIIventaBaseMM": mm(r["venta_base"]), "MIInetoBaseMM": mm(r["neto_base"]),
        "MIIpatBaseUsd": mm(r["pat_base_usd"]), "MIIcompraSobrePat": es(r["compra_sobre_pat"], 1),
        "MIIcompraIni": m(r["compra_ini"]), "MIIventaIni": m(r["venta_ini"]),
        "MIIcompraFin": m(r["compra_fin"]), "MIIventaFin": m(r["venta_fin"]), "MIInetoFin": m(r["neto_fin"]),
        "MIInetoMar": tex(r["neto_mar"] / 1e6, 0), "MIInetoAbr": tex(r["neto_abr"] / 1e6, 0),
        "MIIventaAbr": m(r["venta_abr"]),
        "MIIventaMax": m(r["venta_max"]), "MIIventaMaxMes": mes_largo(r["venta_max_mes"]),
        "MIIpartCompra": pct(r["part_compra_base"]), "MIIpartVenta": pct(r["part_venta_base"]),
        "MIIpartCompraMin": pct(r["part_compra_min"]), "MIIpartCompraMax": pct(r["part_compra_max"]),
        "MIIpartVentaMin": pct(r["part_venta_min"]), "MIIpartVentaMax": pct(r["part_venta_max"]),
        "MIIerrCompraUno": pct(r["err"][1]["compra_fija"], 1), "MIIerrCompraTres": pct(r["err"][3]["compra_fija"], 1),
        "MIIerrVentaUno": pct(r["err"][1]["venta_fija"], 1), "MIIerrVentaTres": pct(r["err"][3]["venta_fija"], 1),
        "MIIpesoCompraLargo": pct(r["peso_compra_largo"], 0), "MIIpesoVentaCorto": pct(r["peso_venta_3m"], 0),
        "MIIresCompra": es(r["res_compra"], 1), "MIIresVenta": es(r["res_venta"], 1),
        "MIItasaCompra": es(r["tasa_compra"], 2), "MIItasaVenta": es(r["tasa_venta"], 2),
        "MIIcontrapartes": str(r["n_contrapartes"]), "MIItopUno": pct(r["top1"], 0), "MIItopTres": pct(r["top3"], 0),
        "MIItopCinco": pct(r["top5"], 0), "MIIextranjeras": pct(r["part_extranjeras"], 0), "MIIhhi": es(r["hhi"], 0),
    })
    return r, tot
