import asyncio
import time
from typing import TypeAlias

# Определяем тип для хранения времени активности
activity_time: TypeAlias = float


# Класс для хранения онлайн-пользователей
class OnlineUsers:
    def __init__(self, online_duration: int) -> None:
        self.online_duration = online_duration
        self.users: dict[int, activity_time] = {}

    def set_online(self, user_id: int) -> None:
        # Записываем время последней активности
        self.users[user_id] = time.monotonic()
        print(f"User {user_id} set online. Current users: {self.users}")

    def cleanup(self) -> None:
        # Удаляем пользователей, у которых время активности истекло
        now = time.monotonic()
        to_remove = [
            user_id for user_id, last_seen in self.users.items()
            if now - last_seen >= self.online_duration
        ]
        for user_id in to_remove:
            del self.users[user_id]


# Глобальный объект для отслеживания онлайн-пользователей
online_users = OnlineUsers(online_duration=60)


async def cleanup_task(online_users: OnlineUsers) -> None:
    """Периодически очищает список онлайн пользователей."""
    while True:
        await asyncio.sleep(10)
        online_users.cleanup()
        print("Online users:", online_users.users)

# Сообщаем, что модуль успешно импортирован
print("Модуль database.db импортирован")
