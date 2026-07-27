import logging
import time

from kbo_alert.slack.client import send_message
from news_briefing.config import NEWS_SLACK_CHANNEL
from news_briefing.fetcher import CATEGORY_CONFIG, fetch_category_news
from news_briefing.formatter import build_message

REQUEST_INTERVAL_SECONDS = 1.0  # 카테고리별 API 호출 사이 간격

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def run() -> None:
    items_by_category = {}

    for category, config in CATEGORY_CONFIG.items():
        try:
            items = fetch_category_news(
                category,
                config["query"],
                sort=config["sort"],
                exclude_local_gov=config["exclude_local_gov"],
            )
            if len(items) < 3:
                logger.warning("%s 카테고리 뉴스가 %d건만 확보됨 (3건 기대)", category, len(items))
            items_by_category[category] = items
        except Exception:
            logger.exception("%s 카테고리 뉴스 조회 실패", category)
            items_by_category[category] = []

        time.sleep(REQUEST_INTERVAL_SECONDS)

    message = build_message(items_by_category)
    send_message(message, channel=NEWS_SLACK_CHANNEL)
    logger.info("뉴스 브리핑 전송 완료")


if __name__ == "__main__":
    run()
