import os

from dotenv import load_dotenv

load_dotenv()

SLACK_BOT_TOKEN = os.environ["SLACK_BOT_TOKEN"]
SLACK_CHANNEL = os.environ["SLACK_CHANNEL"]
ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]
TEAM_CODE = os.environ["TEAM_CODE"]  # 네이버 스포츠 KBO 팀 코드, 예: KT Wiz -> "KT"
