import sqlite3
from pathlib import Path

from kbo_alert.crawler.relay import RelayEvent

DEFAULT_DB_PATH = Path("data/processed_events.db")


class EventStore:
    def __init__(self, db_path: Path | str = DEFAULT_DB_PATH):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self.db_path)
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS processed_events (
                game_id TEXT NOT NULL,
                seqno INTEGER NOT NULL,
                PRIMARY KEY (game_id, seqno)
            )
            """
        )
        self._conn.commit()

    def filter_new(self, events: list[RelayEvent]) -> list[RelayEvent]:
        """Return only events not seen before, marking them as seen."""
        new_events = []
        for event in events:
            try:
                self._conn.execute(
                    "INSERT INTO processed_events (game_id, seqno) VALUES (?, ?)",
                    (event.game_id, event.seqno),
                )
                new_events.append(event)
            except sqlite3.IntegrityError:
                continue
        self._conn.commit()
        return new_events

    def close(self) -> None:
        self._conn.close()
