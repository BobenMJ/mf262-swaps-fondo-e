#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Descarga OPCIONAL de los datos originales del proyecto (requiere internet).

main.py NO necesita este script: trabaja solo con lo que ya está en data/raw/.
Este script documenta de dónde salió cada archivo y permite repetir la descarga.

Uso, desde la raíz del proyecto:

    python scripts/descargar_datos.py                  # todas las fuentes
    python scripts/descargar_datos.py --solo fred fed  # solo algunas
    python scripts/descargar_datos.py --forzar         # vuelve a bajar aunque ya exista

Fuentes automáticas
    fred           Tasas CMT diarias (FRED; lee la clave desde FRED_API_KEY.env)
    fed            Curva de Gürkaynak, Sack y Wright (SVENPY), Federal Reserve Board
    sp_cuotas      Valor cuota y patrimonio del Fondo E (Superintendencia de Pensiones)
    sp_monetarios  UF y dólar diarios (Superintendencia de Pensiones)
    bde_siid       Derivados de Fondos de Pensiones del SIID (BDE, Banco Central)

Fuente manual
    sp_carteras    Carteras históricas de inversión. El formulario de la SP usa
                   reCAPTCHA, así que se descarga a mano (ver README).

Cada archivo se guarda tal como lo entrega la fuente y queda anotado, con URL,
fecha de descarga, tamaño y hash SHA-256, en data/raw/registro_descargas.csv.
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import os
import re
import sys
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

from src import config  # noqa: E402

ARCHIVO_CLAVE = RAIZ / "FRED_API_KEY.env"
USER_AGENT = ("Mozilla/5.0 (compatible; descarga-datos-EAE3301/1.0; "
              "proyecto academico UC; python-requests)")
CAMPOS_REGISTRO = ["fuente", "archivo", "url", "fecha_descarga", "bytes", "sha256"]


class ErrorDescarga(Exception):
    """Error esperable de una fuente (red, formato inesperado, clave, etc.)."""


# ----------------------------------------------------------------------------
# Utilidades
# ----------------------------------------------------------------------------
def crear_sesion():
    try:
        import requests
    except ImportError:
        raise SystemExit("Falta el paquete 'requests'. Instala las dependencias con:\n"
                         "    pip install -r requirements.txt")
    sesion = requests.Session()
    sesion.headers.update({"User-Agent": USER_AGENT,
                           "Accept-Language": "es-CL,es;q=0.9,en;q=0.8"})
    return sesion


def pedir(sesion, metodo, url, intentos=3, espera=3.0, timeout=120, **kw):
    """Hace la petición con reintentos simples y exige HTTP 200."""
    ultimo = "sin respuesta"
    for i in range(1, intentos + 1):
        try:
            r = sesion.request(metodo, url, timeout=timeout, **kw)
            if r.status_code == 200:
                return r
            ultimo = "HTTP {}".format(r.status_code)
            if r.status_code in (400, 401, 403, 404):
                break  # reintentar no ayuda
        except Exception as e:  # errores de red, DNS, TLS, timeout
            ultimo = "{}: {}".format(type(e).__name__, e)
        if i < intentos:
            time.sleep(espera * i)
    raise ErrorDescarga("{} {} -> {}".format(metodo, url, ultimo))


def relativa(ruta):
    return str(Path(ruta).resolve().relative_to(RAIZ)).replace(os.sep, "/")


def registrar(fuente, ruta, url, contenido):
    """Anota (o actualiza) el archivo en data/raw/registro_descargas.csv."""
    filas = {}
    registro = config.REGISTRO_DESCARGAS
    if registro.exists():
        with open(registro, newline="", encoding="utf-8") as f:
            for fila in csv.DictReader(f):
                filas[fila["archivo"]] = fila
    filas[relativa(ruta)] = {
        "fuente": fuente,
        "archivo": relativa(ruta),
        "url": url,
        "fecha_descarga": dt.datetime.now().astimezone().isoformat(timespec="seconds"),
        "bytes": str(len(contenido)),
        "sha256": hashlib.sha256(contenido).hexdigest(),
    }
    registro.parent.mkdir(parents=True, exist_ok=True)
    with open(registro, "w", newline="", encoding="utf-8") as f:
        escritor = csv.DictWriter(f, fieldnames=CAMPOS_REGISTRO)
        escritor.writeheader()
        for clave in sorted(filas):
            escritor.writerow(filas[clave])


