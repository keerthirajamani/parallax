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

def get_nse_holidays(year: int | None = None,
                     calendar_name: str = "XNSE") -> list[date]:
    """
    NSE trading holidays for a given calendar year (excluding weekends).

    Returns full-day market closures only — does not include Muhurat
    trading sessions (e.g. Diwali Laxmi Pujan) which fall on weekends.
    """
    year = year or date.today().year
    cal = mcal.get_calendar(calendar_name)
    holidays = cal.holidays().holidays
    return sorted(
        date.fromisoformat(str(h)[:10])
        for h in holidays
        if str(h).startswith(str(year))
    )

def is_nse_holiday(d: date, calendar_name: str = "XNSE") -> bool:
    """True if d is a weekday NSE holiday (weekends return False)."""
    if d.weekday() >= 5:
        return False
    return d in get_nse_holidays(d.year, calendar_name)

def is_last_trading_day_of_week(d: date, calendar_name: str = "XNSE") -> int:
    """1 if d is the final trading day of its ISO week (Mon–Sun), else 0."""
    cal = mcal.get_calendar(calendar_name)
    monday = d - timedelta(days=d.weekday())
    sunday = monday + timedelta(days=6)
    valid = cal.valid_days(monday.isoformat(), sunday.isoformat()).date
    return int(len(valid) > 0 and d == max(valid))


if __name__ == "__main__":
    today = date.today()
    print(is_last_trading_day_of_week(today))
    if not is_last_trading_day_of_week(today):
        print("Not last trading day — skipping weekly signals")
    else:
        print("last trading day — No skipping weekly signals")

        

    # for h in get_nse_holidays(2026):
    #     print(f"{h}  {h:%A}")
    # for idx in INDEX_CONFIG:
    #     print(f"\n{idx.upper()}")
    #     for when in ("current", "next"):
    #         for kind in ("weekly", "monthly"):
    #             try:
    #                 d = get_expiry(when, kind, idx)
    #                 print(f"  {when:7} {kind:7}: {d}  {d:%a}")
    #             except ValueError:
    #                 print(f"  {when:7} {kind:7}: —  (no weeklies)")