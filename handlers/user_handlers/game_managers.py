import asyncio
from time import sleep
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
        self.opponent_state = self._get_state(opponent_id)

    def _get_state(self, user_id: int) -> FSMContext:
        user_key = StorageKey(
            bot_id=self.bot.id,
            chat_id=user_id,
            user_id=user_id
        )
        return FSMContext(storage=self.state.storage, key=user_key)

    async def send_message(self, chat_id: int, *args, **kwargs) -> None:
        await self.bot.send_message(chat_id, *args, **kwargs)

    async def answer_user(self, *args, **kwargs) -> None:
        await self.message.answer(*args, **kwargs)

    async def answer_opponent(self, *args, **kwargs) -> None:
        await self.send_message(self.opponent_id, *args, **kwargs)

    async def _update_date(self, state: FSMContext, **kwargs) -> None:
        await state.update_data(**kwargs)

    async def update_date_user(self, **kwargs) -> None:
        await self._update_date(self.state, **kwargs)

    async def update_date_opponent(self, **kwargs) -> None:
        await self._update_date(self.opponent_state, **kwargs)

    async def _get_data(self, state: FSMContext) -> dict:
        return await state.get_data()

    async def get_data_user(self) -> dict:
        return await self._get_data(self.state)

    async def get_data_opponent(self) -> dict:
        return await self._get_data(self.opponent_state)

    async def _set_state(self, state: FSMContext,
                         state_type: StateType) -> None:
        await state.set_state(state_type)

    async def set_state_user(self, state: StateType) -> None:
        await self._set_state(self.state, state)

    async def set_state_opponent(self, state: StateType) -> None:
        await self._set_state(self.opponent_state, state)

    async def announce_winner(self, winner_id: int) -> None:
        await self.send_message(winner_id, LEXICON['you_win'])
        winner_state = self._get_state(winner_id)
        winner_data = await self._get_data(winner_state)
        winner_opponent_id = winner_data.get('opponent_id')
        if winner_opponent_id:
            await self.send_message(winner_opponent_id, LEXICON['you_lose'])
        await self._set_state(winner_state, FSMPlay.winner)

    async def wait_for_hands_completion(self, timeout: int = 10,
                                        check_interval: float = 0.5
                                        ) -> str | None:
        """
        Ожидает, пока оба игрока выберут два хода (first_hand и second_hand)
        в течение timeout секунд. Если оба выбрали – возвращает "both".
        Если только один – возвращает "user" или "opponent" того, кто успел.
        """
        start_time = asyncio.get_event_loop().time()
        while True:
            user_data = await self.get_data_user()
            opp_data = await self.get_data_opponent()

            user_complete = ('first_hand' in user_data and
                             'second_hand' in user_data)
            opp_complete = ('first_hand' in opp_data and
                            'second_hand' in opp_data)

            if user_complete and opp_complete:
                return "both"
            elapsed = asyncio.get_event_loop().time() - start_time
            if elapsed >= timeout:
                if user_complete and not opp_complete:
                    return "user"
                elif opp_complete and not user_complete:
                    return "opponent"
                else:
                    return None
            await asyncio.sleep(check_interval)

    async def start_first_hand_round(self) -> None:
        # Оба игрока готовы
        await self.answer_user(LEXICON['opponent_ready_to_play'])

        # Создаем клавиатуру для выбора действия у первой руки
        game_kb = create_inline_kb(*LEXICON_MOVES.keys())
        await self.answer_user(LEXICON['invitation_choose_action'],
                               reply_markup=game_kb)
        await self.set_state_user(FSMPlay.choice_action_for_first_hand)

        # Запускаем таймер на N(=10) секунд, по оконачнию которого
        # выиграет тот игрок, который выбрал обе руки, если другой ещё не успел
        # Если оба игрока выбрали обе руки в течение N секунд,
        # то таймер отменяется и игра продолжается

        # Запускаем таймер ожидания выбора обоих рук
        result = await self.wait_for_hands_completion(timeout=10,
                                                      check_interval=0.5)
        if result == "both":
            # Оба игрока выбрали два хода — переходим к следующему этапу игры
            # Например, запуск выбора оставшейся руки:
            await self.start_hand_choice_round()
        elif result == "user":
            if self.message.from_user:
                # Пользователь успел, а соперник не успел, а значит проиграл
                await self.announce_winner(winner_id=self.message.from_user.id)
        elif result == "opponent":
            # Соперник успел, а пользователь не успел — соперник выигрывает
            await self.announce_winner(winner_id=self.opponent_id)
        else:
            # Ни один не завершил выбор вовремя — игра отменяется
            await self.finish_game()

    async def start_second_hand_round(self) -> None:
        # Оба игрока готовы
        await self.answer_user(LEXICON['opponent_ready_to_play'])

        # Создаем клавиатуру для выбора действия у второй руки
        game_kb = create_inline_kb(*LEXICON_MOVES.keys())
        await self.answer_user(LEXICON['invitation_choose_action'],
                               reply_markup=game_kb)

        await self.set_state_user(FSMPlay.choice_action_for_second_hand)

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

    async def finish_game(self) -> None:
        '''Завершение игры'''
        await self.answer_opponent(LEXICON['game_cancelled'])
        await self.answer_user(LEXICON['game_cancelled'])
        await self.clear_states()

    async def react_to_cancellation(self, who_cancelled: str) -> None:
        '''Реакция на отмену игры'''
        if who_cancelled == 'opponent':
            await self.answer_user(LEXICON['opponent_cancelled_game'])
        elif who_cancelled == 'user':
            await self.answer_opponent(LEXICON['opponent_cancelled_game'])
        await self.finish_game()

    async def react_to_timeout(self, who_timeout: str) -> None:
        '''Реакция на таймаут'''
        if who_timeout == 'opponent':
            await self.answer_user(LEXICON['too_long_waiting_response'])
            await self.answer_opponent(LEXICON['you_are_too_long'])
        elif who_timeout == 'user':
            await self.answer_opponent(LEXICON['too_long_waiting_response'])
            await self.answer_user(LEXICON['you_are_too_long'])
        await self.finish_game()

    async def wait_opponent_consent(self, send_every_n_seconds: int = 2,
                                    update_frequency: int = 10) -> None:
        """Ожидание ответа соперника с обновлениями статуса"""
        steps: int = 0
        sleep_time = 1 / update_frequency
        while True:
            opponent_data = await self.get_data_opponent()
            decision: bool | None = opponent_data.get('ready_to_play')

            # Проверяем не отменил ли соперник игру
            if decision is False or 'opponent_id' not in opponent_data:
                raise asyncio.CancelledError  # Вызываем отмену задачи

            if decision is True:  # Если соперник готов к игре
                return  # Выходим из функции и завершаем задачу

            if steps % (send_every_n_seconds * update_frequency) == 0:
                await self.message.answer(LEXICON['waiting_opponent'])
            await asyncio.sleep(sleep_time)
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
