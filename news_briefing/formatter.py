import re
from datetime import date

from news_briefing.fetcher import NewsItem

CATEGORY_ORDER = ["경제", "IT", "정치"]
HEADLINE_MAX_LEN = 60
SUMMARY_MAX_LEN = 200

# 마침표/물음표/느낌표 뒤에 공백이 와야 문장 경계로 본다("..."도 뒤에 공백이 있으면
# 하나의 경계로 취급됨) - URL이나 "3.1%" 같은 숫자 안의 마침표는 뒤에 공백이 없어서
# 걸리지 않는다.
_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")


def _truncate_headline(text: str, max_len: int) -> str:
    if len(text) <= max_len:
        return text
    return text[:max_len].rstrip() + "…"


def _truncate_summary(text: str, max_len: int) -> str | None:
    """max_len은 상한선일 뿐, 채우려고 하지 않는다 - 문장이 끝나면 거기서 멈춘다.

    문장 단위로 통째로 담을 수 있는 만큼만 담고, 다음 문장이 상한선을 넘기면
    그 문장은 아예 포함하지 않는다(잘린 문장을 보여주지 않음). 첫 문장부터
    이미 상한선을 넘으면 보여줄 게 없다는 뜻으로 None을 반환한다.
    """
    if len(text) <= max_len:
        return text

    sentences = _SENTENCE_SPLIT_RE.split(text)

    result = ""
    for sentence in sentences:
        candidate = f"{result} {sentence}".strip() if result else sentence
        if len(candidate) > max_len:
            break
        result = candidate

    return result or None


def build_message(items_by_category: dict[str, list[NewsItem]], today: date | None = None) -> str:
    today = today or date.today()
    lines = [f"📰 오늘의 뉴스 브리핑 ({today.isoformat()})", ""]

    for category in CATEGORY_ORDER:
        items = items_by_category.get(category, [])
        lines.append(f"*{category}*")
        if not items:
            lines.append("- 뉴스를 가져오지 못했습니다.")
        else:
            for i, item in enumerate(items, 1):
                lines.append(f"{i}. *{_truncate_headline(item.title, HEADLINE_MAX_LEN)}*")
                summary = _truncate_summary(item.description, SUMMARY_MAX_LEN) if item.description else None
                if summary:
                    lines.append(f"    {summary}")
                lines.append(f"    {item.link}")
        lines.append("")

    return "\n".join(lines).rstrip()
