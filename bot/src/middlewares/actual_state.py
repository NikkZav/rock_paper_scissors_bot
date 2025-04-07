from typing import Any, Awaitable, Callable, Dict, Optional
from aiogram import BaseMiddleware
from aiogram.types import Update, TelegramObject
from src.database.db import online_users


class OnlineUserMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        def extract_user_id(update: Update) -> Optional[int]:
            # Извлекаем событие из Update
            if update.message:
                if update.message.from_user:
                    return update.message.from_user.id
            elif update.callback_query:
                return update.callback_query.from_user.id
            elif update.poll_answer:
                if update.poll_answer.user:
                    return update.poll_answer.user.id
            # Добавьте обработку других типов событий при необходимости
            return None

        # Приводим event к типу Update
        update_event = Update.model_validate(event, from_attributes=True)

        user_id = extract_user_id(update_event)
        if user_id is not None:
            online_users.set_online(user_id)
        else:
            print(f"No user info in event: {event}")

        return await handler(event, data)
