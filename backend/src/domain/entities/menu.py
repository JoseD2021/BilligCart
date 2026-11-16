from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone

@dataclass(frozen=True)
class Menu:
    week_start: date
    user_id: str
    id: int | None = None
    created_at: datetime | None = None

    @classmethod
    def default(cls, user_id: str) -> "Menu":
        today = datetime.now(timezone(timedelta(hours=-5))).date()
        return cls(user_id=user_id, week_start=today - timedelta(days=today.weekday()))
