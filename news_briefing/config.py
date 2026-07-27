import os

from dotenv import load_dotenv

load_dotenv()

NAVER_CLIENT_ID = os.environ["NAVER_CLIENT_ID"]
NAVER_CLIENT_SECRET = os.environ["NAVER_CLIENT_SECRET"]
NEWS_SLACK_CHANNEL = os.environ["NEWS_SLACK_CHANNEL"]
