"""Mini-video vertical (30 s) montando las tarjetas Wrapped con FFmpeg. Opcional:
solo si FFmpeg esta instalado en el sistema. No se empaqueta FFmpeg."""

from __future__ import annotations

import logging
import subprocess
from pathlib import Path

from octonove_core.ffmpeg import find_ffmpeg as _find_ffmpeg
from octonove_core.procutil import subprocess_kwargs

logger = logging.getLogger(__name__)


def find_ffmpeg(override: str = "") -> str | None:
    return _find_ffmpeg(override, package_file=__file__)


class VideoError(Exception):
    pass


def concat_cmd(ffmpeg: str, list_file: str, out_mp4: str, seg_por_tarjeta: float = 7.0) -> list:
    """Comando FFmpeg: cada tarjeta se muestra `seg_por_tarjeta` s. Puro."""
    return [ffmpeg, "-y", "-hide_banner", "-loglevel", "error",
            "-f", "concat", "-safe", "0", "-i", list_file,
            "-vf", "scale=1080:1920:force_original_aspect_ratio=decrease,"
                   "pad=1080:1920:(ow-iw)/2:(oh-ih)/2,format=yuv420p",
            "-r", "30", "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
            "-fps_mode", "vfr", out_mp4]


def montar(ffmpeg: str, tarjetas: list[str], out_mp4: str,
           seg_por_tarjeta: float = 7.0) -> str:
    if not ffmpeg:
        raise VideoError("No se encontro FFmpeg (instalalo con: winget install Gyan.FFmpeg).")
    if not tarjetas:
        raise VideoError("No hay tarjetas que montar.")
    wd = Path(out_mp4).parent
    wd.mkdir(parents=True, exist_ok=True)
    lst = wd / ".bl_lista.txt"

    def _q(p: str) -> str:
        # el demuxer concat exige escapar ' como '\'' (rutas tipo C:/Users/O'Brien)
        return Path(p).resolve().as_posix().replace("'", "'\\''")

    lineas = []
    for t in tarjetas:
        lineas.append(f"file '{_q(t)}'\nduration {seg_por_tarjeta:.2f}\n")
    lineas.append(f"file '{_q(tarjetas[-1])}'\n")
    lst.write_text("".join(lineas), encoding="utf-8")
    try:
        r = subprocess.run(concat_cmd(ffmpeg, str(lst), str(Path(out_mp4).resolve())),
                           capture_output=True, timeout=180, **subprocess_kwargs())
    except (OSError, subprocess.SubprocessError) as exc:
        raise VideoError(f"No se pudo ejecutar FFmpeg: {exc}") from exc
    finally:
        try:
            lst.unlink(missing_ok=True)
        except OSError:
            pass
    if r.returncode != 0 or not Path(out_mp4).is_file():
        try:
            Path(out_mp4).unlink(missing_ok=True)
        except OSError:
            pass
        raise VideoError("FFmpeg no pudo montar el video: "
                         + r.stderr.decode("utf-8", "replace")[-200:])
    return out_mp4
