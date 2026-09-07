import logging
import time
from dataclasses import dataclass
from datetime import date, datetime, timedelta

from kbo_alert.active_hours import is_within_game_window
from kbo_alert.config import TEAM_SLACK_CHANNELS
from kbo_alert.crawler import EventStore, ScheduledGame, fetch_relay_events, find_team_game
from kbo_alert.notifier import filter_important_events, format_event
from kbo_alert.slack.client import send_message
from kbo_alert.timezone import KST

MONDAY = 0  # date.weekday()의 월요일 값, KBO는 월요일에 경기가 없음

POLL_INTERVAL_SECONDS = 15  # 문자중계 API가 "최근 이벤트 창"만 주기 때문에, 너무 뜸하게 폴링하면
# 이닝 전환처럼 짧은 시간에 이벤트가 몰릴 때 창이 밀려서 일부를 아예 못 볼 수 있다.
IDLE_CHECK_INTERVAL_SECONDS = 300  # 오늘 경기가 없거나 활성 시간대 밖일 때는 덜 자주 확인
CANCEL_CHECK_LEAD_TIME = timedelta(minutes=10)  # 경기 시작 이만큼 전에 취소 여부 재확인

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def poll_once(state: "TeamState", store: EventStore) -> None:
    game_id = state.todays_game.game_id
    channel = state.channel
    events = fetch_relay_events(game_id)

    if events:
        # API가 "최근 이벤트 창"만 주므로, 지난 폴링 때 본 마지막 seqno와 이번 창의
        # 시작 seqno 사이에 빈틈이 있으면 그 사이 이벤트를 통째로 놓친 것이다.
        current_min = min(e.seqno for e in events)
        current_max = max(e.seqno for e in events)
        if state.last_seqno_seen is not None and current_min > state.last_seqno_seen + 1:
            logger.warning(
                "%s: seqno %d~%d 사이 이벤트를 놓쳤을 수 있음 (문자중계 창이 그 사이 넘어감)",
                channel,
                state.last_seqno_seen + 1,
                current_min - 1,
            )
        state.last_seqno_seen = current_max

    # 전체 스냅샷 기준으로 먼저 중요 이벤트를 판별한 뒤(역전/만루/이닝종료는
    # 직전 이벤트와 비교하는 방식이라 매 폴링마다 새로 계산해야 함),
    # 그중 아직 안 보낸 것만 store로 걸러낸다.
    important_events = filter_important_events(events)
    important_by_seqno = {ie.event.seqno: ie for ie in important_events}

    new_relay_events = store.filter_new([ie.event for ie in important_events], channel)
    new_important_events = [important_by_seqno[e.seqno] for e in new_relay_events]

    for important_event in new_important_events:
        message = format_event(important_event)
        try:
            send_message(message, channel=channel)
        except Exception:
            # 이 이벤트는 store에 이미 처리됨으로 기록됐으니 재전송은 안 되지만,
            # 최소한 배치 안의 나머지 이벤트들은 계속 보내야 한다.
            logger.exception("Failed to send message to %s: %s", channel, message)
            continue
        logger.info("Sent to %s (%s): %s", channel, ",".join(important_event.reasons), message)


def _find_todays_game(team_code: str, today: date) -> ScheduledGame | None:
    if today.weekday() == MONDAY:
        logger.info("Monday - KBO has no games, skipping schedule lookup for %s", team_code)
        return None

    game = find_team_game(team_code, today)
    if game:
        logger.info(
            "Today's game for %s: %s vs %s (%s), starts %s",
            team_code,
            game.home_team_name,
            game.away_team_name,
            game.game_id,
            game.game_datetime,
        )
    else:
        logger.info("No game today for %s", team_code)
    return game


def _no_game_reason(today: date) -> str:
    if today.weekday() == MONDAY:
        return "월요일은 KBO 경기가 없는 날입니다."
    return "오늘 예정된 경기가 없습니다."


