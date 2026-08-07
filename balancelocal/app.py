"""Ventana principal de BalanceLocal: registrar actividad, ver el Wrapped de la
semana (tarjetas + video), informe PDF y boton de panico."""

from __future__ import annotations

import logging
import os
import threading
from datetime import date, datetime
from pathlib import Path

import tkinter as tk
from tkinter import ttk, messagebox, filedialog

from . import APP_NAME, APP_VERSION, theme
from . import cards, report, stats
from .config import AppConfig, DB_PATH, load_config, save_config
from .store import Store
from .tracker import Tracker

logger = logging.getLogger(__name__)


class App(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title(f"{APP_NAME} {APP_VERSION}")
        self.geometry("760x620")
        self.minsize(720, 560)
        theme.apply(self)
        try:
            ico = Path(__file__).resolve().parent.parent / "build" / "icon.ico"
            if ico.is_file():
                self.iconbitmap(str(ico))
        except tk.TclError:
            pass

        self.cfg: AppConfig = load_config()
        self.store = Store(str(DB_PATH))
        self.tracker = Tracker(self._on_muestra, inactividad_seg=self.cfg.inactividad_seg,
                               guardar_titulos=self.cfg.guardar_titulos)
        self._closing = False
        self._tit_ia = None    # (rango, titulares) del ultimo Wrapped con IA
        self._lock = threading.Lock()

        self._build_ui()
        if self.store.recuperada:
            self._set_status("La base de datos estaba dañada: se apartó una copia "
                             "(actividad.db.corrupta-*) y se empezó una nueva.")
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.after(300, self._first_run)
        self.after(600, self._tick)
        if self.cfg.registrar:
            self.tracker.start()

    # ------------------------------------------------------------------ UI
    def _build_ui(self) -> None:
        theme.header(self, APP_NAME, "Tu 'Wrapped' laboral · solo en tu PC, solo para ti")
        self.status = theme.status_bar(self, "Deja la app registrando y mira tu Wrapped cada viernes.")

        top = ttk.Frame(self, padding=(16, 12))
        top.pack(fill="x")
        self.var_reg = tk.BooleanVar(value=self.cfg.registrar)
        self.btn_reg = ttk.Checkbutton(top, text="Registrar mi actividad", variable=self.var_reg,
                                       command=self._toggle_reg)
        self.btn_reg.pack(side="left")
        self.lbl_estado = ttk.Label(top, text="", style="Big.TLabel")
        self.lbl_estado.pack(side="left", padx=(16, 0))
        ttk.Button(top, text="Configurar IA…", command=self._ai_dialog).pack(side="right")

        priv = ttk.LabelFrame(self, text="Privacidad", padding=10)
        priv.pack(fill="x", padx=16, pady=(2, 0))
        ttk.Label(priv, style="CardMuted.TLabel", justify="left", text=(
            "• BalanceLocal solo mira QUÉ programa tienes delante (nombre y título de la "
            "ventana) y si hay teclado/ratón. NO registra lo que tecleas ni hace capturas.\n"
            "• Todo se guarda en tu equipo; el único que lo ve eres tú. Botón de borrado total "
            "abajo.")).pack(anchor="w")

        mid = ttk.Frame(self, padding=(16, 12))
        mid.pack(fill="both", expand=True)
        ttk.Label(mid, text="Tu Wrapped de la semana", style="H.TLabel").pack(anchor="w")
        ttk.Label(mid, text="Genera tus tarjetas para compartir (y, si tienes FFmpeg, un mini-vídeo).",
                  style="Muted.TLabel").pack(anchor="w", pady=(0, 8))
        row = ttk.Frame(mid)
        row.pack(fill="x")
        self.btn_wrap = ttk.Button(row, text="✨  Generar mi Wrapped", style="Primary.TButton",
                                   command=self._wrapped)
        self.btn_wrap.pack(side="left")
        self.var_video = tk.BooleanVar(value=False)
        ttk.Checkbutton(row, text="+ mini-vídeo (necesita FFmpeg)",
                        variable=self.var_video).pack(side="left", padx=(10, 0))
        ttk.Button(row, text="📄 Informe PDF de la semana", command=self._pdf).pack(side="right")

        self.txt_prev = tk.Text(mid, height=8, wrap="word", font=(theme.FONT, 10),
                                bg=theme.CARD, relief="flat", state="disabled")
        self.txt_prev.pack(fill="both", expand=True, pady=(10, 0))

        bar = ttk.Frame(self, padding=(16, 10))
        bar.pack(fill="x", side="bottom")
        ttk.Button(bar, text="Abrir carpeta", command=self._abrir_carpeta).pack(side="left")
        ttk.Button(bar, text="Ajustes", command=self._ajustes).pack(side="left", padx=6)
        ttk.Button(bar, text="🧨 Borrar todos mis datos", command=self._panico,
                   style="Rec.TButton").pack(side="right")

    # ------------------------------------------------------------ registro
    def _on_muestra(self, app: str, titulo: str, activo: bool, seg: int) -> None:
        # llamado desde el hilo del tracker; SQLite con check_same_thread=False +
        # lock propio para no intercalar escrituras con las lecturas de la UI
        if self._closing:
            return
        try:
            with self._lock:
                self.store.add(app, titulo, activo, seg)
        except Exception as exc:  # noqa: BLE001
            logger.debug("guardar muestra fallo: %s", exc)

    def _toggle_reg(self) -> None:
        self.cfg.registrar = bool(self.var_reg.get())
        save_config(self.cfg)
        if self.cfg.registrar:
            self.tracker.start()
        else:
            self.tracker.stop()

    def _tick(self) -> None:
        if self._closing:
            return
        try:
            with self._lock:
                seg = self.store.segundos_hoy_activos()
            estado = "● registrando" if self.tracker.running else "○ en pausa"
            color = theme.SUCCESS if self.tracker.running else theme.MUTED
            self.lbl_estado.config(text=f"{estado} · hoy {stats.fmt_hm(seg)} de foco",
                                   foreground=color)
        except tk.TclError:
            return
        self.after(3000, self._tick)

    # -------------------------------------------------------------- wrapped
    def _resumen_semana(self):
        with self._lock:
            muestras, lunes, domingo = self.store.muestras_semana(date.today())
        return stats.resumir(muestras), lunes, domingo

    def _wrapped(self) -> None:
        resumen, lunes, domingo = self._resumen_semana()
        if resumen.segundos_activos < 60:
            messagebox.showinfo(APP_NAME, "Aún no hay suficiente actividad esta semana. "
                                "Deja la app registrando un rato y vuelve luego.")
            return
        self.btn_wrap.config(state="disabled")
        self._set_status("Generando tus tarjetas…")
        rango = f"{lunes.strftime('%d/%m')} – {domingo.strftime('%d/%m/%Y')}"
        stamp = datetime.now().strftime("%Y-%m-%d")
        out_dir = Path(self.cfg.output_dir) / f"Wrapped_{stamp}"
        hacer_video = bool(self.var_video.get())

        def runner():
            error = None
            video_msg = None
            rutas = []
            video = None
            # titulares con IA (si esta configurada) en el HILO del worker: una
            # llamada con timeout y fallback a los heuristicos. Se cachean por
            # rango para que el Informe PDF de la misma semana los reutilice.
            tit = stats.titulares_finales(resumen)
            self._tit_ia = (rango, tit)
            try:
                rutas = cards.generar_todas(resumen, rango, str(out_dir))
                if hacer_video:
                    from . import video as vid
                    ff = vid.find_ffmpeg() or ""
                    if not ff:
                        video_msg = "sin_ffmpeg"
                    else:
                        try:
                            video = vid.montar(ff, rutas, str(out_dir / "wrapped.mp4"))
                        except Exception as exc:  # noqa: BLE001
                            logger.warning("video fallo: %s", exc)
                            video_msg = "fallo"
            except Exception as exc:  # noqa: BLE001
                logger.exception("wrapped fallo")
                error = str(exc)
            if not self._closing:
                try:
                    self.after(0, self._wrapped_done, resumen, str(out_dir), rutas, video,
                               error, video_msg, tit)
                except (RuntimeError, tk.TclError):
                    pass
        threading.Thread(target=runner, daemon=True).start()

    def _wrapped_done(self, resumen, out_dir, rutas, video, error, video_msg,
                      tit=None) -> None:
        try:
            self.btn_wrap.config(state="normal")
        except tk.TclError:
            return
        if not rutas:
            messagebox.showerror(APP_NAME, f"No se pudo generar el Wrapped:\n{error or 'error desconocido'}")
            return
        # vista previa de titulares
        self.txt_prev.config(state="normal")
        self.txt_prev.delete("1.0", "end")
        self.txt_prev.insert("1.0", "Tu semana:\n\n" + "\n".join(
            "• " + t for t in (tit or stats.titulares(resumen))))
        self.txt_prev.config(state="disabled")
        extra = ""
        if video_msg == "sin_ffmpeg":
            extra = "\n\n(El mini-vídeo necesita FFmpeg: winget install Gyan.FFmpeg)"
        elif video_msg == "fallo":
            extra = "\n\n(El mini-vídeo no se pudo generar; las tarjetas sí están listas.)"
        elif video:
            extra = "\n\n🎬 Vídeo: wrapped.mp4"
        self._set_status(f"Wrapped generado en {out_dir}")
        if messagebox.askyesno(APP_NAME, f"Tus tarjetas están en:\n{out_dir}{extra}\n\n¿Abrir la carpeta?"):
            try:
                os.startfile(out_dir)
            except OSError:
                pass

    def _pdf(self) -> None:
        resumen, lunes, domingo = self._resumen_semana()
        if resumen.segundos_activos < 60:
            messagebox.showinfo(APP_NAME, "Aún no hay suficiente actividad esta semana.")
            return
        out = Path(self.cfg.output_dir) / f"Semana_{lunes.strftime('%Y-%m-%d')}.pdf"
        # si el ultimo Wrapped (misma semana) redacto titulares con IA, el PDF
        # los reutiliza; el PDF no llama a la IA (es sincrono en el hilo de UI)
        rango = f"{lunes.strftime('%d/%m')} – {domingo.strftime('%d/%m/%Y')}"
        tit_pre = None
        if self._tit_ia and self._tit_ia[0] == rango:
            tit_pre = self._tit_ia[1]
        try:
            report.exportar_pdf(str(out), resumen, lunes=lunes, domingo=domingo,
                                titulares_pre=tit_pre)
        except Exception as exc:  # noqa: BLE001
            logger.exception("pdf fallo")
            messagebox.showerror(APP_NAME, f"No se pudo generar el informe:\n{exc}")
            return
        if messagebox.askyesno(APP_NAME, f"Informe guardado en:\n{out}\n\n¿Abrirlo?"):
            try:
                os.startfile(str(out))
            except OSError:
                pass

    # -------------------------------------------------------------- varios
    def _abrir_carpeta(self) -> None:
        try:
            Path(self.cfg.output_dir).mkdir(parents=True, exist_ok=True)
            os.startfile(self.cfg.output_dir)
        except OSError:
            pass

    def _ajustes(self) -> None:
        win = tk.Toplevel(self)
        theme.center_window(win)
        win.title("Ajustes")
        win.configure(bg=theme.BG)
        win.transient(self)
        win.resizable(False, False)
        frm = ttk.Frame(win, padding=16)
        frm.pack(fill="both", expand=True)
        v_tit = tk.BooleanVar(value=self.cfg.guardar_titulos)
        ttk.Checkbutton(frm, text="Guardar el título de las ventanas (más detalle en las "
                        "estadísticas, pero más sensible)", variable=v_tit).pack(anchor="w")
        r = ttk.Frame(frm); r.pack(fill="x", pady=(10, 0))
        ttk.Label(r, text="Minutos sin teclado/ratón para contarte 'ausente':").pack(side="left")
        v_idle = tk.IntVar(value=max(1, self.cfg.inactividad_seg // 60))
        ttk.Spinbox(r, from_=1, to=30, textvariable=v_idle, width=4).pack(side="left", padx=6)
        od = ttk.Frame(frm); od.pack(fill="x", pady=(10, 0))
        outdir = {"v": self.cfg.output_dir}
        lbl = ttk.Label(od, text=f"Carpeta de salida: {outdir['v']}", style="Muted.TLabel",
                        wraplength=420)
        lbl.pack(side="left")

        def cambiar_dir():
            d = filedialog.askdirectory(initialdir=outdir["v"], parent=win)
            if d:
                outdir["v"] = d
                lbl.config(text=f"Carpeta de salida: {d}")

        def guardar():
            self.cfg.guardar_titulos = bool(v_tit.get())
            try:
                mins = int(v_idle.get())      # el Spinbox editable puede tener texto/vacio
            except (tk.TclError, ValueError):
                mins = self.cfg.inactividad_seg // 60
            self.cfg.inactividad_seg = max(60, min(30, mins) * 60)
            self.cfg.output_dir = outdir["v"]
            save_config(self.cfg)
            # aplicar en vivo al tracker
            self.tracker.guardar_titulos = self.cfg.guardar_titulos
            self.tracker.inactividad_seg = self.cfg.inactividad_seg
            win.destroy()
        ttk.Button(od, text="Cambiar…", command=cambiar_dir).pack(side="right")
        ttk.Button(frm, text="Guardar", style="Primary.TButton",
                   command=guardar).pack(anchor="e", pady=(14, 0))
        win.grab_set()

    def _ai_dialog(self) -> None:
        from octonove_core.ai_dialog import show_ai_dialog
        show_ai_dialog(self, on_saved=lambda: self._set_status(
            "IA configurada: los titulares del proximo Wrapped se redactaran con ella."))

    def _panico(self) -> None:
        if not messagebox.askyesno(APP_NAME, "Esto BORRA todos tus datos de actividad de "
                                   "forma permanente. ¿Seguro?"):
            return
        self.tracker.stop()
        with self._lock:
            self.store.borrar_todo()
        self.var_reg.set(False)
        self.cfg.registrar = False
        save_config(self.cfg)
        self.txt_prev.config(state="normal")
        self.txt_prev.delete("1.0", "end")
        self.txt_prev.config(state="disabled")
        self._set_status("Todos tus datos han sido borrados.")

    def _set_status(self, text: str) -> None:
        try:
            self.status.config(text=text)
        except tk.TclError:
            pass

    def _first_run(self) -> None:
        if self._closing or self.cfg.seen_welcome:
            return
        self.cfg.seen_welcome = True
        save_config(self.cfg)
        messagebox.showinfo(
            APP_NAME, "Bienvenido a BalanceLocal.\n\n"
            "Deja la app abierta y registrando: apunta qué programa usas y si estás activo, "
            "sin registrar lo que tecleas ni hacer capturas.\n\n"
            "Cada viernes pulsa 'Generar mi Wrapped' para ver tus tarjetas (horas de foco, apps "
            "top, tu hora de oro, tu racha) y compartirlas. El informe PDF te da las horas por "
            "categoría para facturar.\n\n"
            "Todo se queda en tu PC. Puedes pausar o borrarlo todo cuando quieras.")

    def _on_close(self) -> None:
        self._closing = True
        try:
            self.tracker.stop()      # une el hilo del tracker antes de cerrar la BD
        except Exception:  # noqa: BLE001
            pass
        try:
            with self._lock:         # bajo lock: por si una muestra sigue en vuelo
                self.store.close()
        except Exception:  # noqa: BLE001
            pass
        self.destroy()


def main() -> None:
    from .config import setup_logging
    setup_logging()
    App().mainloop()