def guardar(ruta, contenido, fuente, url):
    ruta = Path(ruta)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_bytes(contenido)
    registrar(fuente, ruta, url, contenido)
    print("    guardado {} ({:,} bytes)".format(relativa(ruta), len(contenido)))


def meses_entre(inicio, fin):
    """Lista de (año, mes) desde inicio hasta fin, ambos inclusive."""
    (a, m), salida = inicio, []
    while (a, m) <= fin:
        salida.append((a, m))
        a, m = (a + 1, 1) if m == 12 else (a, m + 1)
    return salida


# ----------------------------------------------------------------------------
# FRED: tasas CMT diarias
# ----------------------------------------------------------------------------
def leer_clave_fred():
    if not ARCHIVO_CLAVE.exists():
        raise ErrorDescarga("No existe {}. Debe contener una línea "
                            "FRED_API_KEY=<tu clave>.".format(ARCHIVO_CLAVE.name))
    for linea in ARCHIVO_CLAVE.read_text(encoding="utf-8-sig").splitlines():
        linea = linea.strip()
        if not linea or linea.startswith("#") or "=" not in linea:
            continue
        nombre, valor = linea.split("=", 1)
        if nombre.strip() == "FRED_API_KEY":
            valor = valor.strip().strip('"').strip("'")
            if re.fullmatch(r"[0-9a-z]{32}", valor):
                return valor
            raise ErrorDescarga("La clave de FRED_API_KEY.env no tiene el formato "
                                "esperado (32 caracteres, minúsculas y números).")
    raise ErrorDescarga("FRED_API_KEY.env no contiene una línea FRED_API_KEY=<clave>.")


def bajar_fred(sesion, forzar):
    destino = config.RAW_FRED
    if destino.exists() and not forzar:
        return "ya estaba"
    try:
        # fredapi usa urllib; en algunos Python de macOS no encuentra los
        # certificados raíz. Con esto usa los mismos que 'requests'.
        import certifi
        os.environ.setdefault("SSL_CERT_FILE", certifi.where())
    except ImportError:
        pass
    try:
        import pandas as pd
        from fredapi import Fred
    except ImportError:
        raise ErrorDescarga("Faltan 'pandas' o 'fredapi': pip install -r requirements.txt")

    clave = leer_clave_fred()
    fred = Fred(api_key=clave)
    columnas = {}
    for codigo in config.SERIES_CMT:
        try:
            columnas[codigo] = fred.get_series(codigo,
                                               observation_start=config.CMT_INICIO,
                                               observation_end=config.CMT_FIN)
        except Exception as e:
            mensaje = "{}: {}".format(type(e).__name__, e).replace(clave, "***")
            raise ErrorDescarga("FRED, serie {} -> {}".format(codigo, mensaje))
        print("    {:<7} {:>5} observaciones".format(codigo, int(columnas[codigo].notna().sum())))
        time.sleep(0.3)

    tabla = pd.DataFrame(columnas).sort_index()
    tabla.index.name = "fecha"
    vacias = [c for c in tabla.columns if tabla[c].notna().sum() == 0]
    if vacias:
        raise ErrorDescarga("FRED devolvió series sin datos: {}".format(", ".join(vacias)))
    if str(tabla.index.max().date()) < "2026-09-25":
        raise ErrorDescarga("FRED: el último dato es {}, anterior a fines de septiembre "
                            "de 2026.".format(tabla.index.max().date()))
    contenido = tabla.to_csv(float_format="%.2f", date_format="%Y-%m-%d").encode("utf-8")
    url = "https://api.stlouisfed.org/fred/series/observations (fredapi; series: {})".format(
        ", ".join(config.SERIES_CMT))
    guardar(destino, contenido, "fred", url)
    return "ok"


