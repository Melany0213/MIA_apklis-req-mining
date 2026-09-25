"""Genera los archivos de marca de ECO (isotipo, favicon y logotipo).

Los SVG de `webapp/static/img/` y los PNG de `docs/marca/` NO se editan a mano:
salen de aqui. Asi la marca es reproducible como cualquier otro artefacto del
proyecto, y basta cambiar un parametro de este archivo para regenerarla entera.

El rasterizador propio (sin dependencias: solo `zlib` y `struct` de la
biblioteca estandar) existe porque los PNG hacen falta para el documento de
tesis, que no inserta SVG comodamente, y no queremos añadir una dependencia
pesada de renderizado solo para eso.

Uso:
    python scripts/marca.py
"""
from __future__ import annotations
import math, struct, zlib
from pathlib import Path

NAVY, AZUL = "#1a3a6e", "#2563c4"
BLANCO = "#ffffff"
GRAD = "url(#fondo)"


def seg(x1, y1, x2, y2, w, color, op=1.0):
    return ("seg", (x1, y1, x2, y2, w), color, op)


def arco(cx, cy, r, a0, a1, w, color, op=1.0):
    return ("arco", (cx, cy, r, a0, a1, w), color, op)


def anillo(cx, cy, r, w, color, op=1.0):
    return ("arco", (cx, cy, r, -180, 180, w), color, op)


def rrect(x0, y0, x1, y1, r, color, op=1.0):
    return ("rrect", (x0, y0, x1, y1, r), color, op)


def tri(ax, ay, bx, by, cx, cy, color, op=1.0):
    return ("tri", (ax, ay, bx, by, cx, cy), color, op)


def _dist_seg(px, py, x1, y1, x2, y2):
    vx, vy = x2 - x1, y2 - y1
    largo = vx * vx + vy * vy
    t = 0.0 if largo == 0 else max(0.0, min(1.0, ((px - x1) * vx + (py - y1) * vy) / largo))
    return math.hypot(px - (x1 + t * vx), py - (y1 + t * vy))


def dentro(fig, x, y):
    tipo, p = fig[0], fig[1]
    if tipo == "seg":
        x1, y1, x2, y2, w = p
        return _dist_seg(x, y, x1, y1, x2, y2) <= w / 2
    if tipo == "arco":
        cx, cy, r, a0, a1, w = p
        d = math.hypot(x - cx, y - cy)
        ang = math.degrees(math.atan2(y - cy, x - cx))
        barrido = (a1 - a0) % 360 or 360
        if abs(d - r) <= w / 2 and ((ang - a0) % 360) <= barrido:
            return True
        for a in (a0, a1):
            ex = cx + r * math.cos(math.radians(a))
            ey = cy + r * math.sin(math.radians(a))
            if math.hypot(x - ex, y - ey) <= w / 2:
                return True
        return False
    if tipo == "rrect":
        x0, y0, x1, y1, r = p
        qx = min(max(x, x0 + r), x1 - r)
        qy = min(max(y, y0 + r), y1 - r)
        return math.hypot(x - qx, y - qy) <= r
    if tipo == "tri":
        ax, ay, bx, by, cx, cy = p
        d1 = (bx - ax) * (y - ay) - (by - ay) * (x - ax)
        d2 = (cx - bx) * (y - by) - (cy - by) * (x - bx)
        d3 = (ax - cx) * (y - cy) - (ay - cy) * (x - cx)
        negativos = d1 < 0 or d2 < 0 or d3 < 0
        positivos = d1 > 0 or d2 > 0 or d3 > 0
        return not (negativos and positivos)
    raise ValueError(tipo)


def svg_de(fig):
    tipo, p, color, op = fig
    o = f' opacity="{op:g}"' if op != 1.0 else ""
    if tipo == "seg":
        x1, y1, x2, y2, w = p
        return (f'<path d="M {x1:g} {y1:g} L {x2:g} {y2:g}" fill="none" stroke="{color}"'
                f' stroke-width="{w:g}" stroke-linecap="round"{o}/>')
    if tipo == "arco":
        cx, cy, r, a0, a1, w = p
        barrido = (a1 - a0) % 360 or 360
        if barrido >= 359.9:
            return (f'<circle cx="{cx:g}" cy="{cy:g}" r="{r:g}" fill="none" stroke="{color}"'
                    f' stroke-width="{w:g}"{o}/>')
        x1 = cx + r * math.cos(math.radians(a0))
        y1 = cy + r * math.sin(math.radians(a0))
        x2 = cx + r * math.cos(math.radians(a1))
        y2 = cy + r * math.sin(math.radians(a1))
        grande = 1 if barrido > 180 else 0
        return (f'<path d="M {x1:.2f} {y1:.2f} A {r:g} {r:g} 0 {grande} 1 {x2:.2f} {y2:.2f}"'
                f' fill="none" stroke="{color}" stroke-width="{w:g}" stroke-linecap="round"{o}/>')
    if tipo == "rrect":
        x0, y0, x1, y1, r = p
        return (f'<rect x="{x0:g}" y="{y0:g}" width="{x1 - x0:g}" height="{y1 - y0:g}"'
                f' rx="{r:g}" fill="{color}"{o}/>')
    if tipo == "tri":
        ax, ay, bx, by, cx, cy = p
        return f'<path d="M {ax:g} {ay:g} L {bx:g} {by:g} L {cx:g} {cy:g} Z" fill="{color}"{o}/>'
    raise ValueError(tipo)


