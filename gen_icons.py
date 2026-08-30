#!/usr/bin/env python3
"""Genera los iconos PWA (icons/). Ejecuta: python3 gen_icons.py"""
from PIL import Image, ImageDraw, ImageFont
import os

NAVY = (22, 52, 94)
NAVY2 = (27, 66, 117)
GOLD = (212, 175, 55)
WHITE = (245, 248, 252)

FONT_CANDIDATES = [
    "/System/Library/Fonts/Supplemental/Arial Narrow Bold.ttf",
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    "/System/Library/Fonts/HelveticaNeue.ttc",
    "/Library/Fonts/Arial Bold.ttf",
]

def load_font(size):
    for p in FONT_CANDIDATES:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                pass
    return ImageFont.load_default()

def make(size, maskable=False):
    scale = 4
    S = size * scale
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    # fondo
    if maskable:
        d.rectangle([0, 0, S, S], fill=NAVY)
    else:
        radius = int(S * 0.22)
        d.rounded_rectangle([0, 0, S - 1, S - 1], radius=radius, fill=NAVY)

    # degradado diagonal simple (bandas)
    for i in range(S):
        t = i / S
        col = tuple(int(NAVY[c] + (NAVY2[c] - NAVY[c]) * t) for c in range(3))
        d.line([(0, i), (i, 0)], fill=col + (255,), width=1)

    # patron de rayas diagonales tenues
    stripe = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    ds = ImageDraw.Draw(stripe)
    step = int(S * 0.14)
    for x in range(-S, S * 2, step):
        ds.line([(x, 0), (x + S, S)], fill=(255, 255, 255, 14), width=int(S * 0.02))
    img.alpha_composite(stripe)

    # anillo dorado
    inset = int(S * (0.20 if maskable else 0.14))
    d.ellipse([inset, inset, S - inset, S - inset], outline=GOLD, width=int(S * 0.035))

    # monograma
    f = load_font(int(S * (0.30 if maskable else 0.34)))
    text = "CD"
    bbox = d.textbbox((0, 0), text, font=f)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    d.text(((S - tw) / 2 - bbox[0], (S - th) / 2 - bbox[1] - int(S * 0.02)),
           text, font=f, fill=WHITE)

    # acento dorado (barra inferior)
    by = int(S * 0.72)
    d.rounded_rectangle([S * 0.34, by, S * 0.66, by + int(S * 0.045)],
                        radius=int(S * 0.02), fill=GOLD)

    img = img.resize((size, size), Image.LANCZOS)
    return img

os.makedirs("icons", exist_ok=True)
make(192).save("icons/icon-192.png")
make(512).save("icons/icon-512.png")
make(512, maskable=True).save("icons/icon-maskable-512.png")
# apple touch icon (fondo opaco, sin transparencia)
apple = Image.new("RGB", (180, 180), NAVY)
apple.paste(make(180), (0, 0), make(180))
apple.save("icons/apple-touch-icon.png")
print("iconos generados en icons/")
