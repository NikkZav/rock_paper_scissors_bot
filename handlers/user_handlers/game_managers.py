import asyncio
from aiogram import Bot
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.base import StateType, StorageKey
from lexicon.lexicon_ru import LEXICON, LEXICON_MOVES
from keyboards.keyboards import create_inline_kb
from states.states import FSMPlay


class GameMaster:
    def __init__(self,
                 callback: CallbackQuery,
                 state: FSMContext,
                 opponent_id: int):
        self.message: Message = callback.message  # type: ignore[assignment]
        self.bot: Bot = self.message.bot  # type: ignore[assignment]
        self.state: FSMContext = state
        self.opponent_id: int = opponent_id
        self.opponent_key = StorageKey(
            bot_id=self.bot.id,
            chat_id=opponent_id,
            user_id=opponent_id
        )
        self.opponent_state = FSMContext(storage=state.storage,
                                         key=self.opponent_key)

    async def answer_user(self, *args, **kwargs) -> None:
        await self.message.answer(*args, **kwargs)

    async def answer_opponent(self, *args, **kwargs) -> None:
        await self.bot.send_message(self.opponent_id, *args, **kwargs)

    async def update_date_user(self, **kwargs) -> None:
        await self.state.update_data(**kwargs)

    async def update_date_opponent(self, **kwargs) -> None:
        await self.opponent_state.update_data(**kwargs)

    async def set_state_user(self, state: StateType) -> None:
        await self.state.set_state(state)

    async def set_state_opponent(self, state: StateType) -> None:
        await self.opponent_state.set_state(state)

    async def start_first_hand_round(self) -> None:
        # Оба игрока готовы
        await self.answer_user(LEXICON['opponent_ready_to_play'])

        # Создаем клавиатуру для выбора действия у первой руки
        game_kb = create_inline_kb(*LEXICON_MOVES.keys())
        await self.answer_user(LEXICON['invitation_choose_action'],
                               reply_markup=game_kb)
        await self.set_state_user(FSMPlay.choice_action_for_first_hand)
        await self.set_state_opponent(FSMPlay.choice_action_for_first_hand)

        # Запускаем таймер ожидания хода от соперника.
        # Если соперник не сделал ход в течение N секунд, то игра отменяется
        ...

    async def start_second_hand_round(self) -> None:
        # Оба игрока готовы
        await self.answer_user(LEXICON['opponent_ready_to_play'])

        # Создаем клавиатуру для выбора действия у второй руки
        game_kb = create_inline_kb(*LEXICON_MOVES.keys())
        await self.answer_user(LEXICON['invitation_choose_action'],
                               reply_markup=game_kb)

        await self.set_state_user(FSMPlay.choice_action_for_second_hand)
        await self.set_state_opponent(FSMPlay.choice_action_for_second_hand)

        # Запускаем таймер ожидания хода от соперника.
        # Если соперник не сделал ход в течение N секунд, то игра отменяется
        ...

    async def start_hand_choice_round(self) -> None:
        # Оба игрока готовы
        await self.answer_user(LEXICON['opponent_ready_to_play'])

        # Создаем клавиатуру для выбора оставшейся руки
        game_kb = create_inline_kb('first_hand', 'second_hand')
        await self.answer_user(LEXICON['invitation_choose_action'],
                               reply_markup=game_kb)
        await self.set_state_user(FSMPlay.choice_hand)
        await self.set_state_opponent(FSMPlay.choice_hand)

        # Запускаем таймер ожидания хода от соперника.
        # Если соперник не сделал ход в течение N секунд, то игра отменяется
        ...

    async def process_first_hand(self, callback: CallbackQuery) -> None:
        '''Обработка хода первой руки'''
        # Отпровляем сообщение сопернику о том, что игрок сделал ход
        await self.answer_opponent(LEXICON['opponent_made_move'])
        # Отправляем сообщение пользователю о том, что он сделал ход
        first_hand: str = str(callback.data)
        await self.update_date_user(first_hand=first_hand)
        await self.answer_user(text=f'{LEXICON['user_choice']} '
                                    f'- {LEXICON[first_hand]}')

    async def process_second_hand(self, callback: CallbackQuery) -> None:
        '''Обработка хода второй руки'''
        # Отпровляем сообщение сопернику о том, что игрок сделал ход
        await self.answer_opponent(LEXICON['opponent_made_move'])
        # Отправляем сообщение пользователю о том, что он сделал ход
        second_hand: str = str(callback.data)
        await self.update_date_user(second_hand=second_hand)
        await self.answer_user(text=f'{LEXICON['user_choice']} '
                                    f'- {LEXICON[second_hand]}')

    async def clear_states(self) -> None:
        '''Очистка состояний игроков'''
        await self.state.clear()
        await self.opponent_state.clear()

    async def react_to_opponent_cancellation(self) -> None:
        '''Реакция на отмену игры соперником'''
        await self.answer_user(LEXICON['game_cancelled'])
        await self.clear_states()

    async def react_to_opponent_timeout(self) -> None:
        '''Реакция на таймаут соперника'''
        await self.answer_user(LEXICON['too_long_waiting_response'])
        await self.answer_opponent(text=LEXICON['game_cancelled'])
        await self.clear_states()

    async def send_game_end(self) -> None:
        '''Уведомление об окончании игры'''
        await self.answer_opponent(text=LEXICON['opponent_refused'])
        await self.answer_user(LEXICON['game_cancelled'])

    async def wait_opponent_consent(self, send_every_n_seconds: int = 2,
                                    update_frequency: int = 10) -> None:
        """Ожидание ответа соперника с обновлениями статуса"""
        steps: int = 0
        while True:
            opponent_data = await self.opponent_state.get_data()
            decision: bool | None = opponent_data.get('ready_to_play')

            # Проверяем не отменил ли соперник игру
            if decision is False or 'opponent_id' not in opponent_data:
                raise asyncio.CancelledError  # Вызываем отмену задачи

            if decision is True:  # Если соперник готов к игре
                return  # Выходим из функции и завершаем задачу

            if steps % (send_every_n_seconds * update_frequency) == 0:
                await self.message.answer(LEXICON['waiting_opponent'])
            await asyncio.sleep(1 / update_frequency)
            steps += 1

    async def run_waiting_opponent_consent_task(self,
                                                timeout: int = 10) -> None:
        '''Запуск задачи на ожидание согласия соперника с таймаутом'''
        wait_opponent_consent_task = asyncio.create_task(
            self.wait_opponent_consent()
        )
        await asyncio.wait_for(wait_opponent_consent_task, timeout=timeout)


async def get_opponent_id(callback: CallbackQuery,
                          state: FSMContext) -> int:
    message: Message = callback.message  # type: ignore[assignment]
    user_data = await state.get_data()

    try:
        opponent_id: int = user_data['opponent_id']
        return opponent_id
    except KeyError:
        await message.answer(text=LEXICON['opponent_not_found'])
        await state.clear()
        raise KeyError
