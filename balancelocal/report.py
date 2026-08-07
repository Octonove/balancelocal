"""Informe semanal en PDF (PyMuPDF): horas por categoria y por dia, top apps y
titulares. Util para el freelance que factura por horas/proyecto."""

from __future__ import annotations

import html
from datetime import date
from pathlib import Path

from .stats import Resumen, fmt_hm, titulares

PW, PH, M = 595, 842, 42
TW = PW - 2 * M
NAVY = "#1e3a5f"
DIAS = ["lunes", "martes", "miercoles", "jueves", "viernes", "sabado", "domingo"]


class ReportError(Exception):
    pass


def _measure(html_str: str, width: float) -> float:
    import fitz
    d = fitz.open()
    try:
        pg = d.new_page(width=width + 80, height=4000)
        spare, _ = pg.insert_htmlbox(fitz.Rect(0, 0, width, 4000), html_str)
        return max(1.0, 4000 - spare)
    finally:
        d.close()


def _rgb(hx: str):
    c = hx.lstrip("#")
    return int(c[0:2], 16) / 255, int(c[2:4], 16) / 255, int(c[4:6], 16) / 255


def exportar_pdf(out_path: str, resumen: Resumen, *, lunes: date, domingo: date,
                 titulares_pre: list[str] | None = None) -> str:
    import fitz
    doc = fitz.open()
    try:
        page = doc.new_page(width=PW, height=PH)
        y = M

        def put(h: str, gap: float = 6.0):
            nonlocal y, page
            alto = _measure(h, TW)
            if y + alto > PH - M:
                page = doc.new_page(width=PW, height=PH)
                y = M
            page.insert_htmlbox(fitz.Rect(M, y, PW - M, min(y + alto + 2, PH - M)), h)
            y += alto + gap

        page.draw_rect(fitz.Rect(0, 0, PW, 86), color=_rgb(NAVY), fill=_rgb(NAVY))
        page.insert_htmlbox(fitz.Rect(M, 16, PW - M, 56),
                            '<div style="font-family:sans-serif;font-size:21px;font-weight:bold;'
                            'color:#ffffff">Tu semana de trabajo</div>')
        page.insert_htmlbox(fitz.Rect(M, 52, PW - M, 82),
                            f'<div style="font-family:sans-serif;font-size:10px;color:#b7c7da">'
                            f'{lunes.strftime("%d/%m/%Y")} - {domingo.strftime("%d/%m/%Y")} · '
                            f'BalanceLocal, 100% en tu equipo</div>')
        y = 100

        put(f'<div style="font-family:sans-serif;font-size:15px;color:#334155">'
            f'Foco total: <b>{resumen.horas_activas} horas</b></div>', 8)

        tit = titulares_pre or titulares(resumen)
        if tit:
            put('<div style="font-family:sans-serif;font-size:11px;color:#475569;line-height:1.6">'
                + "<br>".join("• " + html.escape(t) for t in tit) + "</div>", 12)

        put(f'<div style="font-family:sans-serif;font-size:14px;font-weight:bold;color:{NAVY}">'
            f'Horas por categoria</div>', 4)
        filas = [f'<tr><td style="padding:3px 6px"><b>{html.escape(c)}</b></td>'
                 f'<td style="padding:3px 6px;text-align:right"><b>{fmt_hm(s)}</b></td></tr>'
                 for c, s in resumen.top_categorias(20)]
        put('<table style="font-family:sans-serif;font-size:11px;border-collapse:collapse;'
            'width:60%">' + "".join(filas) + "</table>", 12)

        put(f'<div style="font-family:sans-serif;font-size:14px;font-weight:bold;color:{NAVY}">'
            f'Horas por dia</div>', 4)
        fdias = []
        for i in range(7):
            d = lunes.fromordinal(lunes.toordinal() + i)
            seg = resumen.por_dia.get(d.strftime("%Y-%m-%d"), 0)
            fdias.append(f'<tr><td style="padding:3px 6px">{DIAS[i]} {d.strftime("%d/%m")}</td>'
                         f'<td style="padding:3px 6px;text-align:right"><b>{fmt_hm(seg)}</b></td></tr>')
        put('<table style="font-family:sans-serif;font-size:11px;border-collapse:collapse;'
            'width:60%">' + "".join(fdias) + "</table>", 12)

        put(f'<div style="font-family:sans-serif;font-size:14px;font-weight:bold;color:{NAVY}">'
            f'Apps mas usadas</div>', 4)
        fapps = [f'<tr><td style="padding:3px 6px">{html.escape(a)}</td>'
                 f'<td style="padding:3px 6px;text-align:right">{fmt_hm(s)}</td></tr>'
                 for a, s in resumen.top_apps(10)]
        put('<table style="font-family:sans-serif;font-size:11px;border-collapse:collapse;'
            'width:60%">' + "".join(fapps) + "</table>", 12)

        pie = ('<div style="font-family:sans-serif;font-size:8px;color:#94a3b8">'
               'Generado con BalanceLocal (gratis y open source) · simplificaconia.com · '
               'La actividad se registra y guarda solo en tu equipo; nada se sube a internet.</div>')
        ph = _measure(pie, TW)
        if y + ph > PH - 20:
            page = doc.new_page(width=PW, height=PH)
        page.insert_htmlbox(fitz.Rect(M, PH - 20 - ph, PW - M, PH - 16), pie)

        try:
            Path(out_path).parent.mkdir(parents=True, exist_ok=True)
            doc.save(out_path, garbage=3, deflate=True)
        except Exception as exc:  # noqa: BLE001
            raise ReportError("No se pudo guardar el informe. Si lo tienes abierto en un "
                              "visor de PDF, cierralo y reintenta.") from exc
    finally:
        doc.close()
    return out_path
