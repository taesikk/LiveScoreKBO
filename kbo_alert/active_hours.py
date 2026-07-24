from datetime import datetime
from datetime import time as dtime

ACTIVE_START = dtime(18, 0)
ACTIVE_END = dtime(22, 0)


def is_active_hours(now: datetime | None = None) -> bool:
    now = now or datetime.now()
    return ACTIVE_START <= now.time() <= ACTIVE_END
