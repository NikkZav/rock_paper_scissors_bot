from aiogram import Router
from .user_handlers import menu_handlers, game_handlers


router = Router()
router.include_routers(
    menu_handlers.router,  # Подключаем роутер с меню
    game_handlers.router  # Подключаем роутер с игрой
)
