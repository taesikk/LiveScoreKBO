import anthropic

from kbo_alert.config import ANTHROPIC_API_KEY
from kbo_alert.notifier.filters import ImportantEvent
from kbo_alert.notifier.prompts import SYSTEM_PROMPT, build_user_prompt

MODEL = "claude-sonnet-5"

_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)


def summarize(important_event: ImportantEvent) -> str:
    # 정형화된 문구를 한 줄로 다듬는 단순 작업이라 thinking은 끔 (지연시간 최소화).
    response = _client.messages.create(
        model=MODEL,
        max_tokens=300,
        system=SYSTEM_PROMPT,
        thinking={"type": "disabled"},
        messages=[{"role": "user", "content": build_user_prompt(important_event)}],
    )
    return next(block.text for block in response.content if block.type == "text").strip()
