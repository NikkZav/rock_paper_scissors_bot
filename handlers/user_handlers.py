from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.types import Message, CallbackQuery
from keyboards.keyboards import yes_no_kb, create_inline_kb
from lexicon.lexicon_ru import LEXICON, LEXICON_MOVES
from services.services import get_bot_choice, get_winner

router = Router()


# Этот хэндлер срабатывает на команду /start
@router.message(CommandStart())
async def process_start_command(message: Message):
    await message.answer(text=LEXICON['/start'], reply_markup=yes_no_kb)


# Этот хэндлер срабатывает на команду /help
@router.message(Command(commands='help'))
async def process_help_command(message: Message):
    await message.answer(text=LEXICON['/help'], reply_markup=yes_no_kb)


# Этот хэндлер срабатывает на согласие пользователя играть в игру
@router.message(F.text == LEXICON['yes_button'])
async def process_yes_answer(message: Message):
    game_kb = create_inline_kb('rock', 'paper', 'scissors')
    await message.answer(text=LEXICON['yes'], reply_markup=game_kb)


# Этот хэндлер срабатывает на отказ пользователя играть в игру
@router.message(F.text == LEXICON['no_button'])
async def process_no_answer(message: Message):
    await message.answer(text=LEXICON['no'])


# Этот хэндлер срабатывает на любую из игровых кнопок
@router.callback_query(F.data.in_(LEXICON_MOVES.keys()))
async def process_game_button(callback: CallbackQuery):
    message: Message = callback.message  # type: ignore[assignment]
    user_choice: str = callback.data  # type: ignore[assignment]

    bot_choice = get_bot_choice()
    await message.answer(text=f'{LEXICON["user_choice"]} '
                              f'- {LEXICON[user_choice]}')
    await message.answer(text=f'{LEXICON["bot_choice"]} '
                              f'- {LEXICON[bot_choice]}')
    winner = get_winner(user_choice, bot_choice)  # type: ignore[arg-type]
    await message.answer(text=LEXICON[winner], reply_markup=yes_no_kb)
