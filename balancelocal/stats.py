"""Estadisticas de actividad: de las muestras crudas a los numeros del 'Wrapped'.
100% puro y testeable (recibe muestras, devuelve resumenes)."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta

from .categorize import categoria, nombre_amigable

logger = logging.getLogger(__name__)


@dataclass
class Muestra:
    ts: float            # time.time() de la muestra
    app: str             # ejecutable (p.ej. 'chrome.exe')
    titulo: str
    activo: bool         # habia teclado/raton reciente
    segundos: int        # cuanto representa la muestra (el intervalo de muestreo)


@dataclass
class Resumen:
    segundos_activos: int = 0
    por_categoria: dict = field(default_factory=dict)     # cat -> segundos
    por_app: dict = field(default_factory=dict)           # app amigable -> segundos
    por_hora: dict = field(default_factory=dict)          # 0..23 -> segundos
    por_dia: dict = field(default_factory=dict)           # 'YYYY-MM-DD' -> segundos

    def top_apps(self, n: int = 5) -> list[tuple[str, int]]:
        return sorted(self.por_app.items(), key=lambda kv: -kv[1])[:n]

    def top_categorias(self, n: int = 8) -> list[tuple[str, int]]:
        return sorted(self.por_categoria.items(), key=lambda kv: -kv[1])[:n]

    @property
    def horas_activas(self) -> float:
        return round(self.segundos_activos / 3600, 1)

    def hora_de_oro(self) -> int | None:
        """La hora del dia (0..23) con mas actividad, o None si no hay datos."""
        if not self.por_hora:
            return None
        return max(self.por_hora.items(), key=lambda kv: kv[1])[0]

    def racha_dias(self, minutos_min: int = 30) -> int:
        """Racha de dias CONSECUTIVOS (hasta el ultimo con datos) con al menos
        `minutos_min` de actividad."""
        if not self.por_dia:
            return 0
        dias_ok = {d for d, s in self.por_dia.items() if s >= minutos_min * 60}
        if not dias_ok:
            return 0
        ultimo = max(date.fromisoformat(d) for d in dias_ok)
        racha, cur = 0, ultimo
        while cur.isoformat() in dias_ok:
            racha += 1
            cur -= timedelta(days=1)
        return racha


def resumir(muestras: list[Muestra]) -> Resumen:
    r = Resumen()
    for m in muestras:
        if not m.activo:
            continue
        r.segundos_activos += m.segundos
        cat = categoria(m.app, m.titulo)
        r.por_categoria[cat] = r.por_categoria.get(cat, 0) + m.segundos
        app = nombre_amigable(m.app)
        r.por_app[app] = r.por_app.get(app, 0) + m.segundos
        dt = datetime.fromtimestamp(m.ts)
        r.por_hora[dt.hour] = r.por_hora.get(dt.hour, 0) + m.segundos
        d = dt.strftime("%Y-%m-%d")
        r.por_dia[d] = r.por_dia.get(d, 0) + m.segundos
    return r


def fmt_hm(segundos: int) -> str:
    """Segundos -> 'Xh YYm' o 'YYm'. Puro."""
    m = int(round(segundos / 60))
    h, mm = divmod(m, 60)
    return f"{h}h {mm:02d}m" if h else f"{mm}m"


def franja_horaria(hora: int) -> str:
    if 5 <= hora < 12:
        return f"las {hora}:00 de la mañana"
    if 12 <= hora < 14:
        return f"las {hora}:00 del mediodía"
    if 14 <= hora < 21:
        return f"las {hora}:00 de la tarde"
    return f"las {hora}:00 de la noche"


def titulares(resumen: Resumen) -> list[str]:
    """Frases resumen sin IA (la IA opcional puede reescribirlas con mas gracia)."""
    out = []
    out.append(f"Sumaste {resumen.horas_activas} horas de foco.")
    top = resumen.top_apps(1)
    if top:
        out.append(f"Tu app estrella fue {top[0][0]} ({fmt_hm(top[0][1])}).")
    tc = resumen.top_categorias(1)
    if tc:
        out.append(f"Donde mas estuviste: {tc[0][0]}.")
    h = resumen.hora_de_oro()
    if h is not None:
        out.append(f"Tu hora de oro fue a {franja_horaria(h)}.")
    racha = resumen.racha_dias()
    if racha >= 2:
        out.append(f"Encadenaste {racha} días seguidos de trabajo.")
    return out


def _cifras(texto: str) -> list[str]:
    """Grupos de digitos de una frase ('8,5', '3'...). Para validar la IA."""
    import re
    return re.findall(r"\d+(?:[.,]\d+)?", texto)


def titulares_finales(resumen: Resumen, timeout: float = 25.0) -> list[str]:
    """Titulares del Wrapped: los heuristicos, reescritos con la IA configurada
    ('Configurar IA…') si la hay. Garantias: una sola llamada, timeout acotado
    (la 1a a Ollama carga el modelo), y validacion ESTRICTA por linea — mismo
    numero de lineas, longitud acotada y las MISMAS cifras que la heuristica
    (la IA pule la redaccion, jamas los datos). Ante cualquier fallo, se
    devuelven los heuristicos: el Wrapped nunca puede fallar por la IA."""
    base = titulares(resumen)
    if not base:
        return base
    try:
        from octonove_core import llm
        if not llm.available():
            return base
        numeradas = "\n".join(f"{i+1}. {t}" for i, t in enumerate(base))
        out = llm.generate(
            "Reescribe estos titulares de un resumen semanal de trabajo para que "
            "suenen mas celebratorios y con gancho (estilo Spotify Wrapped), en "
            "espanol. Devuelve EXACTAMENTE el mismo numero de lineas, numeradas "
            "igual (1., 2., ...), conservando todas las cifras y los nombres de "
            "aplicaciones tal cual. Maximo 12 palabras por linea. Nada mas que "
            f"las lineas:\n\n{numeradas}",
            system="Eres un redactor conciso. Respondes SOLO con las lineas pedidas.",
            timeout=timeout, temperature=0.4)
        if not out:
            return base
        import re
        lineas = [re.sub(r"^\s*\d+[.)]\s*", "", ln).strip().strip('"')
                  for ln in out.strip().splitlines() if ln.strip()]
        if len(lineas) != len(base):
            return base
        finales = []
        for orig, nueva in zip(base, lineas):
            ok = (0 < len(nueva) <= 90
                  and sorted(_cifras(nueva)) == sorted(_cifras(orig)))
            finales.append(nueva if ok else orig)
        return finales
    except Exception as exc:  # noqa: BLE001  la IA nunca tumba el Wrapped
        logger.warning("titulares con IA fallaron (%s): heuristicos", exc)
        return base