@dataclass
class TeamState:
    team_code: str
    channel: str
    checked_date: date | None = None
    todays_game: ScheduledGame | None = None
    confirmed: bool = False  # 경기 시작 10분 전 취소 여부 재확인 완료했는지
    announced: bool = False  # 오늘 경기 안내(또는 경기없음/취소 안내)를 이미 보냈는지
    last_seqno_seen: int | None = None  # 문자중계 창에서 마지막으로 본 최대 seqno (유실 감지용)


def _step(state: TeamState, store: EventStore) -> bool:
    """이 팀에 대해 한 틱 처리. 실제로 폴링했으면 True.

    아래 send_message 호출들은 일부러 try/except로 감싸지 않는다 - 실패하면 예외가
    run()의 팀별 try/except까지 전파되고, 그 시점엔 아직 관련 플래그(announced/confirmed 등)를
    갱신하기 전이라 다음 틱에 자동으로 재시도된다.
    """
    today = datetime.now(KST).date()
    if state.checked_date != today:
        # 일정 조회가 실패해도(네트워크 오류 등) checked_date를 먼저 바꾸지 않아야
        # 다음 틱에 오늘 일정을 다시 조회한다.
        game = _find_todays_game(state.team_code, today)
        state.checked_date = today
        state.confirmed = False
        state.announced = False
        state.todays_game = game

    if state.todays_game is None:
        if not state.announced:
            # 경기가 없는 날은 "시작 시각"이 없으니, 확인되는 즉시 한 번만 안내한다.
            message = f"[{state.team_code}] 오늘 경기 없음 - {_no_game_reason(today)}"
            send_message(message, channel=state.channel)
            logger.info("Sent to %s (경기없음): %s", state.channel, message)
            state.announced = True
        return False

    if not state.confirmed:
        confirm_at = state.todays_game.game_datetime - CANCEL_CHECK_LEAD_TIME
        if datetime.now(KST) < confirm_at:
            return False

        latest = find_team_game(state.team_code, today)
        if latest is None or latest.cancel:
            reason = (latest.status_info if latest else None) or "사유 확인 불가"
            logger.info("Game cancelled for %s: %s", state.team_code, reason)
            send_message(f"[{state.team_code}] 오늘 경기 취소 - {reason}", channel=state.channel)
            state.todays_game = None
            state.announced = True
            return False

        state.todays_game = latest
        state.confirmed = True
        logger.info("Confirmed not cancelled for %s, starting polling", state.team_code)

    if not state.announced and datetime.now(KST) >= state.todays_game.game_datetime:
        game = state.todays_game
        message = f"[{state.team_code}] 오늘 경기: {game.home_team_name} vs {game.away_team_name} ({game.stadium})"
        send_message(message, channel=state.channel)
        logger.info("Sent to %s (경기안내): %s", state.channel, message)
        state.announced = True

    if not is_within_game_window(state.todays_game.game_datetime):
        return False

    try:
        poll_once(state, store)
    except Exception:
        logger.exception("Error during polling cycle for %s", state.team_code)

    return True


def _safe_step(state: TeamState, store: EventStore) -> bool:
    """한 팀 처리 중 어떤 예외가 나도 여기서 멈추고, 다른 팀/다음 틱에 영향 안 주게 한다."""
    try:
        return _step(state, store)
    except Exception:
        logger.exception("Unhandled error while processing %s - will retry next tick", state.team_code)
        return False


def run(team_channels: dict[str, str] = TEAM_SLACK_CHANNELS) -> None:
    store = EventStore()
    states = [TeamState(team_code=code, channel=channel) for code, channel in team_channels.items()]
    logger.info("Starting KBO relay bot for teams: %s", ", ".join(team_channels))

    try:
        while True:
            polled = [_safe_step(state, store) for state in states]
            time.sleep(POLL_INTERVAL_SECONDS if any(polled) else IDLE_CHECK_INTERVAL_SECONDS)
    finally:
        store.close()


if __name__ == "__main__":
    run()
