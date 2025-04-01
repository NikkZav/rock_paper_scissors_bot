import asyncio
import time
from aiogram import F, Router, Bot
from aiogram.filters import Command, CommandStart
from aiogram.types import Message, CallbackQuery
from keyboards.keyboards import yes_no_kb, create_inline_kb
from lexicon.lexicon_ru import LEXICON, LEXICON_MOVES
from services.services import (get_bot_choice, get_winner,
                               get_random_online_user)
from aiogram.filters import Command, CommandStart, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import default_state
from aiogram.fsm.storage.base import StorageKey
from states.states import FSMMenu, FSMPlay
from aiogram.exceptions import TelegramBadRequest


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


@router.callback_query(F.data == 'start_game',
                       StateFilter(FSMPlay.waiting_game_start))
async def process_start_game(callback: CallbackQuery, state: FSMContext):
    message: Message = callback.message  # type: ignore[assignment]
    bot: Bot = message.bot  # type: ignore[assignment]
    user_data = await state.get_data()

    try:
        opponent_id: int = user_data['opponent_id']
    except KeyError:
        await message.answer(text=LEXICON['opponent_not_found'])
        await state.clear()
        return

    await state.update_data(ready_to_play=True)

    # Получаем состояние соперника
    opponent_key = StorageKey(
        bot_id=bot.id,
        chat_id=opponent_id,
        user_id=opponent_id
    )
    opponent_state = FSMContext(storage=state.storage, key=opponent_key)

    async def wait_opponent_consent() -> None:
        """Ожидание ответа соперника с обновлениями статуса"""
        while True:
            opponent_data = await opponent_state.get_data()
            decision: bool | None = opponent_data.get('ready_to_play')

            # Проверяем не отменил ли соперник игру
            if decision is False or 'opponent_id' not in opponent_data:
                raise asyncio.CancelledError  # Вызываем отмену задачи

            if decision is True:  # Если соперник готов к игре
                return  # Выходим из функции и завершаем задачу

            await message.answer(LEXICON['waiting_opponent'])
            await asyncio.sleep(2)

    # Создаем задачу
    wait_opponent_consent_task = asyncio.create_task(wait_opponent_consent())

    # Запускаем задачу с таймаутом
    try:
        await asyncio.wait_for(wait_opponent_consent_task, timeout=10)
        # Оба игрока готовы
        await message.answer(LEXICON['opponent_ready_to_play'])

        # Запускаем игру
        game_kb = create_inline_kb(*LEXICON_MOVES.keys())
        await message.answer(LEXICON['invitation_choose_action'],
                             reply_markup=game_kb)
        await state.set_state(FSMPlay.choice_action_for_first_hand)
        await opponent_state.set_state(FSMPlay.choice_action_for_first_hand)
        return  # Выходим из функции

    except asyncio.CancelledError:
        # Соперник отменил игру
        await message.answer(LEXICON['game_cancelled'])
    except asyncio.TimeoutError:
        await message.answer(LEXICON['too_long_waiting_response'])
        await bot.send_message(  # Уведомляем соперника об отмене
            chat_id=opponent_id,
            text=LEXICON['game_cancelled']
        )
    # Очищаем состояния игроков
    await state.clear()
    await opponent_state.clear()


@router.callback_query(F.data == 'refuse',
                       StateFilter(FSMPlay.waiting_game_start))
async def process_refuse_game(callback: CallbackQuery, state: FSMContext):
    message: Message = callback.message  # type: ignore[assignment]
    bot: Bot = message.bot  # type: ignore[assignment]
    user_data = await state.get_data()

    try:
        opponent_id: int = user_data['opponent_id']
    except KeyError:
        await message.answer(text=LEXICON['opponent_not_found'])
        await state.clear()
        return

    # Очищаем состояние текущего пользователя
    await state.clear()

    # Очищаем состояние соперника
    opponent_key = StorageKey(
        bot_id=bot.id,
        chat_id=opponent_id,
        user_id=opponent_id
    )
    opponent_state = FSMContext(storage=state.storage, key=opponent_key)
    await opponent_state.clear()

    # Уведомляем обоих игроков
    await bot.send_message(
        chat_id=opponent_id,
        text=LEXICON['opponent_refused']
    )
    await message.answer(LEXICON['game_cancelled'])


@router.callback_query(F.data.in_(LEXICON_MOVES.keys()),
                       StateFilter(FSMPlay.choice_action_for_first_hand))
async def process_first_hand(callback: CallbackQuery, state: FSMContext):
    message: Message = callback.message  # type: ignore[assignment]
    action_for_first_hand: str = callback.data  # type: ignore[assignment]

    await state.update_data(action_for_first_hand=action_for_first_hand)
    await message.answer(text=f'{LEXICON['user_choice']} '
                              f'- {LEXICON[action_for_first_hand]}')

    await state.set_state(FSMPlay.choice_action_for_second_hand)


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
