from dataclasses import dataclass
from datetime import datetime

import requests

from kbo_alert.timezone import KST

API_URL = "https://api-gw.sports.naver.com/schedule/games/{game_id}/relay"
REFERER = "https://m.sports.naver.com/game/{game_id}/relay"
USER_AGENT = "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15"

TOP_BOTTOM = {"0": "초", "1": "말"}


@dataclass(frozen=True)
class RelayEvent:
    game_id: str
    no: int
    seqno: int
    inning: int
    top_bottom: str  # "초" or "말"
    text: str
    event_type: int
    home_score: int
    away_score: int
    base1: str  # "0" if empty, otherwise occupying runner's batting order
    base2: str
    base3: str
    outs: int
    collected_at: datetime  # 실제 발생 시각이 아니라 우리가 처음 수집한 시각

    @property
    def bases_loaded(self) -> bool:
        return self.base1 != "0" and self.base2 != "0" and self.base3 != "0"


def fetch_relay_events(game_id: str) -> list[RelayEvent]:
    headers = {
        "User-Agent": USER_AGENT,
        "Referer": REFERER.format(game_id=game_id),
    }
    response = requests.get(API_URL.format(game_id=game_id), headers=headers, timeout=10)
    response.raise_for_status()
    data = response.json()

    collected_at = datetime.now(KST)
    groups = data["result"]["textRelayData"]["textRelays"]

    events = []
    for group in groups:
        top_bottom = TOP_BOTTOM.get(group["homeOrAway"], group["homeOrAway"])
        for option in group["textOptions"]:
            text = (option.get("text") or "").strip()
            if not text:
                continue
            state = option.get("currentGameState", {})
            events.append(
                RelayEvent(
                    game_id=game_id,
                    no=group["no"],
                    seqno=option["seqno"],
                    inning=group["inn"],
                    top_bottom=top_bottom,
                    text=text,
                    event_type=option.get("type", 0),
                    home_score=int(state.get("homeScore", 0)),
                    away_score=int(state.get("awayScore", 0)),
                    base1=state.get("base1", "0"),
                    base2=state.get("base2", "0"),
                    base3=state.get("base3", "0"),
                    outs=int(state.get("out", 0)),
                    collected_at=collected_at,
                )
            )

    events.sort(key=lambda e: e.seqno)
    return events
