from datetime import date

from news_briefing.fetcher import NewsItem

CATEGORY_ORDER = ["경제", "IT", "정치"]
SUMMARY_MAX_LEN = 40


def summarize(item: NewsItem, max_len: int = SUMMARY_MAX_LEN) -> str:
    """제목이 이미 간결하면 그대로 쓰고, 길면 잘라서 한 줄 요약처럼 만든다.

    기사 본문을 직접 열어서 요약하지는 않는다 - 개별 언론사 페이지까지
    크롤링 범위를 넓히면 매체별 robots.txt를 다 따로 확인해야 해서,
    API가 이미 제공하는 title/description만 사용한다.
    """
    text = item.title or item.description
    if len(text) <= max_len:
        return text
    return text[:max_len].rstrip() + "…"


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
                lines.append(f"{i}. {summarize(item)} - {item.link}")
        lines.append("")

    return "\n".join(lines).rstrip()
