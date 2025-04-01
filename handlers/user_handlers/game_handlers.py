import asyncio
from encodings.punycode import T
from sqlite3 import connect
from aiogram import F, Router
from aiogram.types import Message, CallbackQuery
from keyboards.keyboards import yes_no_kb
from lexicon.lexicon_ru import LEXICON, LEXICON_MOVES
from services.services import get_bot_choice, get_winner
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from states.states import FSMPlay
from .game_utils.handlers_utils import (
    get_opponent_id, ConnectionManager
)


router = Router()


@router.callback_query(F.data == 'start_game',
                       StateFilter(FSMPlay.waiting_game_start))
async def process_start_game(callback: CallbackQuery, state: FSMContext):
    try:
        opponent_id = await get_opponent_id(callback, state)
    except KeyError:
        return  # Если соперник не найден, выходим из функции

    connection_manager = ConnectionManager(callback, state, opponent_id,
                                           await state.get_data())

    await connection_manager.update_date_user(ready_to_play=True)

    try:  # Запускаем задачу на ожидание согласия соперника (с таймаутом)
        await connection_manager.run_waiting_opponent_consent_task(timeout=10)
        # Соперник согласился на игру, запускаем первый раунд игры
        await connection_manager.launch_first_hand_round()
    except asyncio.CancelledError:  # Соперник отменил игру
        await connection_manager.react_to_opponent_cancellation()
    except asyncio.TimeoutError:  # Слишком долго ждем ответа от соперника
        await connection_manager.react_to_opponent_timeout()


@router.callback_query(F.data == 'refuse',
                       StateFilter(FSMPlay.waiting_game_start))
async def process_refuse_game(callback: CallbackQuery, state: FSMContext):
    try:
        opponent_id = await get_opponent_id(callback, state)
    except KeyError:
        return  # Если соперник не найден, выходим из функции

    connection_manager = ConnectionManager(callback, state, opponent_id,
                                           await state.get_data())
    await connection_manager.clear_states()  # Очищаем состояния игроков
    await connection_manager.send_game_end()  # Сообщаем им об отмене игры


@router.callback_query(F.data.in_(LEXICON_MOVES.keys()),
                       StateFilter(FSMPlay.choice_action_for_first_hand))
async def process_first_hand(callback: CallbackQuery, state: FSMContext):
    try:
        opponent_id = await get_opponent_id(callback, state)
    except KeyError:
        return  # Если соперник не найден, выходим из функции

    connection_manager = ConnectionManager(callback, state, opponent_id,
                                           await state.get_data())

    await connection_manager.first_hand(callback)  # Обработка первого хода


@router.callback_query(F.data.in_(LEXICON_MOVES.keys()),
                       StateFilter(FSMPlay.choice_action_for_second_hand))
async def process_second_hand(callback: CallbackQuery, state: FSMContext):
    try:
        opponent_id = await get_opponent_id(callback, state)
    except KeyError:
        return  # Если соперник не найден, выходим из функции

    connection_manager = ConnectionManager(callback, state, opponent_id,
                                           await state.get_data())

    await connection_manager.second_hand(callback)  # Обработка второго хода


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