# ----------------------------------------------------------------------------
# Federal Reserve Board: curva GSW (SVENPY)
# ----------------------------------------------------------------------------
def bajar_fed(sesion, forzar):
    destino = config.RAW_FED
    if destino.exists() and not forzar:
        return "ya estaba"
    r = pedir(sesion, "GET", config.URL_FED_GSW, timeout=300)
    contenido = r.content
    if b"SVENPY01" not in contenido[:20000] or b"Date," not in contenido[:20000]:
        raise ErrorDescarga("El archivo de la Fed no trae el encabezado esperado (Date, SVENPY01...).")
    ultima = contenido.strip().splitlines()[-1][:10].decode("ascii", "replace")
    if ultima < config.CIERRE_ANALISIS:
        raise ErrorDescarga("La Fed publica hasta {}; falta {}.".format(ultima, config.CIERRE_ANALISIS))
    guardar(destino, contenido, "fed", config.URL_FED_GSW)
    return "ok"


# ----------------------------------------------------------------------------
# Superintendencia de Pensiones: valor cuota y patrimonio del Fondo E
# ----------------------------------------------------------------------------
def bajar_sp_cuotas(sesion, forzar):
    destino = config.RAW_SP_CUOTAS
    if destino.exists() and not forzar:
        return "ya estaba"
    pagina = "{}?tf={}".format(config.URL_SP_VC, config.FONDO)
    r = pedir(sesion, "GET", pagina)
    m = re.search(r"fecconf=(\d{8})", r.text)
    if not m:
        raise ErrorDescarga("No encontré la fecha de valores confirmados (fecconf) en " + pagina)
    url = "{}?aaaaini={}&aaaafin={}&tf={}&fecconf={}".format(
        config.URL_SP_VC_CSV, config.SP_VC_ANIO_INI, config.SP_VC_ANIO_FIN, config.FONDO, m.group(1))
    r = pedir(sesion, "GET", url, headers={"Referer": pagina})
    contenido = r.content
    for marca in (b"Fecha;", config.AFP.encode("ascii"), b"2025-12-31;", b"2026-09-30;"):
        if marca not in contenido:
            raise ErrorDescarga("El CSV de valores cuota no contiene '{}'.".format(marca.decode()))
    guardar(destino, contenido, "sp_cuotas", url)
    return "ok"


# ----------------------------------------------------------------------------
# Superintendencia de Pensiones: UF y dólar diarios ("Valores monetarios")
# ----------------------------------------------------------------------------
def bajar_sp_monetarios(sesion, forzar):
    meses = meses_entre(config.SP_MONETARIOS_INI, config.SP_MONETARIOS_FIN)
    nuevos = 0
    for anio, mes in meses:
        destino = config.RAW_SP_MONETARIOS / "{}-{:02d}.html".format(anio, mes)
        if destino.exists() and not forzar:
            continue
        datos = {"aaaaVM": str(anio), "mmVM": "{:02d}".format(mes), "btn": "Buscar"}
        r = pedir(sesion, "POST", config.URL_SP_MONETARIOS, data=datos,
                  headers={"Referer": config.URL_SP_MONETARIOS})
        texto = r.text
        if (not re.search(r'value="{}"\s+selected'.format(anio), texto)
                or not re.search(r'value="{:02d}"\s+selected'.format(mes), texto)):
            raise ErrorDescarga("Valores monetarios: la SP no devolvió {}-{:02d}.".format(anio, mes))
        dias = re.findall(r'<td[^>]*>\s*(\d{2})\s*</td>', texto)
        if len(dias) < 28 or "U.F." not in texto:
            raise ErrorDescarga("Valores monetarios {}-{:02d}: tabla incompleta "
                                "({} días).".format(anio, mes, len(dias)))
        guardar(destino, r.content, "sp_monetarios",
                "{} (POST aaaaVM={}, mmVM={:02d})".format(config.URL_SP_MONETARIOS, anio, mes))
        nuevos += 1
        time.sleep(0.4)
    return "ok ({} meses nuevos de {})".format(nuevos, len(meses)) if nuevos else "ya estaba"


# ----------------------------------------------------------------------------
# Banco Central (BDE): estadísticas del SIID para Fondos de Pensiones
# ----------------------------------------------------------------------------
def bajar_bde_siid(sesion, forzar):
    nuevos = 0
    for codigo, url in config.CUADROS_BDE.items():
        destino = config.RAW_BDE / (codigo + ".html")
        if destino.exists() and not forzar:
            continue
        r = pedir(sesion, "GET", url, params=config.BDE_PARAMS)
        texto = r.text
        if 'id="grilla"' not in texto:
            raise ErrorDescarga("BDE {}: la respuesta no trae la tabla de datos (puede ser "
                                "un filtro anti-robots del sitio).".format(codigo))
        if config.BDE_ULTIMO_MES not in texto:
            raise ErrorDescarga("BDE {}: el cuadro no llega a {}.".format(codigo, config.BDE_ULTIMO_MES))
        guardar(destino, r.content, "bde_siid", r.url)
        nuevos += 1
        time.sleep(0.5)
    return "ok ({} cuadros nuevos)".format(nuevos) if nuevos else "ya estaba"


