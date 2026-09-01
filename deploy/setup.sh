#!/usr/bin/env bash
# Oracle Cloud VM에서 이 저장소를 git clone한 디렉토리 안에서 실행한다.
#   git clone <repo-url> && cd LiveScoreKBO
#   cp .env.example .env && vi .env   # 실제 값 채우기
#   sudo bash deploy/setup.sh
set -euo pipefail

APP_DIR="/opt/livescorekbo"
SERVICE_USER="livescorekbo"
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [ ! -f "$REPO_DIR/.env" ]; then
  echo "에러: $REPO_DIR/.env 가 없습니다. .env.example을 복사해서 실제 값을 채운 뒤 다시 실행하세요." >&2
  exit 1
fi

if ! id -u "$SERVICE_USER" &>/dev/null; then
  useradd --system --create-home --home-dir "$APP_DIR" --shell /usr/sbin/nologin "$SERVICE_USER"
fi

mkdir -p "$APP_DIR"
rsync -a --delete \
  --exclude='.venv' --exclude='.git' --exclude='data' --exclude='__pycache__' \
  "$REPO_DIR"/ "$APP_DIR"/

# 실행 중 상태(SQLite dedup DB)는 재배포해도 유지되게 별도로 보존
mkdir -p "$APP_DIR/data"

python3 -m venv "$APP_DIR/.venv"
"$APP_DIR/.venv/bin/pip" install --no-cache-dir --upgrade pip
"$APP_DIR/.venv/bin/pip" install --no-cache-dir -e "$APP_DIR"

chown -R "$SERVICE_USER:$SERVICE_USER" "$APP_DIR"
chmod 600 "$APP_DIR/.env"

cp "$REPO_DIR"/deploy/kbo-alert.service /etc/systemd/system/
cp "$REPO_DIR"/deploy/news-briefing.service /etc/systemd/system/
cp "$REPO_DIR"/deploy/news-briefing.timer /etc/systemd/system/
systemctl daemon-reload

# enable --now은 이미 떠있는 서비스는 재시작시키지 않으므로(이미 active면 no-op),
# 재배포 때 새 코드가 실제로 적용되도록 enable과 restart를 분리해서 항상 재시작한다.
systemctl enable kbo-alert.service
systemctl restart kbo-alert.service
systemctl enable news-briefing.timer
systemctl restart news-briefing.timer

echo "완료."
echo "  KBO 봇 상태:      systemctl status kbo-alert.service"
echo "  KBO 봇 로그:      journalctl -u kbo-alert.service -f"
echo "  뉴스 브리핑 타이머: systemctl status news-briefing.timer"
echo "  뉴스 브리핑 즉시 테스트: systemctl start news-briefing.service"
