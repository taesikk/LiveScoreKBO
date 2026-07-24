from kbo_alert.notifier.filters import ImportantEvent

SYSTEM_PROMPT = (
    "너는 KBO 야구 경기 문자중계를 한 줄로 요약하는 스포츠 캐스터야. "
    "주어진 상황 정보를 바탕으로 팬이 바로 이해할 수 있는 한국어 한 문장으로 핵심만 전달해. "
    "이모지나 과장된 감탄사 없이, 사실 위주로 담백하게 써."
)

USER_PROMPT_TEMPLATE = """\
[경기 상황]
- {inning}회 {top_bottom}
- 스코어: 홈 {home_score} : 원정 {away_score}
- 감지된 이벤트: {reasons}

[중계 원문]
{text}

위 상황을 한 문장으로 요약해줘.
"""


def build_user_prompt(important_event: ImportantEvent) -> str:
    event = important_event.event
    return USER_PROMPT_TEMPLATE.format(
        inning=event.inning,
        top_bottom=event.top_bottom,
        home_score=event.home_score,
        away_score=event.away_score,
        reasons=", ".join(important_event.reasons),
        text=event.text,
    )
