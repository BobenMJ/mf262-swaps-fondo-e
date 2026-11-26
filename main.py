#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Efecto de los swaps de tasas extranjeras en los fondos de pensiones (EAE3301).

Punto de entrada del proyecto. Regenera las tablas y los gráficos del informe a
partir de los datos guardados en data/raw/, sin conexión a internet ni claves:

    python main.py

Estado: verifica los datos originales y ejecuta los módulos I, II y III.
"""
import sys

import warnings

from src import datos, modulo1, modulo2, modulo3

warnings.filterwarnings("ignore", category=FutureWarning)



def main():
    print("Datos originales (data/raw/)")
    estado = datos.estado_datos()
    for nombre, ok, detalle in estado:
        print("  [{}] {:<17} {}".format("OK" if ok else "--", nombre, detalle))

    if not all(ok for nombre, ok, _ in estado if "CMT" in nombre or "GSW" in nombre):
        return 1
    print("\nMódulo I: curvas de tasas en dólares (Nelson y Siegel)")
    r, _ = modulo1.ejecutar()
    print("  P2  {meses} meses x {madureces} madureces = {n_obs} observaciones".format(**r))
    print("  P4  tau = 1: SCR total = {scr_tau_1:.4f} pp2, N = {n_obs}".format(**r))
    print("  P5  tau óptimo = {tau_optimo:.3f} años: SCR mínimo = {scr_minimo:.4f} pp2, N = {n_obs}".format(**r))
    print("  P7  diferencia absoluta media con SVENPY (pb): {}".format(r["p7_dif_abs_media_pb"]))
    print("  Tablas en output/tablas y gráficos en output/figuras")

    print("\nMódulo II: posiciones en swaps del Fondo E de AFP Capital")
    r, _ = modulo2.ejecutar()
    print("  P8  rentabilidad acumulada dic-2025 a sep-2026: nominal {:+.2%}, real {:+.2%}".format(r["nominal_acum"], r["real_acum"]))
    print("  P11 cartera base {}: compra fija {:,.0f}, venta fija {:,.0f}, neto {:,.0f} MMUSD".format(
        r["base"], r["compra_base"] / 1e6, r["venta_base"] / 1e6, r["neto_base"] / 1e6))
    print("  P12 sep-2026 estimado: compra fija {:,.0f}, venta fija {:,.0f}, neto {:,.0f} MMUSD".format(
        r["compra_fin"] / 1e6, r["venta_fin"] / 1e6, r["neto_fin"] / 1e6))
    print("  P14 {} contrapartes; las cinco mayores concentran {:.0%} del nocional bruto".format(r["n_contrapartes"], r["top5"]))

    print("\nMódulo III: PV01, mark-to-market y contribución de los swaps")
    r, _, _ = modulo3.ejecutar()
    print("  P17 PV01 cartera {}: {:,.0f} USD por +1 pb (duración equivalente {:.1f} años)".format(r["base"], r["pv01"], r["duracion"]))
    print("  P19 mark-to-market acumulado feb-2024 a sep-2026: {:,.0f} MMUSD (2026: {:,.0f})".format(r["mtm_total"] / 1e6, r["mtm_2026"] / 1e6))
    print("  P20 contribución acumulada 2026: swaps {:+.2%}, fondo (nominal) {:+.2%}".format(r["swaps_acum"], r["fondo_acum"]))
    return 0 if all(ok for _, ok, _ in estado) else 1


if __name__ == "__main__":
    sys.exit(main())
