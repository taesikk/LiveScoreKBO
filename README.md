# LiveScoreKBO

KBO 문자중계를 폴링해서 중요 이벤트를 Slack으로 보내는 봇 + 매일 아침 경제/IT/정치 뉴스를 요약해서 Slack으로 보내는 브리핑, 두 가지를 담고 있는 프로젝트입니다.

## 기능

### KBO 경기 알림 ([scripts/run_bot.py](scripts/run_bot.py))

- `.env`에 설정한 팀들의 오늘 경기를 매일 자동으로 조회
- 경기가 있으면 시작 시각에 맞춰 "오늘 경기: A vs B" 안내를 팀별 Slack 채널로 1회 발송
- 경기가 없는 날(월요일 등)이나 우천취소 등으로 취소된 경우, 사유와 함께 안내
- 경기 시작 10분 전에 취소 여부를 한 번 더 확인
- 경기 중에는 30초 간격으로 네이버 스포츠 문자중계를 폴링해서 아래 이벤트가 발생하면 그때그때 발송:
  홈런 · 안타 · 도루 · 병살 · 아웃 · 볼넷 · 득점 · 역전 · 만루 · 이닝종료 · 경기종료
- 두 팀이 서로 맞대결하는 경우에도 각 팀 채널에 독립적으로 전부 발송됨 (팀별 dedup)

### 뉴스 브리핑 ([scripts/send_news_briefing.py](scripts/send_news_briefing.py))

- 경제 / IT / 정치 카테고리별로 뉴스 검색 API를 호출해서 상위 3건씩 추려 하나의 Slack 메시지로 발송
- 정리성 기사([오늘의 국회일정] 등)·통신사 중복 기사·지방행정 단신 기사를 걸러냄
- 하루 한 번(기본 KST 08:00) 실행되는 일회성 스크립트

## 동작 방식

두 기능 모두 화면을 긁는 크롤링이 아니라, 실제로 브라우저가 호출하는 내부 API를 그대로 호출합니다.

- **KBO 일정/문자중계**: `api-gw.sports.naver.com`의 비공개 API를 `requests`로 직접 호출 (네이버 뉴스 사이트 자체는 robots.txt로 크롤링이 전면 금지돼 있어서 대상이 아님)
- **뉴스**: 네이버 [검색 Open API](https://developers.naver.com)를 공식적으로 호출

## 프로젝트 구조

```
kbo_alert/
  active_hours.py      경기 알림을 보낼 활성 시간대(18~22시 KST) 판단
  timezone.py           KST 타임존 상수 (서버가 어느 시간대에 있든 항상 한국시간 기준으로 비교)
  config.py              환경변수 로딩
  crawler/                네이버 스포츠 API 호출 (일정 조회, 문자중계 조회)
  notifier/               중요 이벤트 필터링 + 메시지 포맷팅
  slack/                  Slack 메시지 발송

news_briefing/
  fetcher.py              네이버 검색 API 호출 + 필터링
  formatter.py             Slack 메시지 포맷팅

scripts/
  run_bot.py               KBO 봇 진입점 (상시 실행)
  send_news_briefing.py    뉴스 브리핑 진입점 (1회 실행)
  send_test_message.py     Slack 연동 테스트용

deploy/                   Oracle Cloud VM 배포용 (systemd 서비스/타이머 + 설치 스크립트)
.github/workflows/        main 브랜치 push 시 VM에 자동 배포
```

## 로컬 설정

```bash
python3 -m venv .venv
.venv/bin/pip install -e .
cp .env.example .env   # 값 채우기
```

`.env`에 필요한 값:

| 변수 | 설명 |
|---|---|
| `SLACK_BOT_TOKEN` | Slack 봇 토큰 (`xoxb-...`) |
| `SLACK_CHANNEL` | 테스트 메시지용 기본 채널 |
| `ANTHROPIC_API_KEY` | 현재 파이프라인에선 안 쓰지만 `config.py`가 필수로 요구함 (LLM 요약으로 다시 전환할 때 대비, [kbo_alert/notifier/summarizer.py](kbo_alert/notifier/summarizer.py) 참고) |
| `TEAM_SLACK_CHANNELS` | `팀코드:채널ID` 쌍을 쉼표로 구분. 예: `KT:C0BKGS13L02,HH:C0BKKGW1Y3B` |
| `NAVER_CLIENT_ID` / `NAVER_CLIENT_SECRET` | [네이버 개발자센터](https://developers.naver.com)에서 검색 API 애플리케이션 등록 후 발급 |
| `NEWS_SLACK_CHANNEL` | 뉴스 브리핑을 보낼 채널 ID |

봇은 채널에 초대(`/invite @봇이름`)돼 있어야 발송이 됩니다.

실행:

```bash
.venv/bin/python scripts/send_test_message.py     # 연동 테스트
.venv/bin/python scripts/run_bot.py                # KBO 봇 (상시 실행, Ctrl+C로 종료)
.venv/bin/python scripts/send_news_briefing.py     # 뉴스 브리핑 1회 실행
```

## 배포 (Oracle Cloud VM)

```bash
git clone <repo-url> && cd LiveScoreKBO
cp .env.example .env && vi .env
sudo bash deploy/setup.sh
```

`/opt/livescorekbo`에 전용 시스템 유저로 배치되고, systemd 서비스/타이머로 등록됩니다.

```bash
systemctl status kbo-alert.service          # KBO 봇 상태
journalctl -u kbo-alert.service -f          # KBO 봇 로그
systemctl status news-briefing.timer        # 뉴스 브리핑 타이머 상태
systemctl start news-briefing.service       # 뉴스 브리핑 즉시 테스트 실행
```

재배포(코드 변경 반영)는 `git pull` 후 `sudo bash deploy/setup.sh`를 다시 실행하면 됩니다 — 이미 떠있는 서비스도 자동으로 재시작됩니다.

## CI/CD

`main` 브랜치에 push되면 [.github/workflows/deploy.yml](.github/workflows/deploy.yml)이 SSH로 VM에 접속해서 위 재배포 과정을 그대로 수행합니다. 배포 후 `kbo-alert.service`가 살아있는지 확인해서, 죽어있으면 배포 자체를 실패 처리합니다.

필요한 GitHub Secrets: `OCI_HOST`, `OCI_USER`, `OCI_SSH_KEY` (VM 전용으로 발급한 SSH 개인키).

## 알아두면 좋은 제약사항

- KBO 문자중계 API는 항상 "최근 이벤트 창"만 반환합니다 (전체 경기 기록 조회용이 아님) — 실시간 폴링에는 적합하지만, 지나간 이닝을 나중에 다시 조회할 순 없습니다.
- 도루/병살 키워드는 실제 발생 사례로 완전히 검증되진 않았습니다 ([kbo_alert/notifier/filters.py](kbo_alert/notifier/filters.py) 참고).
- 뉴스 브리핑의 지방행정 필터는 규칙 기반이라 완벽하지 않습니다 (예: "OO시청" 패턴은 걸러지지만 "포항정치권"처럼 시/군/구 표기 없이 지명이 붙은 경우는 통과할 수 있음).
