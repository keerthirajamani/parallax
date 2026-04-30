from datetime import date, timedelta
import calendar
import pandas as pd
import pandas_market_calendars as mcal

# weekday: Tuesday=1, Thursday=3
# weekly: whether weekly contracts exist (post-SEBI Nov 2024 rules)
INDEX_CONFIG = {
    "nifty":     {"weekday": 1, "calendar": "XNSE", "weekly": True},
    "sensex":    {"weekday": 3, "calendar": "XBOM", "weekly": True},
    "banknifty": {"weekday": 1, "calendar": "XNSE", "weekly": False},
    "finnifty":  {"weekday": 1, "calendar": "XNSE", "weekly": False},
}


def get_expiry(when: str = "current", kind: str = "weekly",
               index: str = "nifty", today: date | None = None) -> date:
    """
    F&O expiry date for Indian index derivatives.

    when  : "current" (nearest upcoming) | "next"
    kind  : "weekly" | "monthly"
    index : "nifty" | "sensex" | "banknifty" | "finnifty"
    """
    cfg = INDEX_CONFIG[index.lower()]

    if kind == "weekly" and not cfg["weekly"]:
        raise ValueError(
            f"{index} has no weekly contracts (discontinued by SEBI, Nov 2024). "
            f"Use kind='monthly'."
        )

    wd  = cfg["weekday"]
    cal = mcal.get_calendar(cfg["calendar"])

    today = today or date.today()
    valid = set(cal.valid_days(f"{today.year}-01-01",
                               f"{today.year + 1}-12-31").date)

    def adjust(d):
        while d not in valid:
            d -= timedelta(days=1)
        return d

    def last_target_day(y, m):
        last = date(y, m, calendar.monthrange(y, m)[1])
        return last - timedelta(days=(last.weekday() - wd) % 7)

    skip = {"current": 0, "next": 1}[when]

    if kind == "weekly":
        d = today + timedelta(days=(wd - today.weekday()) % 7)
        return adjust(d + timedelta(weeks=skip))

    if kind == "monthly":
        y, m, found = today.year, today.month, []
        while len(found) < skip + 1:
            exp = adjust(last_target_day(y, m))
            if exp >= today:
                found.append(exp)
            m += 1
            if m > 12:
                m, y = 1, y + 1
        return found[skip]

    raise ValueError(f"kind must be 'weekly' or 'monthly', got {kind!r}")


if __name__ == "__main__":
    for idx in INDEX_CONFIG:
        print(f"\n{idx.upper()}")
        for when in ("current", "next"):
            for kind in ("weekly", "monthly"):
                try:
                    d = get_expiry(when, kind, idx)
                    print(f"  {when:7} {kind:7}: {d}  {d:%a}")
                except ValueError:
                    print(f"  {when:7} {kind:7}: —  (no weeklies)")