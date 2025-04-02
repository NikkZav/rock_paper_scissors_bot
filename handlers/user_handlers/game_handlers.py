import asyncio
from aiogram import F, Router
from aiogram.types import Message, CallbackQuery
from keyboards.keyboards import yes_no_kb
from lexicon.lexicon_ru import LEXICON, LEXICON_MOVES
from services.services import get_bot_choice, get_winner
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from states.states import FSMPlay
from .game_managers import GameMaster, get_opponent_id


router = Router()


@router.callback_query(F.data == "start_game",
                       StateFilter(FSMPlay.waiting_game_start))
async def process_start_game(callback: CallbackQuery, state: FSMContext):
    try:
        opponent_id = await get_opponent_id(callback, state)
    except KeyError:
        return  # Если соперник не найден, выходим из функции

    game_master = GameMaster(callback, state, opponent_id)

    await game_master.update_date_user(ready_to_play=True)

    try:  # Запускаем задачу на ожидание согласия соперника (с таймаутом)
        await game_master.run_waiting_opponent_consent_task(timeout=10)
        # Соперник согласился на игру, запускаем первый раунд игры
        await game_master.start_first_hand_round()
    except asyncio.CancelledError:  # Соперник отменил игру
        pass  # Ничего не делаем, так как игра уже завершена противником
    except asyncio.TimeoutError:  # Слишком долго ждем ответа от соперника
        await game_master.react_to_timeout(who_timeout="opponent")


@router.callback_query(F.data == "refuse",
                       StateFilter(FSMPlay.waiting_game_start))
async def process_refuse_game(callback: CallbackQuery, state: FSMContext):
    try:
        opponent_id = await get_opponent_id(callback, state)
    except KeyError:
        return  # Если соперник не найден, выходим из функции

    game_master = GameMaster(callback, state, opponent_id)
    # Пользователь отказался от игры
    await game_master.react_to_cancellation(who_cancelled="user")


@router.callback_query(F.data.in_(LEXICON_MOVES.keys()),
                       StateFilter(FSMPlay.choice_action_for_first_hand))
async def process_first_hand(callback: CallbackQuery, state: FSMContext):
    try:
        opponent_id = await get_opponent_id(callback, state)
    except KeyError:
        return  # Если соперник не найден, выходим из функции

    game_master = GameMaster(callback, state, opponent_id)
    # Обработка первого хода
    await game_master.process_first_hand(callback)
    # Запускаем второй раунд (выбор действия у второй руки)
    await game_master.start_second_hand_round()


@router.callback_query(F.data.in_(LEXICON_MOVES.keys()),
                       StateFilter(FSMPlay.choice_action_for_second_hand))
async def process_second_hand(callback: CallbackQuery, state: FSMContext):
    try:
        opponent_id = await get_opponent_id(callback, state)
    except KeyError:
        return  # Если соперник не найден, выходим из функции

    game_master = GameMaster(callback, state, opponent_id)
    # Обработка второго хода
    await game_master.process_second_hand(callback)

    # А третий раунд запускается только после того,
    # как оба игрока сделают ходы (либо конец игры с выводом победителя)
    # Вся логика таймера в .game_managers: GameMaster.wait_for_hands_completion


# # Этот хэндлер срабатывает на любую из игровых кнопок
# @router.callback_query(F.data.in_(LEXICON_MOVES.keys()))
# async def process_game_button(callback: CallbackQuery):
#     message: Message = callback.message  # type: ignore[assignment]
#     user_choice: str = callback.data  # type: ignore[assignment]

#     bot_choice = get_bot_choice()
#     await message.answer(text=f'{LEXICON["user_choice"]} '
#                               f'- {LEXICON[user_choice]}')
#     await message.answer(text=f'{LEXICON["bot_choice"]} '
#                               f'- {LEXICON[bot_choice]}')
#     winner = get_winner(user_choice, bot_choice)  # type: ignore[arg-type]
#     await message.answer(text=LEXICON[winner], reply_markup=yes_no_kb)
