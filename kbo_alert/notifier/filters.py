from dataclasses import dataclass

from kbo_alert.crawler.relay import RelayEvent

HOMERUN_KEYWORDS = ("홈런",)
HIT_KEYWORDS = ("안타", "1루타", "2루타", "3루타")
STEAL_KEYWORDS = ("도루",)
DOUBLE_PLAY_KEYWORDS = ("병살",)
GAME_END_KEYWORDS = ("승리투수", "경기 종료", "경기종료")


@dataclass(frozen=True)
class ImportantEvent:
    event: RelayEvent
    reasons: list[str]


def _leader(event: RelayEvent) -> str:
    if event.home_score > event.away_score:
        return "home"
    if event.away_score > event.home_score:
        return "away"
    return "tie"


def _is_homerun(event: RelayEvent) -> bool:
    return any(keyword in event.text for keyword in HOMERUN_KEYWORDS)


def _is_hit(event: RelayEvent) -> bool:
    return any(keyword in event.text for keyword in HIT_KEYWORDS)


def _is_steal(event: RelayEvent) -> bool:
    return any(keyword in event.text for keyword in STEAL_KEYWORDS)


def _is_double_play(event: RelayEvent) -> bool:
    return any(keyword in event.text for keyword in DOUBLE_PLAY_KEYWORDS)


def _is_game_end(event: RelayEvent) -> bool:
    return any(keyword in event.text for keyword in GAME_END_KEYWORDS)


def filter_important_events(events: list[RelayEvent]) -> list[ImportantEvent]:
    """events must be sorted by seqno ascending (fetch_relay_events already does this).

    역전/만루/이닝종료는 템플릿 텍스트에 단어로 나오지 않아서, 스코어·주자·아웃카운트 변화를
    직접 비교해서 판단한다. 같은 상황이 여러 이벤트에 걸쳐 유지될 때 매번 잡히지 않도록,
    상태가 "바뀌는 순간"만 잡는다(rising edge). outs==3이 되는 이벤트가 정확히 그 반이닝의
    마지막 플레이라는 건 실제 응답으로 확인했다.
    """
    important = []
    prev_leader = None
    prev_bases_loaded = False
    prev_outs = 0

    for event in events:
        reasons = []

        if _is_homerun(event):
            reasons.append("홈런")

        if _is_hit(event):
            reasons.append("안타")

        if _is_steal(event):
            reasons.append("도루")

        if _is_double_play(event):
            reasons.append("병살")

        if _is_game_end(event):
            reasons.append("경기종료")

        leader = _leader(event)
        if prev_leader is not None and leader != "tie" and leader != prev_leader:
            reasons.append("역전")

        if event.bases_loaded and not prev_bases_loaded:
            reasons.append("만루")

        if event.outs == 3 and prev_outs != 3:
            reasons.append("이닝종료")

        if reasons:
            important.append(ImportantEvent(event=event, reasons=reasons))

        prev_leader = leader
        prev_bases_loaded = event.bases_loaded
        prev_outs = event.outs

    return important