def disco(cx, cy, r, color, op=1.0):
    """Circulo relleno (se dibuja como un arco cerrado de grosor r)."""
    return ("arco", (cx, cy, r / 2, -180, 180, r), color, op)


def capsula(x0, y0, x1, y1, color, op=1.0):
    """Renglon de esquinas totalmente redondeadas."""
    return rrect(x0, y0, x1, y1, (y1 - y0) / 2, color, op)


def eco_arcos(cx, cy, pares, grosor, apertura=52.0):
    """Arcos a ambos lados: el eco de la multitud de usuarios, que va y vuelve."""
    figs = []
    for r, op in pares:
        figs.append(arco(cx, cy, r, -apertura, apertura, grosor, BLANCO, op))
        figs.append(arco(cx, cy, r, 180 - apertura, 180 + apertura, grosor, BLANCO, op))
    return figs


def globo(x0, y0, x1, y1, r, rabito):
    """Globo de dialogo: la opinion cruda del usuario."""
    ax, ay, bx, by, cx, cy = rabito
    return [rrect(x0, y0, x1, y1, r, BLANCO), tri(ax, ay, bx, by, cx, cy, BLANCO)]


def renglones(filas):
    """Lo que el metodo saca de la opinion: renglones de distinto peso.

    Los tres pesos no son decorativos — representan las tres etiquetas del
    dominio (RF, RNF, Ruido), que es justo lo que la fase 4 separa.
    """
    return [capsula(x0, y0, x1, y1, NAVY, op) for x0, y0, x1, y1, op in filas]


def sello_validacion(cx, cy, r, tic):
    """El tic de la fase 5: nada sale del sistema sin que una persona lo apruebe."""
    (ax, ay), (bx, by), (dx, dy), grosor = tic
    return [
        disco(cx, cy, r, BLANCO),
        seg(ax, ay, bx, by, grosor, NAVY),
        seg(bx, by, dx, dy, grosor, NAVY),
    ]


def isotipo():
    """La historia completa: la opinion entra, sale clasificada, un humano la valida.

    De fuera hacia dentro: el eco de la multitud (arcos), la opinion (globo),
    los requisitos ya separados por tipo (renglones) y la validacion (sello).
    """
    figs = [rrect(0, 0, 512, 512, 112, GRAD)]
    figs += eco_arcos(236, 204, [(180.0, 0.5)], 22, apertura=44)
    figs += eco_arcos(236, 204, [(214.0, 0.25)], 22, apertura=40)
    figs += globo(96, 112, 376, 296, 52, (152, 284, 138, 352, 216, 296))
    figs += renglones([
        (136, 148, 300, 178, 1.0),
        (136, 196, 336, 226, 0.5),
        (136, 244, 262, 274, 0.26),
    ])
    figs += sello_validacion(388, 356, 76, ((362, 356), (380, 376), (418, 328), 20))
    return figs


def favicon():
    """Version reducida: a 16-32 px solo sobreviven globo, dos renglones y sello."""
    figs = [rrect(0, 0, 512, 512, 96, GRAD)]
    figs += globo(72, 118, 396, 330, 56, (132, 312, 112, 402, 236, 322))
    figs += renglones([
        (120, 168, 300, 208, 1.0),
        (120, 238, 348, 278, 0.45),
    ])
    figs += sello_validacion(390, 362, 104, ((354, 362), (378, 390), (430, 320), 26))
    return figs


def letras_eco():
    """ECO en trazo geometrico: la C y la O son los mismos arcos del isotipo."""
    w = 34
    return [
        seg(392, 96, 392, 264, w, NAVY),
        seg(392, 96, 496, 96, w, NAVY),
        seg(392, 180, 474, 180, w, NAVY),
        seg(392, 264, 496, 264, w, NAVY),
        arco(628, 180, 84, 48, 312, w, NAVY),
        anillo(844, 180, 84, w, NAVY),
    ]


