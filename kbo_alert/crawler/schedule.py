from dataclasses import dataclass
from datetime import date, datetime

import requests

SCHEDULE_API_URL = "https://api-gw.sports.naver.com/schedule/games"
REFERER = "https://m.sports.naver.com/"
USER_AGENT = "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15"


@dataclass(frozen=True)
class ScheduledGame:
    game_id: str
    game_datetime: datetime
    stadium: str
    home_team_code: str
    home_team_name: str
    away_team_code: str
    away_team_name: str
    status_code: str  # "BEFORE" | "LIVE" | "RESULT" 등
    status_info: str  # 예: "경기전", 우천취소 시 관련 문구가 들어올 것으로 예상 (미검증)
    cancel: bool


def fetch_games_on(day: date) -> list[ScheduledGame]:
    date_str = day.isoformat()
    params = {
        "fields": "basic,schedule,baseball,manualRelayUrl",
        "upperCategoryId": "kbaseball",
        "categoryId": "kbo",
        "fromDate": date_str,
        "toDate": date_str,
        "roundCodes": "",
        "size": 500,
    }
    headers = {"User-Agent": USER_AGENT, "Referer": REFERER}
    response = requests.get(SCHEDULE_API_URL, params=params, headers=headers, timeout=10)
    response.raise_for_status()
    data = response.json()

    return [
        ScheduledGame(
            game_id=g["gameId"],
            game_datetime=datetime.fromisoformat(g["gameDateTime"]),
            stadium=g["stadium"],
            home_team_code=g["homeTeamCode"],
            home_team_name=g["homeTeamName"],
            away_team_code=g["awayTeamCode"],
            away_team_name=g["awayTeamName"],
            status_code=g["statusCode"],
            status_info=g.get("statusInfo", ""),
            cancel=g["cancel"],
        )
        for g in data["result"]["games"]
    ]


def find_team_game(team_code: str, day: date | None = None) -> ScheduledGame | None:
    """team_code가 홈/원정 어느 쪽이든 참여하는 그날 경기를 찾는다. 없으면 None."""
    day = day or date.today()
    for game in fetch_games_on(day):
        if team_code in (game.home_team_code, game.away_team_code):
            return game
    return None
