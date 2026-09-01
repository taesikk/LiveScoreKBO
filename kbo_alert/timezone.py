from zoneinfo import ZoneInfo

# 서버가 어느 시간대에서 돌든(예: Oracle Cloud 기본값인 UTC) KBO 경기 시각은
# 항상 한국시간 기준이라, 모든 시각 비교는 이 시간대로 명시적으로 고정한다.
KST = ZoneInfo("Asia/Seoul")
