from pydantic import BaseModel, Field, field_validator
from datetime import datetime, timezone, timedelta


class GameSession(BaseModel):
    """
    Класс GameSession описывает временную игровую сессию.
    Здесь мы храним идентификатор сессии, статус игры и время создания.
    В данной концепции сессия хранится в Redis, поэтому объект сериализуется в JSON.
    """
    session_id: str   # например "123:456"
    status: str       # например "pending", "accepted", "finished" и т.д.
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def model_post_init(self, __context: dict) -> None:
        # Если кто-то передал created_at=None, исправим на текущее время
        if self.created_at.tzinfo is None:
            self.created_at = datetime.now(timezone.utc)


DEFAULT_TIMEOUT = 10.0  # в секундах
DEFAULT_FREQUENCY = 0.1  # в секундах


class GameTimer(BaseModel):
    session_id: str
    timer_name: str
    frequency: float = DEFAULT_FREQUENCY
    timeout: float = DEFAULT_TIMEOUT  # время жизни таймера в секундах
    expire_at: datetime | None = None
    next_tick: datetime | None = None

    def model_post_init(self, __context: dict) -> None:
        now = datetime.now(timezone.utc)
        # Если expire_at не задано, вычисляем его как now + timeout секунд
        if self.expire_at is None:
            self.expire_at = now + timedelta(seconds=self.timeout)
        # Если next_tick не задано, вычисляем его как now + frequency секунд
        if self.next_tick is None:
            self.next_tick = now + timedelta(seconds=self.frequency)

    def model_dump(self, *args, **kwargs) -> dict:
        data = super().model_dump(*args, **kwargs)
        # timeout больше не нужен при сериализации
        data.pop("timeout", None)
        return data

    def model_dump_json(self, *args, **kwargs) -> str:
        exclude = set(kwargs.pop("exclude", set())) | {"timeout"}
        return super().model_dump_json(*args, exclude=exclude, **kwargs)
