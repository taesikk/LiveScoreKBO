from kbo_alert.notifier.filters import ImportantEvent


def format_event(important_event: ImportantEvent) -> str:
    """LLM 호출 없이 규칙 기반으로 한 줄 메시지를 만든다."""
    event = important_event.event
    reasons = "/".join(important_event.reasons)
    return (
        f"[{event.inning}회{event.top_bottom} {reasons}] {event.text}"
        f" (홈 {event.home_score} : 원정 {event.away_score})"
    )
