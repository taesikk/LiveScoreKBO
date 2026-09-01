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
                channel TEXT NOT NULL,
                PRIMARY KEY (game_id, seqno, channel)
            )
            """
        )
        self._conn.commit()

    def filter_new(self, events: list[RelayEvent], channel: str) -> list[RelayEvent]:
        """Return only events not seen before *for this channel*, marking them as seen.

        channel까지 키에 포함하는 이유: 두 팀이 서로 맞대결하면 같은 game_id를
        여러 채널이 동시에 폴링한다. (game_id, seqno)로만 dedup하면 먼저 폴링한
        채널이 이벤트를 전부 "처리됨"으로 찍어버려서 다른 채널은 아무것도 못 받는다.
        """
        new_events = []
        for event in events:
            try:
                self._conn.execute(
                    "INSERT INTO processed_events (game_id, seqno, channel) VALUES (?, ?, ?)",
                    (event.game_id, event.seqno, channel),
                )
                new_events.append(event)
            except sqlite3.IntegrityError:
                continue
        self._conn.commit()
        return new_events

    def close(self) -> None:
        self._conn.close()
