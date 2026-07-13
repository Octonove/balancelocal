"""Tarjetas 'Wrapped' (PNG verticales 1080x1920) con Pillow. Cada funcion recibe
el Resumen y devuelve una imagen PIL. Estilo de marca navy + terracota."""

from __future__ import annotations

from pathlib import Path

from .stats import Resumen, fmt_hm, franja_horaria

W, H = 1080, 1920
NAVY = (30, 58, 95)
NAVY2 = (21, 48, 77)
TERRA = (206, 110, 97)
CYAN = (110, 193, 228)
WHITE = (255, 255, 255)
MUTED = (183, 199, 218)

_PALETA = [TERRA, CYAN, (122, 191, 143), (240, 196, 106), (176, 148, 214),
           (233, 150, 122), (120, 200, 200), (200, 160, 130)]


def _font(size: int, bold: bool = False):
    from PIL import ImageFont
    fuentes = (["C:/Windows/Fonts/segoeuib.ttf", "C:/Windows/Fonts/arialbd.ttf"] if bold
               else ["C:/Windows/Fonts/segoeui.ttf", "C:/Windows/Fonts/arial.ttf"])
    for fp in fuentes:
        try:
            return ImageFont.truetype(fp, size)
        except OSError:
            continue
    try:
        return ImageFont.load_default(size)     # Pillow >=10.1: respeta el tamano
    except TypeError:
        return ImageFont.load_default()


def _ajustar(d, texto: str, font, ancho_max: float) -> str:
    """Recorta el texto con '…' hasta que quepa en `ancho_max`. Evita que un
    nombre de app largo se salga del canvas."""
    if d.textlength(texto, font=font) <= ancho_max:
        return texto
    while texto and d.textlength(texto + "…", font=font) > ancho_max:
        texto = texto[:-1]
    return (texto + "…") if texto else ""


def _fondo():
    from PIL import Image, ImageDraw
    img = Image.new("RGB", (W, H), NAVY)
    d = ImageDraw.Draw(img)
    for i in range(H):
        f = i / H
        d.line([(0, i), (W, i)], fill=(int(NAVY[0] * (1 - f) + NAVY2[0] * f),
                                       int(NAVY[1] * (1 - f) + NAVY2[1] * f),
                                       int(NAVY[2] * (1 - f) + NAVY2[2] * f)))
    return img, d


def _centrado(d, y, texto, font, fill):
    w = d.textlength(texto, font=font)
    d.text(((W - w) / 2, y), texto, font=font, fill=fill)


def portada(resumen: Resumen, rango: str) -> "object":
    img, d = _fondo()
    _centrado(d, 150, "TU SEMANA EN EL PC", _font(46, True), CYAN)
    _centrado(d, 220, rango, _font(34), MUTED)
    _centrado(d, 640, f"{resumen.horas_activas}", _font(300, True), TERRA)
    _centrado(d, 1000, "horas de foco", _font(56, True), WHITE)
    tc = resumen.top_categorias(1)
    if tc:
        _centrado(d, 1160, f"sobre todo en {tc[0][0]}", _font(40), MUTED)
    _centrado(d, 1780, "BalanceLocal · 100% en tu PC", _font(28), MUTED)
    return img


def top_apps(resumen: Resumen) -> "object":
    img, d = _fondo()
    _centrado(d, 150, "TUS 5 APPS ESTRELLA", _font(46, True), CYAN)
    apps = resumen.top_apps(5)
    maxs = max((s for _a, s in apps), default=1)
    y = 420
    for i, (app, seg) in enumerate(apps):
        col = _PALETA[i % len(_PALETA)]
        d.text((110, y), f"{i + 1}", font=_font(60, True), fill=col)
        f_app = _font(52, True)
        d.text((230, y + 6), _ajustar(d, app, f_app, W - 260), font=f_app, fill=WHITE)
        bw = int((W - 340) * (seg / maxs))
        d.rounded_rectangle([230, y + 82, 230 + max(24, bw), y + 120], radius=18, fill=col)
        d.text((230, y + 128), fmt_hm(seg), font=_font(34), fill=MUTED)
        y += 250
    _centrado(d, 1780, "BalanceLocal · 100% en tu PC", _font(28), MUTED)
    return img


def reparto(resumen: Resumen) -> "object":
    img, d = _fondo()
    _centrado(d, 150, "EN QUÉ SE FUE EL TIEMPO", _font(46, True), CYAN)
    cats = resumen.top_categorias(8)
    total = sum(s for _c, s in cats) or 1
    y = 380
    for i, (cat, seg) in enumerate(cats):
        col = _PALETA[i % len(_PALETA)]
        pct = seg / total * 100
        d.text((110, y), cat, font=_font(46, True), fill=WHITE)
        d.text((W - 110 - d.textlength(f"{pct:.0f}%", font=_font(46, True)), y),
               f"{pct:.0f}%", font=_font(46, True), fill=col)
        bw = int((W - 220) * (seg / total))
        d.rounded_rectangle([110, y + 62, 110 + max(20, bw), y + 96], radius=16, fill=col)
        y += 175
    _centrado(d, 1780, "BalanceLocal · 100% en tu PC", _font(28), MUTED)
    return img


def logros(resumen: Resumen) -> "object":
    img, d = _fondo()
    _centrado(d, 150, "TUS RÉCORDS", _font(46, True), CYAN)
    h = resumen.hora_de_oro()
    racha = resumen.racha_dias()
    bloques = []
    if h is not None:
        bloques.append(("Tu hora de oro", franja_horaria(h)))
    if racha >= 1:
        bloques.append(("Racha de foco", f"{racha} día(s) seguidos"))
    top = resumen.top_apps(1)
    if top:
        bloques.append(("App campeona", f"{top[0][0]} · {fmt_hm(top[0][1])}"))
    bloques.append(("Foco total", f"{resumen.horas_activas} h esta semana"))
    y = 420
    for i, (titulo, valor) in enumerate(bloques):
        col = _PALETA[i % len(_PALETA)]
        d.rounded_rectangle([90, y, W - 90, y + 260], radius=32, fill=NAVY2)
        # acento de color dibujado (evita 'tofu' de emojis que Pillow no renderiza)
        d.rounded_rectangle([140, y + 70, 230, y + 190], radius=24, fill=col)
        d.text((155, y + 95), str(i + 1), font=_font(70, True), fill=NAVY)
        d.text((300, y + 55), titulo, font=_font(40), fill=MUTED)
        f_val = _font(56, True)
        d.text((300, y + 120), _ajustar(d, valor, f_val, W - 340), font=f_val, fill=WHITE)
        y += 320
    return img


def generar_todas(resumen: Resumen, rango: str, out_dir: str) -> list[str]:
    """Genera las 4 tarjetas PNG y devuelve sus rutas."""
    d = Path(out_dir)
    d.mkdir(parents=True, exist_ok=True)
    rutas = []
    for i, fn in enumerate((portada, top_apps, reparto, logros), 1):
        img = fn(resumen) if fn is not portada else portada(resumen, rango)
        p = d / f"wrapped_{i}.png"
        img.save(p)
        rutas.append(str(p))
    return rutas
