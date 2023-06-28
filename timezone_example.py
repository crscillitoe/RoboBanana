from datetime import datetime, timezone, timedelta
import pytz
from time import sleep

def option_one():
    hour = 12
    utc_now = datetime.utcnow()

    local_tz_unaware = utc_now.replace(hour=hour)
    tzinfo = timezone(local_tz_unaware - utc_now)
    local_tz_aware = local_tz_unaware.replace(tzinfo=tzinfo)
    
    tz_offset = local_tz_aware.utcoffset()
    sleep(1)

    now = datetime.utcnow()
    apply_timezone = now + tz_offset
    apply_timezone = apply_timezone.replace(tzinfo=timezone(tz_offset))
    print(apply_timezone.isoformat())

def option_two():
    utc = pytz.utc
    utc_dt = datetime.now(utc)
    pacific = pytz.timezone("US/Pacific")
    local_dt = utc_dt.astimezone(pacific)
    print(local_dt.isoformat())

if __name__ == "__main__":
    option_one()
    option_two()