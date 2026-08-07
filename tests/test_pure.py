"""Tests de logica pura de BalanceLocal (categorizacion, estadisticas, store,
tarjetas, informe). Ejecutar:  python -m pytest tests/ -q"""

import os
import subprocess
import sys
from datetime import date, datetime
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from balancelocal import cards, categorize, report, stats, video  # noqa: E402
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


def test_store_bd_corrupta_se_recupera(tmp_path):
    # una actividad.db con basura NO debe matar el arranque para siempre:
    # se aparta como evidencia y se recrea vacia
    db = tmp_path / "c.db"
    basura = b"esto no es una base de datos sqlite " * 4
    db.write_bytes(basura)
    s = Store(str(db))
    try:
        assert s.recuperada
        s.add("chrome.exe", "x", True, 900)
        assert s.segundos_hoy_activos() == 900
        respaldos = list(tmp_path.glob("c.db.corrupta-*"))
        assert len(respaldos) == 1 and respaldos[0].read_bytes() == basura
    finally:
        s.close()
    # una BD sana no debe marcar recuperada
    s2 = Store(str(tmp_path / "sana.db"))
    try:
        assert not s2.recuperada
    finally:
        s2.close()


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


# ------------------------------------------------------------------- video
def test_concat_cmd_sin_flags_contradictorios():
    cmd = video.concat_cmd("ffmpeg", "lista.txt", "out.mp4")
    # '-r 30' junto a '-fps_mode vfr' (o '-vsync vfr') hace que FFmpeg >=5.1
    # aborte al arrancar ("This is contradictory"): el video no salia NUNCA
    assert "-fps_mode" not in cmd and "-vsync" not in cmd
    assert cmd[cmd.index("-r") + 1] == "30"
    assert cmd[-1] == "out.mp4"


@pytest.mark.skipif(not video.find_ffmpeg(), reason="FFmpeg no instalado")
def test_montar_video_smoke(tmp_path):
    # smoke contra el FFmpeg real del sistema: es lo unico que detecta flags
    # que una version nueva rechaza (la causa del bug del mini-video)
    from PIL import Image
    tarjetas = []
    for i in range(2):
        p = tmp_path / f"t{i}.png"
        Image.new("RGB", (108, 192), (40 + 80 * i, 80, 120)).save(p)
        tarjetas.append(str(p))
    out = tmp_path / "wrapped.mp4"
    video.montar(video.find_ffmpeg(), tarjetas, str(out), seg_por_tarjeta=0.5)
    assert out.is_file() and out.stat().st_size > 0


# ----------------------------------------------------------------- lanzador
def test_instancia_unica_mutex():
    import BalanceLocal as lanzador
    # nombre propio del test: no colisiona con una app real abierta
    nombre = f"Local\\BalanceLocal_test_{os.getpid()}"
    assert lanzador._single_instance(nombre)          # libre: la adquiere
    # un segundo PROCESO debe verla ocupada mientras este proceso viva
    raiz = str(Path(__file__).resolve().parent.parent)
    env = dict(os.environ)
    env["PYTHONPATH"] = raiz + os.pathsep + env.get("PYTHONPATH", "")
    r = subprocess.run(
        [sys.executable, "-c",
         "import sys, BalanceLocal; "
         f"sys.exit(0 if not BalanceLocal._single_instance({nombre!r}) else 1)"],
        env=env, timeout=30)
    assert r.returncode == 0


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


def _resumen_min():
    """Resumen sintetico con actividad suficiente para tener titulares."""
    from datetime import datetime, timedelta
    from balancelocal.stats import resumir
    from balancelocal.store import Muestra
    base = datetime(2026, 8, 3, 9, 0)
    ms = [Muestra((base + timedelta(minutes=i)).timestamp(), "chrome.exe", "Docs", 1, 60)
          for i in range(120)]
    return resumir(ms)


def test_titulares_ia_valida_y_fallback(monkeypatch):
    from octonove_core import llm
    from balancelocal import stats
    resumen = _resumen_min()
    base = stats.titulares(resumen)
    assert base
    monkeypatch.setattr(llm, "available", lambda timeout=3.0: True)

    # respuesta valida: mismo numero de lineas y mismas cifras -> se usa la IA
    valida = "\n".join(f"{i+1}. ✨ {t}" for i, t in enumerate(base))
    monkeypatch.setattr(llm, "generate", lambda *a, **k: valida)
    out = stats.titulares_finales(resumen)
    assert out != base and len(out) == len(base)

    # numero de lineas equivocado -> fallback total
    monkeypatch.setattr(llm, "generate", lambda *a, **k: "1. hola")
    assert stats.titulares_finales(resumen) == base

    # cifras alteradas en una linea -> esa linea cae a la heuristica
    alterada = [f"{i+1}. {t}" for i, t in enumerate(base)]
    alterada[0] = "1. Sumaste 999 horas de foco."
    monkeypatch.setattr(llm, "generate", lambda *a, **k: "\n".join(alterada))
    out = stats.titulares_finales(resumen)
    assert out[0] == base[0]

    # excepcion -> fallback total
    def boom(*a, **k):
        raise RuntimeError("x")
    monkeypatch.setattr(llm, "generate", boom)
    assert stats.titulares_finales(resumen) == base

    # sin proveedor -> heuristicos sin llamar a generate
    monkeypatch.setattr(llm, "available", lambda timeout=3.0: False)
    assert stats.titulares_finales(resumen) == base
