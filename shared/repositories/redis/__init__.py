from redis.asyncio import Redis

from .session import SessionManager
from .timer import TimerManager

# Один экземпляр Redis на всё приложение
rdb = Redis(host='localhost')

# Менеджеры
session_manager = SessionManager(rdb)
timer_manager = TimerManager(rdb)

__all__ = ["session_manager", "timer_manager", "rdb"]