def envolver(figs, ancho, alto, con_gradiente=True, prefijo=""):
    defs = ""
    if con_gradiente:
        defs = ('  <defs>\n    <linearGradient id="fondo" x1="0" y1="0" x2="1" y2="1">\n'
                f'      <stop offset="0" stop-color="{NAVY}"/>\n'
                f'      <stop offset="1" stop-color="{AZUL}"/>\n'
                '    </linearGradient>\n  </defs>\n')
    cuerpo = "\n".join("  " + svg_de(f) for f in figs)
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {ancho} {alto}" '
            f'width="{ancho}" height="{alto}" role="img" '
            f'aria-label="ECO, Escucha Colectiva de Opiniones">\n'
            f'  <title>ECO — Escucha Colectiva de Opiniones</title>\n'
            f'{defs}{prefijo}{cuerpo}\n</svg>\n')


def svg_logotipo():
    """Lockup horizontal: el isotipo reducido a la izquierda y ECO a la derecha."""
    escala = 0.62
    tile = "\n".join("    " + svg_de(f) for f in isotipo())
    grupo = f'  <g transform="translate(0,20) scale({escala:g})">\n{tile}\n  </g>\n'
    return envolver(letras_eco(), 980, 360, con_gradiente=True, prefijo=grupo)


def rasterizar(ruta, figs, ancho, alto, salida_ancho, fondo=(255, 255, 255), m=3, extra=None):
    esc = ancho / salida_ancho
    salida_alto = int(round(alto / esc))
    a_navy = tuple(int(NAVY[i:i + 2], 16) for i in (1, 3, 5))
    a_azul = tuple(int(AZUL[i:i + 2], 16) for i in (1, 3, 5))
    todas = list(extra or []) + list(figs)
    filas = []
    for py in range(salida_alto):
        fila = bytearray([0])
        for px in range(salida_ancho):
            ac = [0.0, 0.0, 0.0]
            n = 0
            for sy in range(m):
                for sx in range(m):
                    x = (px + (sx + .5) / m) * esc
                    y = (py + (sy + .5) / m) * esc
                    n += 1
                    col = list(fondo)
                    for fig in todas:
                        transformada = fig
                        if len(fig) == 5:
                            tx, ty, s = fig[4]
                            transformada = fig[:4]
                            if not dentro(transformada, (x - tx) / s, (y - ty) / s):
                                continue
                        elif not dentro(fig, x, y):
                            continue
                        c = fig[2]
                        if c == GRAD:
                            t = (x / ancho + y / alto) / 2
                            nc = [a_navy[i] + (a_azul[i] - a_navy[i]) * t for i in range(3)]
                        else:
                            nc = [int(c[i:i + 2], 16) for i in (1, 3, 5)]
                        op = fig[3]
                        col = [col[i] * (1 - op) + nc[i] * op for i in range(3)]
                    for i in range(3):
                        ac[i] += col[i]
            fila += bytes(max(0, min(255, int(round(c / n)))) for c in ac)
        filas.append(bytes(fila))

    def trozo(t, d):
        return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xFFFFFFFF)

    Path(ruta).write_bytes(
        b"\x89PNG\r\n\x1a\n"
        + trozo(b"IHDR", struct.pack(">IIBBBBB", salida_ancho, salida_alto, 8, 2, 0, 0, 0))
        + trozo(b"IDAT", zlib.compress(b"".join(filas), 9))
        + trozo(b"IEND", b"")
    )


if __name__ == "__main__":
    raiz = Path(__file__).resolve().parents[1]
    estaticos = raiz / "webapp" / "static" / "img"
    marca = raiz / "docs" / "marca"
    estaticos.mkdir(parents=True, exist_ok=True)
    marca.mkdir(parents=True, exist_ok=True)

    (estaticos / "eco-isotipo.svg").write_text(envolver(isotipo(), 512, 512), encoding="utf-8")
    (estaticos / "eco-favicon.svg").write_text(envolver(favicon(), 512, 512), encoding="utf-8")
    (estaticos / "eco-logotipo.svg").write_text(svg_logotipo(), encoding="utf-8")

    # PNG para el documento de tesis y para cualquier sitio que no acepte SVG.
    rasterizar(marca / "eco-isotipo-512.png", isotipo(), 512, 512, 512)
    escala = 0.62
    tile = [(f[0], f[1], f[2], f[3], (0, 20, escala)) for f in isotipo()]
    rasterizar(marca / "eco-logotipo-980.png", letras_eco(), 980, 360, 980, extra=tile)

    print("marca regenerada en webapp/static/img/ y docs/marca/")
