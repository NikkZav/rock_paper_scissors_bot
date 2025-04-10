import asyncio
from aiogram import F, Router
from aiogram.types import CallbackQuery
from lexicon.lexicon_ru import LEXICON, LEXICON_MOVES
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from states.states import FSMPlay
from .game_managers import GameMaster
from utils.enums import PlayerCode


router = Router()


@router.callback_query(F.data == "start_game",
                       StateFilter(FSMPlay.waiting_game_start))
async def process_start_game(callback: CallbackQuery, state: FSMContext):
    try:
        opponent_id = await GameMaster.get_opponent_id(callback, state)
    except KeyError:
        return  # Если соперник не найден, выходим из функции

    game_master = GameMaster(callback, state, opponent_id)

    # Обновляем данные пользователя о готовности к игре
    await game_master.update_date(whom=PlayerCode.USER, ready_to_play=True)

    # Если задача на ожидание согласия соперника уже запущена соперником, то...
    if game_master.session.running_tasks.get('wait_opponent_consent_task'):
        await game_master.start_first_hand_round()  # Запускаем первый раунд
        return  # Выходим из функции, так как соперник уже запустил задачу

    try:  # Запускаем задачу на ожидание согласия соперника (с таймаутом)
        await game_master.run_waiting_opponent_consent_task(timeout=10)
    except asyncio.CancelledError:  # Соперник отменил игру
        pass  # Ничего не делаем, так как игра уже завершена противником
    except asyncio.TimeoutError:  # Слишком долго ждем ответа от соперника
        await game_master.react_to_timeout(who_timeout=PlayerCode.OPPONENT)
    else:  # Соперник согласился на игру, запускаем первый раунд игры
        await game_master.start_first_hand_round()
        # Паралелльно запускаем задачу ожидающую выбора обеих рук (с таймаутом)
        # Если игрок не успевает сделать выбор, то он проигрывает раунд
        # Если оба игрока сделали выбор, то запускаем раунд выбора руки
        await game_master.run_delayed_start_hand_choice_round_task(timeout=10)
    finally:  # Убиваем задачу ожидания согласия соперника, если она не умерла
        game_master.session.kill_task('wait_opponent_consent_task')


@router.callback_query(F.data == "refuse",
                       StateFilter(FSMPlay.waiting_game_start))
async def process_refuse_game(callback: CallbackQuery, state: FSMContext):
    try:
        opponent_id = await GameMaster.get_opponent_id(callback, state)
    except KeyError:
        return  # Если соперник не найден, выходим из функции

    game_master = GameMaster(callback, state, opponent_id)
    # Пользователь отказался от игры
    await game_master.react_to_cancellation(who_cancelled=PlayerCode.USER)


@router.callback_query(F.data.in_(LEXICON_MOVES.keys()),
                       StateFilter(FSMPlay.choice_action_for_first_hand))
async def process_first_hand(callback: CallbackQuery, state: FSMContext):
    try:
        opponent_id = await GameMaster.get_opponent_id(callback, state)
    except KeyError:
        return  # Если соперник не найден, выходим из функции

    game_master = GameMaster(callback, state, opponent_id)
    # Обработка первого хода
    await game_master.process_first_hand()
    # Запускаем второй раунд (выбор действия у второй руки)
    await game_master.start_second_hand_round()


@router.callback_query(F.data.in_(LEXICON_MOVES.keys()),
                       StateFilter(FSMPlay.choice_action_for_second_hand))
async def process_second_hand(callback: CallbackQuery, state: FSMContext):
    try:
        opponent_id = await GameMaster.get_opponent_id(callback, state)
    except KeyError:
        return  # Если соперник не найден, выходим из функции

    game_master = GameMaster(callback, state, opponent_id)
    # Обработка второго хода
    await game_master.process_second_hand()

    # А третий раунд запускается автоматически только после того,
    # как оба игрока сделают ходы (либо конец игры с выводом победителя)
    # Вся логика таймера в .game_managers: GameMaster.wait_for_hands_completion


# @router.callback_query(F.data.in_('first_hand', 'second_hand'),
#                        StateFilter(FSMPlay.choice_hand))
# async def process_hand_choice(callback: CallbackQuery, state: FSMContext):
#     try:
#         opponent_id = await GameMaster.get_opponent_id(callback, state)
#     except KeyError:
#         return  # Если соперник не найден, выходим из функции

#     game_master = GameMaster(callback, state, opponent_id)



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
