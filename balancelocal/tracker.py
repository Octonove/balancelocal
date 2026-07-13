"""Rastreador de actividad: cada intervalo mira que ventana esta en primer plano
(app + titulo) y si hay teclado/raton reciente, y guarda una muestra. Solo lee
el estado de Windows con ctypes; no engancha nada global ni registra pulsaciones.

Solo funciona con ventana en primer plano de OTRA app: BalanceLocal no se cuenta
a si mismo (su propio PID se excluye)."""

from __future__ import annotations

import ctypes
import logging
import os
import threading
import time
from ctypes import wintypes
from pathlib import Path

logger = logging.getLogger(__name__)

INTERVALO = 15          # segundos entre muestras
PROCESS_QUERY_LIMITED_INFORMATION = 0x1000

try:
    _user32 = ctypes.windll.user32
    _kernel32 = ctypes.windll.kernel32
    _user32.GetForegroundWindow.restype = wintypes.HWND
    _user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
    _user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
    _user32.GetWindowTextLengthW.argtypes = [wintypes.HWND]
    _kernel32.GetTickCount.restype = wintypes.DWORD
    WIN = True
except Exception as exc:  # noqa: BLE001
    WIN = False
    logger.warning("API de Windows no disponible: %s", exc)


class _LASTINPUTINFO(ctypes.Structure):
    _fields_ = [("cbSize", ctypes.c_uint), ("dwTime", ctypes.c_uint)]


def _ms_inactivo() -> int:
    """Milisegundos desde la ultima entrada de teclado/raton (0 si no se puede)."""
    try:
        lii = _LASTINPUTINFO()
        lii.cbSize = ctypes.sizeof(lii)
        if not _user32.GetLastInputInfo(ctypes.byref(lii)):
            return 0
        # aritmetica de 32 bits: GetTickCount y dwTime comparten el mismo dominio
        # y el enmascarado gestiona el desbordamiento (~49 dias) correctamente
        return (_kernel32.GetTickCount() - lii.dwTime) & 0xFFFFFFFF
    except Exception:  # noqa: BLE001
        return 0


def _ventana_activa() -> tuple[str, str]:
    """(ejecutable, titulo) de la ventana en primer plano. ('','') si no hay."""
    hwnd = _user32.GetForegroundWindow()
    if not hwnd:
        return "", ""
    pid = wintypes.DWORD()
    _user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    if not pid.value or pid.value == os.getpid():
        return "", ""       # la propia BalanceLocal no cuenta
    # titulo
    n = _user32.GetWindowTextLengthW(hwnd)
    buf = ctypes.create_unicode_buffer(n + 1)
    _user32.GetWindowTextW(hwnd, buf, n + 1)
    titulo = buf.value
    # ejecutable
    app = ""
    h = _kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid.value)
    if h:
        try:
            size = wintypes.DWORD(4096)
            b = ctypes.create_unicode_buffer(4096)
            if _kernel32.QueryFullProcessImageNameW(h, 0, b, ctypes.byref(size)):
                app = Path(b.value).name
        finally:
            _kernel32.CloseHandle(h)
    return app, titulo


class Tracker:
    """Hilo que muestrea la ventana activa y guarda muestras via callback."""

    def __init__(self, on_muestra, *, inactividad_seg: int = 120,
                 guardar_titulos: bool = True, intervalo: int = INTERVALO):
        self.on_muestra = on_muestra          # (app, titulo, activo, segundos)
        self.inactividad_seg = inactividad_seg
        self.guardar_titulos = guardar_titulos
        self.intervalo = max(5, int(intervalo))
        self._stop: threading.Event | None = None
        self._thread: threading.Thread | None = None

    @property
    def running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def start(self) -> None:
        if self.running or not WIN:
            return
        ev = threading.Event()
        self._stop = ev
        self._thread = threading.Thread(target=self._run, args=(ev,), daemon=True)
        self._thread.start()

    def stop(self) -> None:
        if self._stop is not None:
            self._stop.set()
        if self._thread:
            self._thread.join(timeout=2)
        self._thread = None

    def _run(self, stop: threading.Event) -> None:
        while not stop.is_set():
            t0 = time.time()
            try:
                app, titulo = _ventana_activa()
                activo = _ms_inactivo() < self.inactividad_seg * 1000
                if app:
                    self.on_muestra(app, titulo if self.guardar_titulos else "",
                                    activo, self.intervalo)
            except Exception as exc:  # noqa: BLE001
                logger.debug("muestra fallo: %s", exc)
            stop.wait(max(0.5, self.intervalo - (time.time() - t0)))
