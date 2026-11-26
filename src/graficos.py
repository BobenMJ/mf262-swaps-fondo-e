# -*- coding: utf-8 -*-
"""Estilo común de los gráficos del informe."""
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

AZUL, NARANJA, VERDE, AMARILLO = "#2a78d6", "#eb6834", "#1baf7a", "#eda100"
MAGENTA = "#e87ba4"
CATEGORICA = [AZUL, NARANJA, VERDE, AMARILLO, MAGENTA]
# Un solo tono, de claro a oscuro, para categorías ordenadas (plazos)
RAMPA_AZUL = ["#b7d3f6", "#86b6ef", "#6da7ec", "#5598e7", "#2a78d6", "#256abf", "#184f95", "#0d366b"]
TEXTO, TEXTO_2, GRILLA = "#0b0b0b", "#52514e", "#e4e3df"
SUPERFICIE = "#fcfcfb"

plt.rcParams.update({
    "figure.dpi": 110, "savefig.dpi": 200, "savefig.bbox": "tight",
    "font.size": 10, "axes.titlesize": 11, "axes.titleweight": "bold",
    "axes.edgecolor": TEXTO_2, "axes.labelcolor": TEXTO_2, "text.color": TEXTO,
    "xtick.color": TEXTO_2, "ytick.color": TEXTO_2,
    "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "grid.color": GRILLA, "grid.linewidth": 0.8,
    "lines.linewidth": 2.0, "legend.frameon": False,
})


def guardar(fig, ruta):
    ruta.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(ruta)
    plt.close(fig)
    return ruta
