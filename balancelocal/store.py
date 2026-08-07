"""Almacen de muestras de actividad (SQLite). Vive solo en la carpeta de datos
del usuario; el boton de panico lo borra entero."""

from __future__ import annotations

import logging
import os
import sqlite3
import time
from datetime import date, datetime, timedelta
from pathlib import Path

from .stats import Muestra

logger = logging.getLogger(__name__)


class Store:
    def __init__(self, db_path: str):
        self.db_path = str(db_path)
        self.recuperada = False   # True si la BD estaba corrupta y se recreo
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        try:
            self._con = self._abrir()
        except sqlite3.DatabaseError as exc:
            # BD corrupta (corte de luz, disco lleno, antivirus): sin esto la
            # app moria al arrancar y no volvia a abrir hasta borrar a mano
            # actividad.db. Se aparta conservando la evidencia y se recrea.
            logger.warning("actividad.db corrupta (%s): se aparta y se crea una nueva", exc)
            stamp = date.today().strftime("%Y%m%d")
            os.replace(self.db_path, self.db_path + f".corrupta-{stamp}")
            for suf in ("-wal", "-shm"):
                # los sidecar del WAL pertenecen a la BD corrupta: fuera
                try:
                    Path(self.db_path + suf).unlink(missing_ok=True)
                except OSError:
                    pass
            self._con = self._abrir()
            self.recuperada = True

    def _abrir(self) -> sqlite3.Connection:
        # connect() abre en diferido: la corrupcion salta en el primer PRAGMA,
        # por eso todo el arranque va junto y con cierre en caso de error
        con = sqlite3.connect(self.db_path, check_same_thread=False)
        try:
            con.execute("PRAGMA journal_mode=WAL")
            con.execute("""
                CREATE TABLE IF NOT EXISTS muestras(
                    ts REAL NOT NULL, app TEXT NOT NULL, titulo TEXT NOT NULL DEFAULT '',
                    activo INTEGER NOT NULL, segundos INTEGER NOT NULL)""")
            con.execute("CREATE INDEX IF NOT EXISTS ix_ts ON muestras(ts)")
            con.commit()
        except sqlite3.DatabaseError:
            con.close()
            raise
        return con

    def close(self) -> None:
        try:
            self._con.close()
        except sqlite3.Error:
            pass

    def add(self, app: str, titulo: str, activo: bool, segundos: int,
            ts: float | None = None) -> None:
        self._con.execute(
            "INSERT INTO muestras(ts, app, titulo, activo, segundos) VALUES(?,?,?,?,?)",
            (ts if ts is not None else time.time(), app, titulo, 1 if activo else 0, segundos))
        self._con.commit()

    def _rango(self, ini: float, fin: float) -> list[Muestra]:
        filas = self._con.execute(
            "SELECT ts, app, titulo, activo, segundos FROM muestras "
            "WHERE ts>=? AND ts<? ORDER BY ts", (ini, fin))
        return [Muestra(ts=t, app=a, titulo=ti, activo=bool(ac), segundos=int(s))
                for t, a, ti, ac, s in filas]

    @staticmethod
    def _medianoche(d: date) -> float:
        return datetime(d.year, d.month, d.day).timestamp()

    def muestras_dia(self, dia: date) -> list[Muestra]:
        # limite = medianoche LOCAL del dia siguiente (no ini+86400: en los dias
        # de cambio de hora un dia dura 23 o 25 h)
        return self._rango(self._medianoche(dia), self._medianoche(dia + timedelta(days=1)))

    def muestras_semana(self, cualquier_dia: date) -> tuple[list[Muestra], date, date]:
        """Muestras de la semana (lunes a domingo) que contiene `cualquier_dia`."""
        lunes = cualquier_dia - timedelta(days=cualquier_dia.weekday())
        return (self._rango(self._medianoche(lunes), self._medianoche(lunes + timedelta(days=7))),
                lunes, lunes + timedelta(days=6))

    def segundos_hoy_activos(self) -> int:
        return sum(m.segundos for m in self.muestras_dia(date.today()) if m.activo)

    def hay_datos(self) -> bool:
        return self._con.execute("SELECT 1 FROM muestras LIMIT 1").fetchone() is not None

    def borrar_todo(self) -> None:
        self._con.execute("DELETE FROM muestras")
        self._con.commit()
        self._con.execute("VACUUM")

    def borrar_titulos(self) -> None:
        self._con.execute("UPDATE muestras SET titulo=''")
        self._con.commit()
