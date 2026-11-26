# -*- coding: utf-8 -*-
"""Formato de números y fragmentos LaTeX para el informe."""
FIN = " \\\\\n"


def es(x, dec=2):
    """Número con coma decimal y punto de miles (formato chileno)."""
    return "{:,.{}f}".format(x, dec).replace(",", "X").replace(".", ",").replace("X", ".")


def tex(x, dec=2):
    """Como es(), pero con signo menos tipográfico para LaTeX."""
    return es(x, dec).replace("-", "$-$")


def pct(x, dec=2):
    return tex(100 * x, dec) + "\\%"


def macros(ruta, valores):
    ruta.write_text("".join("\\newcommand{{\\{}}}{{{}}}\n".format(k, v) for k, v in valores.items()),
                    encoding="utf-8")
