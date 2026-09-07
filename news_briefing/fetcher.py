import html
import re
from dataclasses import dataclass

import requests

from news_briefing.config import NAVER_CLIENT_ID, NAVER_CLIENT_SECRET

SEARCH_API_URL = "https://openapi.naver.com/v1/search/news.json"
USER_AGENT = "kbo-alert-news-briefing/1.0"
FETCH_BUFFER = 40  # 필터링으로 걸러질 걸 감안해서 필요한 개수보다 넉넉히 가져온다.
# 15였을 때는 하나의 이슈(통신사 중복기사)가 상위권을 도배하면 중복 제거 후
# 진짜 다른 주제가 3개도 안 남는 경우가 있었다 - 실제로 재현해서 확인했다.

# 네이버 뉴스 섹션(정치/경제/IT) 크롤링은 robots.txt(Disallow: /)로 전면 금지돼 있어서,
# 대신 공식 네이버 검색 Open API를 카테고리별 키워드 검색으로 사용한다.
# 이 방식은 에디터가 고른 "TOP 3 헤드라인"이 아니라 검색 결과 상위 N건이라는 점에서
# 원래 요청과는 다른 근사치다. sort=date(최신순)는 검색어와 무관한 기사가 많이
# 섞여서 sort=sim(관련도순)으로 바꿨다 - 실제 API로 비교해서 확인한 결과다.
CATEGORY_CONFIG = {
    "경제": {"query": "경제", "sort": "sim", "exclude_local_gov": True},
    "IT": {"query": "IT업계", "sort": "sim", "exclude_local_gov": False},
    "정치": {"query": "정치", "sort": "sim", "exclude_local_gov": True},
}

_HTML_TAG_RE = re.compile(r"<[^>]+>")

# "오늘의 국회일정", "[포토] ..." 같이 개별 기사가 아니라 정리/사진 성격의 글
_ROUNDUP_TITLE_PATTERNS = ("오늘의", "이 시각", "주요일정", "헤드라인", "[포토]", "[사진]")

# 특정 지방자치단체 소식(시의회/구청 등)을 걸러내기 위한 패턴.
# "서울" 같은 지명 자체는 전국 뉴스에도 흔히 나오므로 블록하지 않고,
# 지방행정기관을 직접 다루는 기사만 걸러낸다.
_LOCAL_GOV_TITLE_PATTERNS = ("시의회", "도의회", "구의회", "군의회", "시청", "구청", "군청", "도청")

# "순천시·정치권"처럼 지명+시/군/구가 문장부호로 다른 단어와 바로 이어지는 건
# 그 지역 단신 기사인 경우가 많다.
_LOCAL_GOV_TITLE_RE = re.compile(r"[가-힣]+(시|군|구)[·,]")

# 주제 중복 판정에서 무시할 범용 단어(카테고리 검색어, 흔한 보도 표현 등).
# 이런 단어만 겹치는 건 "같은 주제"로 보지 않는다.
_TOPIC_STOPWORDS = {
    "정치",
    "경제",
    "IT업계",
    "IT",
    "대통령",
    "정부",
    "우리",
    "오늘",
    "이번",
    "관련",
    "위해",
    "대해",
    "이후",
    "기대",
    "발표",
    "정책",
    "산업",
    "시장",
    "확대",
    "추진",
}
_KEYWORD_SPLIT_RE = re.compile(r"[^\w가-힣]")


@dataclass(frozen=True)
class NewsItem:
    category: str
    title: str
    description: str
    link: str


def _clean_text(raw: str) -> str:
    return html.unescape(_HTML_TAG_RE.sub("", raw)).strip()


def _is_roundup_title(title: str) -> bool:
    return any(pattern in title for pattern in _ROUNDUP_TITLE_PATTERNS)


def _is_local_gov_title(title: str) -> bool:
    if any(pattern in title for pattern in _LOCAL_GOV_TITLE_PATTERNS):
        return True
    return bool(_LOCAL_GOV_TITLE_RE.search(title))


def _keywords(title: str) -> list[str]:
    words = _KEYWORD_SPLIT_RE.sub(" ", title).split()
    return [w for w in words if len(w) >= 2 and w not in _TOPIC_STOPWORDS]


def _shares_topic(title: str, seen_titles: list[str]) -> bool:
    """이미 고른 기사들과 주제가 겹치는지 확인한다.

    같은 사건을 다룬 기사끼리는 제목 표현이 완전히 달라도(예: '브라질서도 경제 강조'
    vs '브라질 도착…경제 대국') 핵심 키워드는 겹친다. 한국어는 조사가 명사에 바로
    붙어서('브라질' vs '브라질서도') 정확히 같은 단어인지 비교하면 놓치므로,
    부분 문자열 포함 여부로 비교한다.
    """
    keywords = _keywords(title)
    for seen in seen_titles:
        seen_keywords = _keywords(seen)
        if any(kw in sk or sk in kw for kw in keywords for sk in seen_keywords):
            return True
    return False


def fetch_category_news(
    category: str,
    query: str,
    count: int = 3,
    sort: str = "sim",
    exclude_local_gov: bool = False,
    exclude_links: frozenset[str] = frozenset(),
) -> list[NewsItem]:
    headers = {
        "X-Naver-Client-Id": NAVER_CLIENT_ID,
        "X-Naver-Client-Secret": NAVER_CLIENT_SECRET,
        "User-Agent": USER_AGENT,
    }
    params = {"query": query, "display": FETCH_BUFFER, "start": 1, "sort": sort}
    response = requests.get(SEARCH_API_URL, headers=headers, params=params, timeout=10)
    response.raise_for_status()
    data = response.json()

    items: list[NewsItem] = []
    seen_titles: list[str] = []

    for raw in data.get("items", []):
        title = _clean_text(raw["title"])
        link = raw.get("originallink") or raw["link"]

        if link in exclude_links:
            continue
        if _is_roundup_title(title):
            continue
        if exclude_local_gov and _is_local_gov_title(title):
            continue
        if _shares_topic(title, seen_titles):
            continue

        seen_titles.append(title)
        items.append(
            NewsItem(
                category=category,
                title=title,
                description=_clean_text(raw["description"]),
                link=link,
            )
        )

        if len(items) >= count:
            break

    return items
