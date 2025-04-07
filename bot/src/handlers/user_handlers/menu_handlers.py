from aiogram import F, Router, Bot
from aiogram.filters import Command, CommandStart
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command, CommandStart, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.base import StorageKey
from src.keyboards.keyboards import yes_no_kb, create_inline_kb
from src.lexicon.lexicon_ru import LEXICON
from src.services.services import get_random_online_user
from src.states.states import FSMMenu, FSMPlay


router = Router()


# Этот хэндлер срабатывает на команду /start
@router.message(CommandStart())
async def process_start_command(message: Message, state: FSMContext):
    await message.answer(text=LEXICON['/start'], reply_markup=yes_no_kb)
    await state.clear()
    await state.set_state(FSMMenu.game_consent)


# Этот хэндлер срабатывает на команду /help
@router.message(Command(commands='help'))
async def process_help_command(message: Message, state: FSMContext):
    await message.answer(text=LEXICON['/help'], reply_markup=yes_no_kb)
    await state.set_state(FSMMenu.game_consent)


# Этот хэндлер срабатывает на согласие пользователя играть в игру
@router.message(F.text == LEXICON['yes_button'],
                StateFilter(FSMMenu.game_consent))
async def process_game_mode(message: Message, state: FSMContext):
    choice_game_mode_kb = create_inline_kb('quick_game', 'tournir')
    await message.answer(text=LEXICON['choice_game_mode'],
                         reply_markup=choice_game_mode_kb)
    await state.set_state(FSMMenu.choice_game_mode)


# Этот хэндлер срабатывает на отказ пользователя играть в игру
@router.message(F.text == LEXICON['no_button'],
                StateFilter(FSMMenu.game_consent))
async def process_no_answer(message: Message, state: FSMContext):
    await message.answer(text=LEXICON['refused_to_play'])
    await state.clear()


@router.callback_query(F.data == 'quick_game',
                       StateFilter(FSMMenu.choice_game_mode))
async def process_quick_game(callback: CallbackQuery, state: FSMContext):
    message: Message = callback.message  # type: ignore[assignment]
    choice_user_search_kb = create_inline_kb('matchmaking')
    await message.answer(text=LEXICON['choice_user_search'],
                         reply_markup=choice_user_search_kb)
    await state.set_state(FSMMenu.quick_game)


@router.callback_query(F.data == 'matchmaking',
                       StateFilter(FSMMenu.quick_game))
async def process_matchmaking(callback: CallbackQuery, state: FSMContext):
    message: Message = callback.message  # type: ignore[assignment]
    user_id: int = callback.from_user.id  # type: ignore[assignment]
    bot: Bot = message.bot  # type: ignore[assignment]
    storage = state.storage

    try:
        opponent_id = get_random_online_user(except_user_id=user_id)
    except IndexError:
        await message.answer(text=LEXICON['no_online_users'])
        await state.clear()
        return

    # Создаем корректный ключ состояния
    opponent_key = StorageKey(
        bot_id=bot.id,
        chat_id=opponent_id,
        user_id=opponent_id
    )

    # Создаем контекст состояния для соперника
    opponent_state = FSMContext(storage=storage, key=opponent_key)

    # Устанавливаем сопернику новое состояние
    await opponent_state.set_state(FSMPlay.waiting_game_start)

    # Устанавливаем новое состояние для текущего пользователя
    await state.set_state(FSMPlay.waiting_game_start)

    waiting_game_start_kb = create_inline_kb('start_game', 'refuse')

    # Отправляем сообщение сопернику о том, что его выбрали для игры
    await bot.send_message(
        chat_id=opponent_id,
        text=LEXICON['you_are_chosen'].format(user_id=user_id),
        reply_markup=waiting_game_start_kb
    )

    # Отправляем сообщение пользователю о его сопернике
    await message.answer(
        text=LEXICON['your_opponent'].format(opponent_id=opponent_id),
        reply_markup=waiting_game_start_kb,
        parse_mode='HTML'
    )

    await state.update_data(opponent_id=opponent_id)
    await opponent_state.update_data(opponent_id=user_id)
