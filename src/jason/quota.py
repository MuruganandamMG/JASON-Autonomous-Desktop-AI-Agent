import time
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

def pacific_reset(stamp):
    local = datetime.fromtimestamp(stamp, ZoneInfo("America/Los_Angeles"))
    return datetime.combine(local.date() + timedelta(days=1), datetime.min.time(), local.tzinfo).timestamp()

class QuotaWait(Exception):
    def __init__(self, reason, retry_at=None):
        super().__init__(reason)
        self.retry_at = retry_at

class Quota:
    def __init__(self, store, limits, now=time.time):
        self.store, self.limits, self.now = store, limits, now
        self.cooldowns = {}
    def reserve(self, model, tokens):
        stamp = self.now()
        rpm, tpm, rpd = self.limits.get(model, (0,0,0))
        if min(rpm,tpm,rpd) <= 0:
            raise QuotaWait("Quota unknown/zero; configure actual Free-tier limits in AI Studio.")
        if self.cooldowns.get(model,0) > stamp:
            raise QuotaWait("Provider cooldown.", self.cooldowns[model])
        records = [r for r in self.store.usage() if r["model"] == model]
        day_start = pacific_reset(stamp) - 86400
        # Derive the actual local midnight, including 23/25-hour DST days.
        local = datetime.fromtimestamp(stamp, ZoneInfo("America/Los_Angeles"))
        day_start = datetime.combine(local.date(), datetime.min.time(), local.tzinfo).timestamp()
        daily = [r for r in records if r["stamp"] >= day_start]
        minute = [r for r in records if r["stamp"] > stamp-60]
        if len(daily) >= rpd:
            raise QuotaWait("Estimated daily request limit reached.", pacific_reset(stamp))
        if tokens > tpm:
            raise QuotaWait("Request context exceeds configured input TPM; reduce context.")
        if len(minute) >= rpm or sum(r["tokens"] for r in minute)+tokens > tpm:
            raise QuotaWait("Estimated minute quota reached.", min(r["stamp"] for r in minute)+61)
        return self.store.record_usage(model, stamp, tokens)

