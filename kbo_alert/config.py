import os

from dotenv import load_dotenv

load_dotenv()

SLACK_BOT_TOKEN = os.environ["SLACK_BOT_TOKEN"]
SLACK_CHANNEL = os.environ["SLACK_CHANNEL"]
ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]


def _parse_team_channels(raw: str) -> dict[str, str]:
    channels = {}
    for pair in raw.split(","):
        team_code, channel = pair.split(":", 1)
        channels[team_code.strip()] = channel.strip()
    return channels


# 네이버 스포츠 KBO 팀 코드 -> 알림 보낼 슬랙 채널. 예: "KT:kt알림,HH:한화알림"
TEAM_SLACK_CHANNELS = _parse_team_channels(os.environ["TEAM_SLACK_CHANNELS"])
