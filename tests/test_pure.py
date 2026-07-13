"""Tests de logica pura de BalanceLocal (categorizacion, estadisticas, store,
tarjetas, informe). Ejecutar:  python -m pytest tests/ -q"""

import sys
from datetime import date, datetime
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from balancelocal import cards, categorize, report, stats  # noqa: E402
from balancelocal.stats import Muestra  # noqa: E402
from balancelocal.store import Store  # noqa: E402


# --------------------------------------------------------------- categorize
def test_categoria_por_app():
    assert categorize.categoria("chrome.exe") == "Navegador"
    assert categorize.categoria("WINWORD.EXE") == "Documentos"
    assert categorize.categoria("Code.exe") == "Desarrollo"
    assert categorize.categoria("Teams.exe") == "Reuniones"
    assert categorize.categoria("cosa_rara.exe") == "Otros"


def test_categoria_titulo_gana():
    # una reunion abierta en el navegador se cuenta como Reuniones
    assert categorize.categoria("chrome.exe", "Reunión semanal - Google Meet") == "Reuniones"
    assert categorize.categoria("chrome.exe", "Bandeja de entrada - Gmail") == "Correo"


def test_categoria_sin_falsos_positivos_de_subcadena():
    # 'logitech' contiene 'git' pero NO es Desarrollo (match por token, no subcadena)
    assert categorize.categoria("logitech.exe") == "Otros"
    # el titulo 'Correos' (empresa postal) contiene 'correo' pero no es Correo
    assert categorize.categoria("chrome.exe", "Oficina Virtual - Correos") == "Navegador"
    # pero las variantes versionadas siguen funcionando (startswith)
    assert categorize.categoria("pycharm64.exe") == "Desarrollo"
    assert categorize.categoria("sublime_text.exe") == "Desarrollo"


def test_nombre_amigable():
    assert categorize.nombre_amigable("msedge.exe") == "Edge"
    assert categorize.nombre_amigable("WINWORD.EXE") == "Word"
    assert categorize.nombre_amigable("rarito.exe") == "Rarito"


# ------------------------------------------------------------------- stats
def _m(ts, app, activo=True, seg=15, titulo=""):
    return Muestra(ts=ts, app=app, titulo=titulo, activo=activo, segundos=seg)


def test_resumir_agrega_y_ignora_inactivo():
    base = datetime(2026, 7, 13, 9, 0, 0).timestamp()   # lunes 09:00
    ms = [_m(base, "chrome.exe", seg=3600),
          _m(base + 3600, "winword.exe", seg=1800),
          _m(base + 5400, "chrome.exe", activo=False, seg=1800)]  # ausente: no cuenta
    r = stats.resumir(ms)
    assert r.segundos_activos == 5400
    assert r.por_categoria["Navegador"] == 3600
    assert r.por_categoria["Documentos"] == 1800
    assert r.top_apps(1)[0] == ("Chrome", 3600)
    assert r.hora_de_oro() == 9


def test_racha_dias():
    r = stats.Resumen()
    r.por_dia = {"2026-07-10": 3600, "2026-07-11": 3600, "2026-07-13": 3600}  # hueco el 12
    # la racha se cuenta hacia atras desde el ultimo dia con datos (13) -> solo el 13
    assert r.racha_dias(minutos_min=30) == 1
    r.por_dia = {"2026-07-11": 3600, "2026-07-12": 3600, "2026-07-13": 3600}
    assert r.racha_dias(minutos_min=30) == 3
    r.por_dia = {"2026-07-13": 600}          # 10 min < 30 min
    assert r.racha_dias(minutos_min=30) == 0


def test_fmt_hm():
    assert stats.fmt_hm(0) == "0m"
    assert stats.fmt_hm(1800) == "30m"
    assert stats.fmt_hm(3660) == "1h 01m"


def test_titulares():
    base = datetime(2026, 7, 13, 16, 0, 0).timestamp()
    r = stats.resumir([_m(base, "code.exe", seg=7200), _m(base + 7200, "teams.exe", seg=1800)])
    t = stats.titulares(r)
    assert any("horas de foco" in x for x in t)
    assert any("VS Code" in x for x in t)


# ------------------------------------------------------------------- store
def test_store_semana_y_hoy(tmp_path):
    s = Store(str(tmp_path / "a.db"))
    try:
        hoy = datetime.now()
        s.add("chrome.exe", "x", True, 900, ts=hoy.timestamp())
        s.add("code.exe", "y", True, 900, ts=hoy.timestamp())
        s.add("idle.exe", "z", False, 900, ts=hoy.timestamp())   # inactivo
        assert s.segundos_hoy_activos() == 1800
        ms, lunes, domingo = s.muestras_semana(date.today())
        assert len(ms) == 3 and (domingo - lunes).days == 6
        assert s.hay_datos()
        s.borrar_todo()
        assert not s.hay_datos()
    finally:
        s.close()


def test_store_borrar_titulos(tmp_path):
    s = Store(str(tmp_path / "b.db"))
    try:
        s.add("chrome.exe", "documento secreto", True, 900)
        s.borrar_titulos()
        ms = s.muestras_dia(date.today())
        assert ms and all(m.titulo == "" for m in ms)
    finally:
        s.close()


# ------------------------------------------------------------------- cards
def test_generar_tarjetas(tmp_path):
    from PIL import Image
    base = datetime(2026, 7, 13, 10, 0, 0).timestamp()
    # incluye una app de nombre larguisimo (debe recortarse, no salirse del canvas)
    r = stats.resumir([_m(base, "chrome.exe", seg=5400), _m(base + 5400, "winword.exe", seg=3600),
                       _m(base + 9000, "un_proceso_con_un_nombre_absurdamente_largo.exe", seg=1800)])
    rutas = cards.generar_todas(r, "13/07 – 19/07/2026", str(tmp_path / "w"))
    assert len(rutas) == 4
    for p in rutas:
        img = Image.open(p)
        assert img.size == (1080, 1920)


def test_ajustar_texto():
    from PIL import Image, ImageDraw
    d = ImageDraw.Draw(Image.new("RGB", (10, 10)))
    f = cards._font(52, True)
    corto = cards._ajustar(d, "Chrome", f, 800)
    assert corto == "Chrome"
    largo = cards._ajustar(d, "X" * 200, f, 400)
    assert largo.endswith("…") and d.textlength(largo, font=f) <= 400


# ------------------------------------------------------------------- report
def test_informe_pdf(tmp_path):
    import fitz
    base = datetime(2026, 7, 13, 11, 0, 0).timestamp()
    r = stats.resumir([_m(base, "code.exe", seg=7200), _m(base + 7200, "outlook.exe", seg=1800)])
    out = str(tmp_path / "sem.pdf")
    report.exportar_pdf(out, r, lunes=date(2026, 7, 13), domingo=date(2026, 7, 19))
    doc = fitz.open(out)
    text = "\n".join(doc[p].get_text("text") for p in range(doc.page_count))
    doc.close()
    assert "Tu semana de trabajo" in text
    assert "Desarrollo" in text and "Correo" in text
    assert "13/07/2026" in text
