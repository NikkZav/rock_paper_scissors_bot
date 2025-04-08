import json
from shared.schemas.game_schemas import GameTimer
from .base import RedisProtocol


class TimerManager:
    def __init__(self, redis_conn: RedisProtocol):
        self.redis = redis_conn
        self.zset_key = "game_timers"
        self.index_key = "game_timers:index"

    def _make_timer_key(self, session_id: str, timer_name: str) -> str:
        return f"{session_id}:{timer_name}"

    async def schedule_timer(self, session_id: str, timer_name: str,
                             frequency: float, timeout: float = 10.0) -> bool:
        key = self._make_timer_key(session_id, timer_name)
        exists = await self.redis.hget(self.index_key, key)
        if exists:
            return False

        timer = GameTimer(
            session_id=session_id,
            timer_name=timer_name,
            frequency=frequency,
            timeout=timeout
        )

        if timer.next_tick is None:
            raise ValueError("GameTimer.next_tick is None")

        element = timer.model_dump_json()
        await self.redis.zadd(self.zset_key,
                              {element: timer.next_tick.timestamp()})
        await self.redis.hset(self.index_key, key, element)
        return True

    async def get_timer(self,
                        session_id: str, timer_name: str) -> GameTimer | None:
        key = self._make_timer_key(session_id, timer_name)
        data = await self.redis.hget(self.index_key, key)
        if data is not None:
            return GameTimer(**json.loads(data))
        return None

    async def delete_timer(self, session_id: str, timer_name: str) -> None:
        key = self._make_timer_key(session_id, timer_name)
        data = await self.redis.hget(self.index_key, key)
        if data is not None:
            await self.redis.zrem(self.zset_key, data)
        await self.redis.hdel(self.index_key, key)
