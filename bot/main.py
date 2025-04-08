import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from src.config_data.config import Config, load_config
from src.handlers import other_handlers, user_routers
from src.middlewares.middlewares import OnlineUserMiddleware, DataBaseMiddleware
from shared.repositories.db import cleanup_task, online_users
from aiogram.fsm.storage.redis import RedisStorage
from redis.asyncio import Redis


# Инициализируем логгер
logger = logging.getLogger(__name__)


# Функция конфигурирования и запуска бота
async def main():
    # Конфигурируем логирование
    logging.basicConfig(
        level=logging.INFO,
        format='%(filename)s:%(lineno)d #%(levelname)-8s '
               '[%(asctime)s] - %(name)s - %(message)s')

    # Выводим в консоль информацию о начале запуска бота
    logger.info('Starting bot')

    # Загружаем конфиг в переменную config
    config: Config = load_config()

    # Инициализируем Redis
    rdb = Redis(host='localhost')

    # Инициализируем хранилище (создаем экземпляр класса MemoryStorage)
    storage = RedisStorage(redis=rdb)

    # Инициализируем бот и диспетчер
    bot = Bot(
        token=config.tg_bot.token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    dp = Dispatcher(storage=storage)

    asyncio.create_task(cleanup_task(online_users))

    # Регистрация middleware
    dp.update.outer_middleware(DataBaseMiddleware(rdb=rdb))
    dp.update.middleware(OnlineUserMiddleware())

    # Регистриуем роутеры в диспетчере
    dp.include_router(user_routers.router)
    dp.include_router(other_handlers.router)

    # Пропускаем накопившиеся апдейты и запускаем polling
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


asyncio.run(main())
