from dataclasses import dataclass
import datetime

@dataclass(frozen=True)
class Menu:
    week_start: datetime # la fecha a la que corresponde el menu (toda esa semana)
    user_id: str
    id: int | None = None
    created_at: datetime.date | None = None
    
    @classmethod
    def default(cls, user_id: str) -> "Menu":
        today = datetime.datetime.now()

        # calc lunes a las 00:00
        start_of_week = today - datetime.timedelta(days=today.weekday())
        start_of_week = start_of_week.replace(hour=0, minute=0, second=0, microsecond=0)
        start_of_week = start_of_week.strftime("%Y-%m-%d")

        return cls(user_id=user_id, week_start=start_of_week)