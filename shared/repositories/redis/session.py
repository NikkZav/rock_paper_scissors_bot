import json
from shared.schemas.game_schemas import GameSession
from .base import RedisKVProtocol


class SessionManager:
    """
    SessionManager отвечает за сохранение, извлечение и удаление игровых сессий в Redis.
    Для ключей используется префикс "session:" плюс уникальный идентификатор сессии.
    """
    def __init__(self, redis_conn: RedisKVProtocol):
        self.redis = redis_conn
        self.prefix = "session:"  # Префикс ключей в Redis

    async def save_session(self, session: GameSession,
                           ttl: int = 3600) -> None:
        """
        Сохраняет сессию в Redis с указанным TTL (в секундах).
        setex устанавливает ключ со значением и временем жизни.
        """
        key = f"{self.prefix}{session.session_id}"
        # ttl здесь задаёт время жизни сессии, например, 1 час.
        await self.redis.setex(key, ttl, session.model_dump_json())

    async def get_session(self, session_id: str) -> GameSession | None:
        """
        Извлекает сессию по ключу из Redis.
        Если сессия не найдена, возвращает None.
        """
        key = f"{self.prefix}{session_id}"
        data = await self.redis.get(key)
        if data:
            return GameSession(**json.loads(data))
        return None

    async def delete_session(self, session_id: str) -> None:
        """
        Удаляет сессию из Redis по ключу.
        """
        key = f"{self.prefix}{session_id}"
        await self.redis.delete(key)

    @staticmethod
    def generate_session_id(user_id: int, opponent_id: int) -> str:
        # Убедимся, что идентификатор будет одинаков для обеих сторон
        ids = sorted((user_id, opponent_id))
        return f"{ids[0]}:{ids[1]}"