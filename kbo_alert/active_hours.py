from datetime import datetime, timedelta

from kbo_alert.timezone import KST

# KBO 정규 경기는 평균 3시간 안팎이지만 연장전을 감안해서 여유를 둔다.
GAME_WINDOW_DURATION = timedelta(hours=4, minutes=30)


def is_within_game_window(game_datetime: datetime, now: datetime | None = None) -> bool:
    """지금이 실제 경기 시작~종료 예상 시각 사이인지 확인한다.

    예전엔 활성 시간대를 18~22시로 고정해뒀는데, 주말 경기는 14시/17시에도
    시작해서 그 시간대엔 폴링 자체가 안 되는 버그가 있었다(1~4회 알림 누락으로
    실제 발견됨). 팀별로 조회한 실제 경기 시작 시각을 기준으로 판단해야
    평일/주말 상관없이 맞는다.
    """
    now = now or datetime.now(KST)
    return game_datetime <= now <= game_datetime + GAME_WINDOW_DURATION
