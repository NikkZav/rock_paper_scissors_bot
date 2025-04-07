from aiogram import Router
from aiogram.types import Message
from src.lexicon.lexicon_ru import LEXICON

router = Router()


# Хэндлер для сообщений, которые не попали в другие хэндлеры
@router.message()
async def send_answer(message: Message):
    await message.answer(text=LEXICON["other_answer"])
