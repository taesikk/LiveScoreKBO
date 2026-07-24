import logging
import time
from datetime import date, datetime, timedelta

from kbo_alert.active_hours import is_active_hours
from kbo_alert.config import TEAM_CODE
from kbo_alert.crawler import EventStore, ScheduledGame, fetch_relay_events, find_team_game
from kbo_alert.notifier import filter_important_events, format_event
from kbo_alert.slack.client import send_message

MONDAY = 0  # date.weekday()의 월요일 값, KBO는 월요일에 경기가 없음

POLL_INTERVAL_SECONDS = 30
IDLE_CHECK_INTERVAL_SECONDS = 300  # 오늘 경기가 없거나 활성 시간대 밖일 때는 덜 자주 확인
CANCEL_CHECK_LEAD_TIME = timedelta(minutes=10)  # 경기 시작 이만큼 전에 취소 여부 재확인

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def poll_once(game_id: str, store: EventStore) -> None:
    events = fetch_relay_events(game_id)

    # 전체 스냅샷 기준으로 먼저 중요 이벤트를 판별한 뒤(역전/만루/이닝종료는
    # 직전 이벤트와 비교하는 방식이라 매 폴링마다 새로 계산해야 함),
    # 그중 아직 안 보낸 것만 store로 걸러낸다.
    important_events = filter_important_events(events)
    important_by_seqno = {ie.event.seqno: ie for ie in important_events}

    new_relay_events = store.filter_new([ie.event for ie in important_events])
    new_important_events = [important_by_seqno[e.seqno] for e in new_relay_events]

    for important_event in new_important_events:
        message = format_event(important_event)
        send_message(message)
        logger.info("Sent (%s): %s", ",".join(important_event.reasons), message)


def _find_todays_game(team_code: str, today: date) -> ScheduledGame | None:
    if today.weekday() == MONDAY:
        logger.info("Monday - KBO has no games, skipping schedule lookup")
        return None

    game = find_team_game(team_code, today)
    if game:
        logger.info(
            "Today's game: %s vs %s (%s), starts %s",
            game.home_team_name,
            game.away_team_name,
            game.game_id,
            game.game_datetime,
        )
    else:
        logger.info("No game today for %s", team_code)
    return game


def run(team_code: str = TEAM_CODE) -> None:
    store = EventStore()
    logger.info("Starting KBO relay bot for team %s", team_code)

    checked_date: date | None = None
    todays_game: ScheduledGame | None = None
    confirmed = False  # 경기 시작 10분 전 취소 여부 재확인 완료했는지

    try:
        while True:
            today = date.today()
            if checked_date != today:
                checked_date = today
                confirmed = False
                todays_game = _find_todays_game(team_code, today)

            if todays_game is None:
                time.sleep(IDLE_CHECK_INTERVAL_SECONDS)
                continue

            if not confirmed:
                confirm_at = todays_game.game_datetime - CANCEL_CHECK_LEAD_TIME
                if datetime.now() < confirm_at:
                    time.sleep(IDLE_CHECK_INTERVAL_SECONDS)
                    continue

                latest = find_team_game(team_code, today)
                if latest is None or latest.cancel:
                    logger.info("Game cancelled, skipping for today")
                    todays_game = None
                    time.sleep(IDLE_CHECK_INTERVAL_SECONDS)
                    continue

                todays_game = latest
                confirmed = True
                logger.info("Confirmed not cancelled, starting polling")

            if not is_active_hours():
                time.sleep(IDLE_CHECK_INTERVAL_SECONDS)
                continue

            try:
                poll_once(todays_game.game_id, store)
            except Exception:
                logger.exception("Error during polling cycle")

            time.sleep(POLL_INTERVAL_SECONDS)
    finally:
        store.close()


if __name__ == "__main__":
    run()
