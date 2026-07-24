from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

from kbo_alert.config import SLACK_BOT_TOKEN, SLACK_CHANNEL

_client = WebClient(token=SLACK_BOT_TOKEN)


def send_message(text: str, channel: str = SLACK_CHANNEL) -> None:
    try:
        _client.chat_postMessage(channel=channel, text=text)
    except SlackApiError as e:
        raise RuntimeError(f"Slack API error: {e.response['error']}") from e
