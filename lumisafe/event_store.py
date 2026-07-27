"""
Couche infrastructure : persistance des événements (motion, vandalisme)
dans SQLite, pour que l'API REST (api/) et le dashboard de François et
Guillaume puissent consulter l'historique.

Même esprit que mqtt_client.py et camera_controller.py : le domaine
(motion_handler.py, vandalism_handler.py) ne connaît pas ce module —
c'est main.py qui appelle EventStore après chaque décision.

SQLite plutôt qu'un vrai serveur de base de données : un seul writer
(le service MQTT), lectures peu fréquentes (dashboard), tourne sans
dépendance supplémentaire sur le Pi. Si le volume d'événements ou le
nombre de lampadaires grossit, migrer vers Postgres sans changer
l'interface publique de cette classe.
"""

import sqlite3
import threading
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from . import config

_SCHEMA = """
CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL,
    lamppost_id TEXT NOT NULL,
    event_type TEXT NOT NULL,       -- 'motion' | 'vandalism'
    detail TEXT,                     -- ex: "son 72.4dB", "choc 1.8g"
    light_on INTEGER,                -- 0/1, NULL si non applicable
    alert_active INTEGER,            -- 0/1, NULL si non applicable
    photo_path TEXT                  -- chemin de la capture, NULL si aucune
);
CREATE INDEX IF NOT EXISTS idx_events_created_at ON events(created_at);
CREATE INDEX IF NOT EXISTS idx_events_type ON events(event_type);
"""

# Un seul process écrit (main.py) mais SQLite + threads paho peuvent se
# chevaucher : verrou simple, largement suffisant à ce volume d'écritures.
_write_lock = threading.Lock()


@dataclass(frozen=True)
class Event:
    id: int
    created_at: str
    lamppost_id: str
    event_type: str
    detail: Optional[str]
    light_on: Optional[bool]
    alert_active: Optional[bool]
    photo_path: Optional[str]


class EventStore:
    def __init__(self, db_path: Optional[str] = None):
        self._db_path = db_path or config.DB_PATH
        Path(self._db_path).parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.executescript(_SCHEMA)

    @contextmanager
    def _connect(self):
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def record_motion(self, light_on: bool, photo_path: Optional[Path] = None) -> None:
        self._insert(
            event_type="motion",
            detail=None,
            light_on=light_on,
            alert_active=None,
            photo_path=photo_path,
        )

    def record_vandalism(
        self, alert_active: bool, detail: str, photo_path: Optional[Path] = None
    ) -> None:
        self._insert(
            event_type="vandalism",
            detail=detail,
            light_on=None,
            alert_active=alert_active,
            photo_path=photo_path,
        )

    def _insert(self, event_type, detail, light_on, alert_active, photo_path) -> None:
        with _write_lock, self._connect() as conn:
            conn.execute(
                "INSERT INTO events "
                "(created_at, lamppost_id, event_type, detail, light_on, alert_active, photo_path) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    datetime.now(timezone.utc).isoformat(),
                    config.LAMPPOST_ID,
                    event_type,
                    detail,
                    None if light_on is None else int(light_on),
                    None if alert_active is None else int(alert_active),
                    str(photo_path) if photo_path else None,
                ),
            )

    def list_events(self, event_type: Optional[str] = None, limit: int = 50) -> List[Event]:
        limit = max(1, min(limit, 500))
        query = "SELECT * FROM events"
        params: list = []
        if event_type:
            query += " WHERE event_type = ?"
            params.append(event_type)
        query += " ORDER BY id DESC LIMIT ?"
        params.append(limit)
        with self._connect() as conn:
            rows = conn.execute(query, params).fetchall()
        return [self._row_to_event(r) for r in rows]

    def get_status(self) -> dict:
        with self._connect() as conn:
            last_motion = conn.execute(
                "SELECT * FROM events WHERE event_type = 'motion' ORDER BY id DESC LIMIT 1"
            ).fetchone()
            last_vandalism = conn.execute(
                "SELECT * FROM events WHERE event_type = 'vandalism' ORDER BY id DESC LIMIT 1"
            ).fetchone()
        return {
            "lamppost_id": config.LAMPPOST_ID,
            "light_on": bool(last_motion["light_on"])
            if last_motion and last_motion["light_on"] is not None
            else False,
            "alert_active": bool(last_vandalism["alert_active"])
            if last_vandalism and last_vandalism["alert_active"] is not None
            else False,
            "last_motion_at": last_motion["created_at"] if last_motion else None,
            "last_vandalism_at": last_vandalism["created_at"] if last_vandalism else None,
        }

    @staticmethod
    def _row_to_event(row: sqlite3.Row) -> Event:
        return Event(
            id=row["id"],
            created_at=row["created_at"],
            lamppost_id=row["lamppost_id"],
            event_type=row["event_type"],
            detail=row["detail"],
            light_on=None if row["light_on"] is None else bool(row["light_on"]),
            alert_active=None if row["alert_active"] is None else bool(row["alert_active"]),
            photo_path=row["photo_path"],
        )
