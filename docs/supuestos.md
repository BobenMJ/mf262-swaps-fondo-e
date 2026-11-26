# Supuestos y decisiones metodológicas

Registro vivo. Cada punto indica la pregunta del enunciado a la que afecta. Lo marcado
*por verificar* o *por decidir* todavía no está resuelto por el grupo.

## Datos (15-11-2026)

1. **CMT (P2).** Series diarias DGS1MO, DGS3MO, DGS6MO, DGS1, DGS2, DGS3, DGS5, DGS7, DGS10,
   DGS20 y DGS30 de FRED, del 01-10-2016 al 30-09-2026. "Último dato disponible de cada mes"
   se toma como el último día del mes en que las 11 madureces tienen dato, para que todas
   las regresiones mensuales usen una misma fecha y 11 observaciones (120 meses × 11 = 1.320).
2. **Curva de la Fed (P7).** Archivo `feds200628.csv` del Federal Reserve Board, columnas
   SVENPY01 a SVENPY30 (tasas al valor par, convención *coupon-equivalent*).
3. **Valor cuota y patrimonio (P8).** CSV de la Superintendencia de Pensiones para el Fondo E.
   Al revisar la fuente, los valores estaban confirmados hasta el 31-10-2026, de modo que
   toda la ventana del análisis (hasta el 30-09-2026) usa valores confirmados. El patrimonio
   viene en pesos.
4. **UF y tipo de cambio (P8 y P20).** Página "Valores monetarios" de la Superintendencia de
   Pensiones (columnas Dólar y U.F., diarias). *Por verificar:* que la columna Dólar
   corresponda al dólar observado del Banco Central.
5. **SIID (P9 y P12).** Se usan los cuadros de la Base de Datos Estadísticos (BDE) del Banco
   Central, que publica las series del Monitor de Derivados del SIID:
   - `DER_RES_POS_02`: montos vigentes en derivados de los Fondos de Pensiones por subyacente.
   - `DER_TAS_FP_STO_01`: swaps de tasas de interés extranjeras (total, compra, venta y neto,
     y su desglose por sector contraparte).

   Motivo: los Excel descargables del Monitor de Fondos de Pensiones tenían fecha 22-05-2026
   y llegaban solo a abril de 2026, mientras que la BDE llega a septiembre de 2026. Para
   abril de 2026 ambas fuentes difieren levemente (total con no residentes: 617.585 en el
   Excel y 619.930 en la BDE, en millones de USD), lo que es consistente con revisiones.
6. **Unidad del SIID (P9).** Millones de USD, saldos a fin de mes. La BDE los muestra sin
   decimales.
7. **Sentido de las operaciones en el SIID (P12).** El SIID clasifica según la tasa variable:
   "compra tasa variable" equivale a pagar fija, es decir, a la **venta fija** del enunciado;
   "venta tasa variable" equivale a la **compra fija**.
8. **Carteras históricas (P10 a P14).** Descarga manual desde la Superintendencia de Pensiones
   (formulario con reCAPTCHA). La página indicaba "Fecha de cierre de la Base de Datos:
   01/JUN/2026". *Por determinar al abrir los archivos:* cuál es la última cartera mensual
   publicada (la cartera base de la P11).

## Módulo I (15-11-2026)

9. **Estimación (P4 y P5).** Para cada τ, los β de cada mes se estiman por MCO sobre las 11
   CMT del último día hábil del mes. τ se busca en una grilla de 0,05 a 15 años con paso
   0,001; el óptimo minimiza la suma de los SCR de los 120 meses.
10. **Comparación con la Fed (P7).** Las SVENPY se toman en la misma fecha que las CMT de
    cada mes (29-12-2023, 31-12-2024, 31-12-2025 y 30-09-2026), para madureces de 1 a 30 años.

## Módulo II (15-11-2026)

11. **Extracto de carteras (P10).** La base completa de la SP (117 MB) no se incluye en el
    proyecto: pesa más que el límite de GitHub y su manual pide no redistribuirla. Se
    incluyen dos extractos en `data/processed/`: los registros del Fondo E de AFP Capital
    con el descriptor SFRUS$360 y un agregado del sistema por fecha, AFP, fondo y sentido.
12. **Cartera base (P11).** Junio de 2026 (cierre del 30-06-2026), la última publicada.
13. **Sentido (P10 y P11).** Compra fija si la tasa de la contraparte es fija y la del fondo
    es SOFR; venta fija en el caso contrario. Los registros con nocional cero se excluyen.
14. **Nemotécnico.** Tres letras de la contraparte, `US$`, vencimiento (aammdd) e inicio
    (aammdd). Trece registros no traen fecha de inicio; no se usa en los cálculos.
15. **Plazo residual (P13).** Días entre la fecha de la cartera y el vencimiento, dividido
    por 365,25; tramo más cercano y, en empate, el mayor.
16. **Meses estimados (P12).** Julio a septiembre de 2026: nocional de la cartera base por
    el factor del agregado del SIID de cada sentido, manteniendo la composición de la
    cartera base por año de madurez y por tramo. Se fechan al último día del mes.
17. **SIID por subyacente (P9).** Las cinco categorías suman el total publicado salvo
    redondeos y una diferencia de 0,1% en septiembre de 2025, propia de la fuente.

## Módulo III (15-11-2026)

18. **Valorización (P17 y P19).** Swap que recibe fija = bono fijo menos bono flotante a la
    par. Cupón fijo anual ACT/360 en los aniversarios del vencimiento; pago único en
    contratos de hasta un año; precios limpios (sin carry). Las carteras no informan la
    frecuencia de pago: se supone la convención habitual de los swaps SOFR en dólares.
19. **Descuento.** Cada contrato se descuenta a la tasa par de Nelson y Siegel de su plazo
    residual (mínimo 1 mes), llevada de composición semestral a anual. No se modela el
    swap spread; por eso el nivel del valor difiere del informado por la AFP (-299 contra
    -137 millones de USD en junio de 2026), pero los cambios mensuales se parecen
    (correlación 0,95).
20. **PV01 (P17).** Cambio de valor ante un alza paralela de 1 pb de la curva par.
21. **Mark-to-market (P19).** Cartera del cierre anterior valorizada al inicio y al cierre
    del mes; los contratos envejecen y los que vencen terminan en cero. Agosto y septiembre
    de 2026 usan posiciones estimadas, cuyas fechas se desplazan para mantener las
    duraciones de la cartera base.
22. **Contribución (P20).** Nominal: MTM en pesos (dólar de cierre de la SP) sobre el
    patrimonio al inicio del mes; se compara con la rentabilidad nominal del valor cuota.
23. **Regulación (P15).** Fuentes: comunicado de la SP del 09-04-2026 y Compendio de Normas,
    Libro IV, Título I, Letra A, Capítulo III. No se leyó el texto de la Resolución 549.

## Por decidir

- P3: se usaron 3 meses, 5 años y 10 años como corto, mediano y largo plazo; falta que el grupo lo confirme.
- P21: la evaluación es un borrador; debe reflejar la opinión del grupo.
- P22: decidir si se incluye la autorización para compartir el informe.