# ----------------------------------------------------------------------------
# Carteras históricas (manual)
# ----------------------------------------------------------------------------
def revisar_carteras():
    carpeta = config.RAW_CARTERAS
    archivos = [p.name for p in carpeta.glob("*")
                if p.is_file() and p.name.upper() not in ("LEEME.TXT", ".GITKEEP", ".DS_STORE")]
    return archivos


AYUDA_MANUAL = {
    "fred": "Revisa tu conexión y la clave de FRED_API_KEY.env (https://fredaccount.stlouisfed.org/apikeys).",
    "fed": "Abre {} en el navegador y guarda el archivo como {}.".format(
        config.URL_FED_GSW, relativa(config.RAW_FED)),
    "sp_cuotas": ("Abre {}?tf=E, elige {} y {} al pie de la página, pulsa el ícono CSV y guarda "
                  "el archivo como {}.").format(config.URL_SP_VC, config.SP_VC_ANIO_INI,
                                                config.SP_VC_ANIO_FIN, relativa(config.RAW_SP_CUOTAS)),
    "sp_monetarios": "Avisa: son muchos meses para bajarlos a mano; conviene cambiar de fuente (p. ej. SII).",
    "bde_siid": ("Abre cada enlace en el navegador y usa Archivo > Guardar como > 'Página web, solo "
                 "HTML' en {}/<codigo>.html:\n".format(relativa(config.RAW_BDE))
                 + "\n".join("        {}: {}?{}".format(
                     c, u, "&".join("{}={}".format(k, v) for k, v in config.BDE_PARAMS.items()))
                     for c, u in config.CUADROS_BDE.items())),
}

FUENTES = {
    "fred": bajar_fred,
    "fed": bajar_fed,
    "sp_cuotas": bajar_sp_cuotas,
    "sp_monetarios": bajar_sp_monetarios,
    "bde_siid": bajar_bde_siid,
}


def main(argv=None):
    parser = argparse.ArgumentParser(description="Descarga los datos originales a data/raw/.")
    parser.add_argument("--solo", nargs="+", choices=sorted(FUENTES), metavar="FUENTE",
                        help="descargar solo estas fuentes: " + ", ".join(sorted(FUENTES)))
    parser.add_argument("--forzar", action="store_true",
                        help="volver a descargar aunque el archivo ya exista")
    args = parser.parse_args(argv)

    print("Proyecto: {}".format(RAIZ))
    print("Python {}".format(sys.version.split()[0]))
    sesion = crear_sesion()
    resultados = {}
    for nombre in (args.solo or list(FUENTES)):
        print("\n[{}]".format(nombre))
        try:
            resultados[nombre] = FUENTES[nombre](sesion, args.forzar)
        except ErrorDescarga as e:
            resultados[nombre] = "ERROR: {}".format(e)
        except Exception as e:  # algo no previsto: se informa y se sigue con el resto
            resultados[nombre] = "ERROR inesperado: {}: {}".format(type(e).__name__, e)
        print("    -> {}".format(resultados[nombre]))

    print("\n" + "=" * 70 + "\nRESUMEN")
    for nombre, estado in resultados.items():
        print("  {:<14} {}".format(nombre, estado))
    carteras = revisar_carteras()
    print("  {:<14} {}".format("sp_carteras", "archivos presentes: " + ", ".join(carteras) if carteras
                               else "PENDIENTE (descarga manual, ver README)"))

    fallidas = [n for n, e in resultados.items() if e.startswith("ERROR")]
    if fallidas:
        print("\nQué hacer con las fuentes que fallaron:")
        for nombre in fallidas:
            print("  - {}: {}".format(nombre, AYUDA_MANUAL[nombre]))
        return 1
    print("\nListo. Revisa el estado de los datos con:  python main.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
