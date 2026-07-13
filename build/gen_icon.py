"""Genera build/icon.ico para BalanceLocal (barras de estadistica + destello)."""

from pathlib import Path
from PIL import Image, ImageDraw

NAVY = (30, 58, 95, 255)
NAVY2 = (21, 48, 77, 255)
TERRA = (206, 110, 97, 255)
CYAN = (110, 193, 228, 255)
GREEN = (122, 191, 143, 255)
WHITE = (255, 255, 255, 255)


def make(size: int) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    r = int(size * 0.22)
    d.rounded_rectangle([0, 0, size - 1, size - 1], radius=r, fill=NAVY)
    d.rounded_rectangle([0, int(size * 0.5), size - 1, size - 1], radius=r, fill=NAVY2)
    # tres barras (tipo grafico de actividad)
    base = int(size * 0.74)
    ancho = int(size * 0.14)
    xs = [int(size * 0.24), int(size * 0.43), int(size * 0.62)]
    alturas = [0.30, 0.46, 0.22]
    cols = [CYAN, TERRA, GREEN]
    rad = max(2, size // 20)
    for x, h, c in zip(xs, alturas, cols):
        top = base - int(size * h)
        d.rounded_rectangle([x, top, x + ancho, base], radius=rad, fill=c)
    # destello (Wrapped)
    sx, sy = int(size * 0.72), int(size * 0.28)
    s = max(3, size // 10)
    d.line([sx - s, sy, sx + s, sy], fill=WHITE, width=max(2, size // 26))
    d.line([sx, sy - s, sx, sy + s], fill=WHITE, width=max(2, size // 26))
    d.line([sx - int(s * 0.7), sy - int(s * 0.7), sx + int(s * 0.7), sy + int(s * 0.7)],
           fill=WHITE, width=max(2, size // 30))
    d.line([sx - int(s * 0.7), sy + int(s * 0.7), sx + int(s * 0.7), sy - int(s * 0.7)],
           fill=WHITE, width=max(2, size // 30))
    return img


def main() -> None:
    out = Path(__file__).resolve().parent / "icon.ico"
    sizes = [16, 24, 32, 48, 64, 128, 256]
    imgs = [make(s) for s in sizes]
    imgs[-1].save(out, format="ICO", sizes=[(s, s) for s in sizes])
    make(256).save(out.with_name("icon_preview.png"))
    print("icono ->", out)


if __name__ == "__main__":
    main()
