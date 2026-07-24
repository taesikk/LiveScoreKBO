from kbo_alert.slack.client import send_message

if __name__ == "__main__":
    send_message("테스트 메시지입니다")
    print("Sent.")
