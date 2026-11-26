Proyecto del curso Mercados Financieros (EAE3301, Instituto de Economía UC, profesor
Jaime Casassus). Fondo analizado: **Fondo E de AFP Capital**.

> **Estado (26-11-2026):** están implementados los tres módulos y el informe está completo
> en borrador. Falta la revisión del grupo (ver `docs/bitacora_ia.md`).

## Estructura

```
main.py                      Punto de entrada: regenera tablas y gráficos (sin internet)
requirements.txt             Dependencias
src/config.py                Rutas, fechas del enunciado y fuentes
src/datos.py                 Lectura de los datos originales
scripts/descargar_datos.py   Descarga opcional de los datos (requiere internet)
data/raw/                    Datos originales, tal como los entrega cada fuente
data/raw/registro_descargas.csv   URL, fecha de descarga, tamaño y SHA-256 de cada archivo
data/processed/              Datos intermedios generados por el código
output/figuras, output/tablas     Resultados que usa el informe
informe/informe.tex          Informe (LaTeX); informe/informe.pdf es el PDF compilado
docs/supuestos.md            Supuestos y decisiones metodológicas
docs/bitacora_ia.md          Registro del uso de inteligencia artificial
```

## Instalación

Requiere Python 3.9 o superior. Desde la raíz del proyecto:

```bash
python3 -m venv .venv
source .venv/bin/activate          # en Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Ejecución

```bash
python main.py
```

`main.py` trabaja solo con los archivos de `data/raw/`: no necesita internet ni claves.
Todas las rutas son relativas a la raíz del proyecto.

## Datos

| Fuente | Contenido | Archivo en `data/raw/` | Obtención |
|---|---|---|---|
| FRED (Federal Reserve Bank of St. Louis) | Tasas CMT diarias, 11 madureces, oct-2016 a sep-2026 | `fred/cmt_diario.csv` | Script (API, con clave) |
| Federal Reserve Board | Curva de Gürkaynak, Sack y Wright (SVENPY) | `fed/feds200628.csv` | Script |
| Superintendencia de Pensiones | Valor cuota y patrimonio del Fondo E, 2023-2026 | `sp/vcfE_2023-2026.csv` | Script |
| Superintendencia de Pensiones | UF y dólar diarios, dic-2023 a sep-2026 | `sp/valores_monetarios/AAAA-MM.html` | Script |
| Banco Central de Chile, BDE (estadísticas del SIID) | Derivados de los Fondos de Pensiones, millones de USD | `siid_bde/DER_RES_POS_02.html`, `siid_bde/DER_TAS_FP_STO_01.html` | Script |
| Superintendencia de Pensiones | Carteras históricas de inversión y su documentación | `sp_carteras/` | Manual |

### Repetir la descarga (opcional)

```bash
python scripts/descargar_datos.py            # todas las fuentes automáticas
python scripts/descargar_datos.py --forzar   # vuelve a bajar aunque el archivo exista
```

El script no vuelve a bajar lo que ya existe, valida el contenido de cada archivo y deja
anotada la fecha de descarga en `data/raw/registro_descargas.csv`.

**Clave de FRED.** La descarga de FRED lee la clave desde `FRED_API_KEY.env`, en la raíz,
con una sola línea `FRED_API_KEY=<clave de 32 caracteres>`. Ese archivo está excluido del
repositorio (`.gitignore`) y no debe incluirse en ningún ZIP. La clave es gratuita y se
pide en https://fredaccount.stlouisfed.org/apikeys.

**Carteras históricas.** La base completa (`chistAFP.zip`, 117 MB) no se incluye en el
repositorio; `main.py` funciona sin ella porque usa los extractos de `data/processed/`
(`src/carteras.py` los regenera si el ZIP está presente). El formulario de la Superintendencia usa reCAPTCHA, por lo que se
descargan a mano. Los pasos están en `data/raw/sp_carteras/LEEME.txt`.

## Informe

El informe se compila después de ejecutar `main.py`, que genera sus tablas y gráficos:

```bash
cd informe && latexmk -pdf informe.tex
```

## Supuestos y uso de IA

Los supuestos y las decisiones metodológicas se registran en `docs/supuestos.md`. El uso
de inteligencia artificial y la forma en que se verificó cada resultado, en
`docs/bitacora_ia.md`.
