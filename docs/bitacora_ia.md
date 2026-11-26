# Bitácora de uso de inteligencia artificial

Insumo para la declaración de uso de IA que exige el enunciado. Cada entrada indica qué
hizo la IA, cómo se verificó y qué queda por revisar por el grupo.

**Herramienta:** Claude (Anthropic), modelo Claude Fable 5.2, usado desde la aplicación de
Claude con acceso a la carpeta del proyecto y a un navegador.

## 15-11-2026: estructura del proyecto y descarga de datos

**Qué hizo la IA**
- Leyó el enunciado y propuso el plan de trabajo por módulos.
- Revisó en el navegador los sitios de la Superintendencia de Pensiones, el SIID, la BDE del
  Banco Central y la Reserva Federal para identificar las URL y los formatos de descarga.
- Escribió `src/config.py`, `src/datos.py`, `scripts/descargar_datos.py`, `main.py`, el
  README, `docs/supuestos.md` y este registro.

**Cómo se verificó**
- Los formatos de cada fuente se contrastaron con los sitios reales el 15-11-2026
  (encabezados, separadores, fechas extremas y valores de muestra).
- El script de descarga y los lectores se probaron con archivos sintéticos que reproducen
  esos formatos, comprobando valores observados en las fuentes: valor cuota de AFP Capital
  Fondo E al 31-12-2025 (66.937,35) y al 30-09-2026 (61.731,74); UF al 31-12-2025
  (39.727,96) y al 30-09-2026 (41.057,20); swaps de tasas extranjeras de los Fondos de
  Pensiones a septiembre de 2026 (compra de tasa variable 144.545 y venta 357.091 millones
  de USD).

**Pendiente de revisar por el grupo**
- Ejecutar la descarga real y confirmar que `python main.py` muestra todos los datos en OK.
- Leer `scripts/descargar_datos.py` y `src/datos.py`.

## 15-11-2026: Módulo I (P2 a P7)

**Qué hizo la IA**
- Escribió `src/modulo1.py` y `src/graficos.py`, y conectó el módulo a `main.py`.
- Resultados: 1.320 observaciones; con τ = 1, SCR total = 23,0575 pp²; τ óptimo = 2,094 años
  con SCR mínimo = 12,5808 pp² (grilla de 0,05 a 15 años, paso 0,001).

**Cómo se verificó**
- La descarga real corrió en el computador del grupo y `python main.py` mostró las seis
  fuentes en OK.
- Se revisaron visualmente los cuatro gráficos y la coherencia de los parámetros con el
  ciclo de tasas (nivel al alza desde 2022, curva invertida en 2023).
- La curva propia se comparó con las SVENPY de la Fed: diferencia absoluta media de 4 pb
  en las tres fechas de diciembre y de 9 pb al 30-09-2026.

**Pendiente de revisar por el grupo**
- Contrastar el SCR con τ = 1 con otro grupo o con el profesor.
- Confirmar las madureces del gráfico de la P3 (3 meses, 5 años y 10 años).
- Redactar la P1 y los comentarios de la P6 y la P7.

## 15-11-2026: informe (portada, introducción y Módulo I)

**Qué hizo la IA**
- Creó `informe/informe.tex` y redactó la portada, la introducción y las respuestas a las
  preguntas 1 a 7. Las cifras y tablas se leen de `output/tablas/*.tex`, que genera `main.py`.

**Cómo se verificó**
- Las cifras del texto se contrastaron con las tablas generadas por el código.

**Pendiente de revisar por el grupo**
- La pregunta 1 se redactó sin consultar fuentes: verificar contra la metodología del Tesoro
  de EE.UU. y la nota del informe H.15 antes de entregar, y agregar las referencias.
- Revisar la redacción de las preguntas 3, 6 y 7.

## 15-11-2026: Módulo II (P8 a P14)

**Qué hizo la IA**
- Escribió `src/carteras.py`, `src/modulo2.py` y `src/formato.py`; conectó el módulo a
  `main.py` y redactó la sección del Módulo II del informe.

**Cómo se verificó**
- Suma de los swaps SOFR de todas las AFP y fondos en las carteras frente al agregado del
  SIID: coinciden con diferencias menores a 2% (p. ej., marzo de 2026: 316,9 contra 320,5
  miles de millones de USD en compra fija), lo que valida el sentido de las operaciones.
- Los totales por tramo de plazo se comprueban en el código contra los totales por año de
  madurez; el signo del valor de mercado informado por la AFP es coherente con el sentido
  asignado (posiciones que reciben fija con valor negativo tras el alza de tasas).
- Rentabilidad real acumulada del fondo (-10,76%) comparada con el promedio del sistema
  citado en el enunciado (-10,39%).

**Pendiente de revisar por el grupo**
- Revisar la redacción y la evaluación del supuesto de proporcionalidad (P12).
- Verificar que la columna Dólar de la SP sea el dólar observado.

## 15-11-2026: Módulo III (P15 a P21) y anexos

**Qué hizo la IA**
- Buscó la normativa (comunicado de la SP y Compendio de Normas) y redactó la P15 y la P16.
- Escribió `src/modulo3.py` (PV01, mark-to-market, contribución) y redactó las P17 a P21 y
  los anexos del informe.

**Cómo se verificó**
- Función de valorización probada con casos conocidos: un swap a la par vale cero; un bono
  a 5 años con cupón 4% descontado al 5% reproduce el precio calculado a mano; un contrato
  vencido vale cero.
- El valor del modelo se comparó con el valor de mercado informado en las carteras:
  correlación de 0,95 entre los cambios mensuales; la diferencia de nivel es coherente con
  el swap spread no modelado.

**Pendiente de revisar por el grupo**
- La P21 es un borrador: la opinión debe ser del grupo.
- Leer el texto de la Resolución Exenta N.º 549 y de la NCG N.º 362 y confirmar la P15.
- Completar el enlace al repositorio y la declaración de uso de IA; decidir la P22.
