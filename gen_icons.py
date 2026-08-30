#!/usr/bin/env python3
"""Genera los iconos PWA (icons/) a partir de icons/escudo.png.
Fondo BLANCO para diferenciar la app de la de hábitos. Ejecuta: python3 gen_icons.py"""
from PIL import Image

WHITE = (255, 255, 255)
SRC = "icons/escudo.png"


def icon(size, crest_frac, bg=WHITE, mode="RGB"):
    """size px, escudo centrado ocupando crest_frac del lado."""
    base = Image.new("RGBA", (size, size), bg + (255,))
    crest = Image.open(SRC).convert("RGBA")
    w = int(size * crest_frac)
    h = int(w * crest.height / crest.width)
    crest = crest.resize((w, h), Image.LANCZOS)
    base.alpha_composite(crest, ((size - w) // 2, (size - h) // 2))
    return base.convert(mode)


# iconos normales: el sistema ya redondea las esquinas -> cuadrado a sangre
icon(192, 0.78).save("icons/icon-192.png")
icon(512, 0.78).save("icons/icon-512.png")
# maskable: zona segura ~66% (Android recorta a círculo/squircle)
icon(512, 0.62).save("icons/icon-maskable-512.png")
# apple touch: sin transparencia
icon(180, 0.80, mode="RGB").save("icons/apple-touch-icon.png")

print("iconos generados en icons/ (fondo blanco).")
