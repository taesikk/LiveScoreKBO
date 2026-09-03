import sqlite3
from datetime import datetime
from pathlib import Path

DEFAULT_DB_PATH = Path("data/sent_articles.db")


class SentArticleStore:
    """한 번 보낸 기사 링크를 기억해서, 이후 브리핑에서 같은 기사가 다시 뽑히지 않게 한다.

    sort=sim(관련도순)으로 API를 호출하다 보니, IT처럼 하루 발행량이 적은 카테고리는
    새 기사가 별로 없으면 어제 순위 높았던 기사가 오늘도 그대로 뽑히는 문제가 있었다.
    API 정렬 방식과 무관하게 중복을 원천 차단하려고 링크 단위로 dedup한다.
    """

    def __init__(self, db_path: Path | str = DEFAULT_DB_PATH):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self.db_path)
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS sent_articles (
                link TEXT PRIMARY KEY,
                sent_at TEXT NOT NULL
            )
            """
        )
        self._conn.commit()

    def already_sent(self) -> set[str]:
        rows = self._conn.execute("SELECT link FROM sent_articles").fetchall()
        return {row[0] for row in rows}

    def mark_sent(self, links: list[str]) -> None:
        now = datetime.now().isoformat()
        self._conn.executemany(
            "INSERT OR IGNORE INTO sent_articles (link, sent_at) VALUES (?, ?)",
            [(link, now) for link in links],
        )
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()
