"""Lanzador de BalanceLocal."""

from __future__ import annotations


def _set_dpi_awareness() -> None:
    try:
        import ctypes
        try:
            ctypes.windll.user32.SetProcessDpiAwarenessContext(-4)  # PER_MONITOR_AWARE_V2
        except Exception:  # noqa: BLE001
            try:
                ctypes.windll.shcore.SetProcessDpiAwareness(2)
            except Exception:  # noqa: BLE001
                ctypes.windll.user32.SetProcessDPIAware()
    except Exception:  # noqa: BLE001
        pass


def _single_instance(nombre: str = "Local\\BalanceLocal") -> bool:
    """Guard de instancia unica. Dos BalanceLocal a la vez muestrean la misma
    ventana y escriben en la misma BD (WAL lo permite sin error): todas las
    horas del Wrapped y del PDF de facturacion saldrian duplicadas en silencio.
    El SO libera el mutex al morir el proceso: no quedan locks huerfanos."""
    try:
        import ctypes
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        # el handle se deja abierto a proposito: vive lo que el proceso
        kernel32.CreateMutexW(None, False, nombre)
        return ctypes.get_last_error() != 183  # ERROR_ALREADY_EXISTS
    except Exception:  # noqa: BLE001
        return True    # ante la duda, no impedir el arranque


def main() -> None:
    if not _single_instance():
        try:
            import ctypes
            ctypes.windll.user32.MessageBoxW(
                None, "BalanceLocal ya está abierto. Usa la ventana existente "
                "(dos instancias a la vez duplicarían tus horas registradas).",
                "BalanceLocal", 0x40)  # MB_ICONINFORMATION
        except Exception:  # noqa: BLE001
            pass
        return
    _set_dpi_awareness()
    from balancelocal.app import main as run
    run()


if __name__ == "__main__":
    main()
