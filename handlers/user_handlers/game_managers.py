import asyncio
from aiogram import Bot
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import default_state
from aiogram.fsm.storage.base import StateType, StorageKey
from lexicon.lexicon_ru import LEXICON, LEXICON_MOVES
from keyboards.keyboards import create_inline_kb
from states.states import FSMPlay
from utils.enums import PlayerCode
from typing import TypeAlias


class GameSession:

    # Уникальный идентификатор сессии (tuple из двух id)
    SessionId: TypeAlias = tuple[int, int]

    # Хранилище сеансов по уникальному идентификатору (tuple из двух id)
    sessions: dict[SessionId, 'GameSession'] = {}

    def __init__(self, session_id: SessionId):
        self.session_id = session_id
        self.lock = asyncio.Lock()  # Блокировка для атомарных операций
        self.__class__.sessions[session_id] = self

    async def delete(self) -> None:
        del self.__class__.sessions[self.session_id]

    @staticmethod
    def generate_session_id(user_id: int, opponent_id: int) -> SessionId:
        # Убедимся, что идентификатор будет одинаков для обеих сторон
        ids = sorted((user_id, opponent_id))
        return (ids[0], ids[1])


class GameMaster:
    def __init__(self,
                 callback: CallbackQuery,
                 context: FSMContext,
                 opponent_id: int):
        self.callback: CallbackQuery = callback
        self.message: Message = callback.message  # type: ignore[assignment]
        self.bot: Bot = self.message.bot  # type: ignore[assignment]
        self.user_context: FSMContext = context
        self.user_id: int = self._get_user_id()
        self.opponent_id: int = opponent_id
        self.opponent_context: FSMContext = self._get_context(opponent_id)

        self.session_id = GameSession.generate_session_id(self.user_id,
                                                          self.opponent_id)
        # Получаем или создаем игровую сессию
        if session := GameSession.sessions.get(self.session_id):
            self.session = session
        else:  # Если сессии нет, создаем новую сессию
            self.session = GameSession(session_id=self.session_id)

    def _get_user_id(self) -> int:
        return self.callback.from_user.id

    def _get_context(self, user_id: int) -> FSMContext:
        user_key = StorageKey(
            bot_id=self.bot.id,
            chat_id=user_id,
            user_id=user_id
        )
        return FSMContext(storage=self.user_context.storage, key=user_key)

    async def send_message(self, chat_id: int, *args, **kwargs) -> None:
        await self.bot.send_message(chat_id, *args, **kwargs)

    async def answer_user(self, *args, **kwargs) -> None:
        await self.message.answer(*args, **kwargs)

    async def answer_opponent(self, *args, **kwargs) -> None:
        await self.send_message(self.opponent_id, *args, **kwargs)

    async def _update_date(self, context: FSMContext, **kwargs) -> None:
        await context.update_data(**kwargs)

    async def update_date_user(self, **kwargs) -> None:
        await self._update_date(self.user_context, **kwargs)

    async def update_date_opponent(self, **kwargs) -> None:
        await self._update_date(self.opponent_context, **kwargs)

    async def _get_data(self, context: FSMContext) -> dict:
        return await context.get_data()

    async def get_data_user(self) -> dict:
        return await self._get_data(self.user_context)

    async def get_data_opponent(self) -> dict:
        return await self._get_data(self.opponent_context)

    async def _set_state(self, context: FSMContext,
                         state_type: StateType) -> None:
        await context.set_state(state_type)

    async def set_state_user(self, state_type: StateType) -> None:
        await self._set_state(self.user_context, state_type)

    async def set_state_opponent(self, state_type: StateType) -> None:
        await self._set_state(self.opponent_context, state_type)

    async def _get_state(self, context: FSMContext) -> StateType:
        return await context.get_state()

    async def get_state_user(self) -> StateType:
        return await self._get_state(self.user_context)

    async def get_state_opponent(self) -> StateType:
        return await self._get_state(self.opponent_context)

    async def announce_winner(self, winner_id: int) -> None:
        await self.send_message(winner_id, LEXICON['you_win'])
        winner_context = self._get_context(winner_id)
        winner_data = await self._get_data(winner_context)
        winner_opponent_id = winner_data.get('opponent_id')
        if winner_opponent_id:
            await self.send_message(winner_opponent_id, LEXICON['you_lose'])
        await self._set_state(context=winner_context,
                              state_type=FSMPlay.winner)

    async def show_players_hands(self) -> None:
        user_data = await self.get_data_user()
        opponent_data = await self.get_data_opponent()
        await self.answer_user(
            LEXICON['your_hands'].format(
                hand1=LEXICON[user_data['first_hand']],
                hand2=LEXICON[user_data['second_hand']]
            )
        )
        await self.answer_user(
            LEXICON['opponent_hands'].format(
                hand1=LEXICON[opponent_data['first_hand']],
                hand2=LEXICON[opponent_data['second_hand']]
            )
        )

    async def wait_for_hands_completion(self, timeout: int = 10,
                                        check_interval: float = 0.5
                                        ) -> PlayerCode:
        """
        Ожидает, пока оба игрока выберут два хода (first_hand и second_hand)
        в течение timeout секунд. Если оба выбрали – возвращает BOTH.
        Если только один – возвращает USER или OPPONENT того, кто успел.
        """
        start_time = asyncio.get_event_loop().time()
        while True:
            user_state = await self.get_state_user()
            opp_state = await self.get_state_opponent()

            user_complete = (user_state == FSMPlay.both_hands_ready)
            opp_complete = (opp_state == FSMPlay.both_hands_ready)

            if user_complete and opp_complete:
                return PlayerCode.BOTH
            elapsed = asyncio.get_event_loop().time() - start_time
            if elapsed >= timeout:
                if user_complete and not opp_complete:
                    return PlayerCode.USER
                elif opp_complete and not user_complete:
                    return PlayerCode.OPPONENT
                else:
                    return PlayerCode.NOBODY
            await asyncio.sleep(check_interval)

    async def run_delayed_start_hand_choice_round_task(
            self, timeout: int = 10,
            check_interval: float = 0.1) -> None:
        players_ready = await self.wait_for_hands_completion(timeout,
                                                             check_interval)
        match players_ready:
            case PlayerCode.BOTH:  # Оба игрока выбрали обе руки вовремя
                await self.show_players_hands()
                await self.start_hand_choice_round()
            case PlayerCode.USER:  # Пользователь успел, а соперник не нет
                await self.announce_winner(winner_id=self.user_id)
            case PlayerCode.OPPONENT:  # Соперник успел, а пользователь нет
                await self.announce_winner(winner_id=self.opponent_id)
            case PlayerCode.NOBODY:  # Никто не успел — игра отменяется
                await self.answer_user(LEXICON['both_are_too_long'])
                await self.finish_game()

    async def start_first_hand_round(self) -> None:
        # Создаем клавиатуру для выбора действия у первой руки
        game_kb = create_inline_kb(*LEXICON_MOVES.keys())
        await self.answer_user(LEXICON['invitation_choose_action'],
                               reply_markup=game_kb)
        await self.set_state_user(FSMPlay.choice_action_for_first_hand)

    async def start_second_hand_round(self) -> None:
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

    async def process_first_hand(self) -> None:
        '''Обработка хода первой руки'''
        first_hand: str = str(self.callback.data)
        await self.update_date_user(first_hand=first_hand)

    async def process_second_hand(self) -> None:
        '''Обработка хода второй руки'''
        second_hand: str = str(self.callback.data)
        await self.update_date_user(second_hand=second_hand)
        await self.set_state_user(FSMPlay.both_hands_ready)

    async def clear_states(self) -> None:
        '''Очистка состояний игроков'''
        await self.user_context.clear()
        await self.opponent_context.clear()

    async def finish_game(self) -> None:
        """Завершает игру атомарно"""
        print('--- Start finish_game ---')
        print(f'--- GameMaster session: {self.session} ---')
        print(f'--- GameMaster session_id: {self.session_id} ---')
        print(f'--- GameSession sessions: {GameSession.sessions} ---')
        print(f'--- GameMaster session.lock: {self.session.lock} ---')
        async with self.session.lock:
            print('--- Lock acquired ---')
            # Проверяем, что игра еще не была завершена
            if self.session_id not in GameSession.sessions:
                print('--- Game already finished ---')
                return  # Значит игра уже была завершена оппонентом

            # Завершаем игру для обоих игроков (т.к. она еще не завершена)
            await self.answer_opponent(LEXICON['game_cancelled'])
            await self.answer_user(LEXICON['game_cancelled'])
            await self.clear_states()
            await self.session.delete()
            print('--- Game finished ---')

    async def react_to_cancellation(self, who_cancelled: PlayerCode) -> None:
        '''Реакция на отмену игры'''
        match who_cancelled:
            case PlayerCode.OPPONENT:
                await self.answer_user(LEXICON['opponent_cancelled_game'])
            case PlayerCode.USER:
                await self.answer_opponent(LEXICON['opponent_cancelled_game'])
        await self.finish_game()

    async def react_to_timeout(self, who_timeout: PlayerCode) -> None:
        '''Реакция на таймаут'''
        if who_timeout == PlayerCode.OPPONENT:
            await self.answer_user(LEXICON['too_long_waiting_response'])
            await self.answer_opponent(LEXICON['you_are_too_long'])
        elif who_timeout == PlayerCode.USER:
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

    @staticmethod
    async def get_opponent_id(callback: CallbackQuery,
                              context: FSMContext) -> int:
        message: Message = callback.message  # type: ignore[assignment]
        user_data = await context.get_data()

        try:
            opponent_id: int = user_data['opponent_id']
            return opponent_id
        except KeyError:
            await message.answer(text=LEXICON['opponent_not_found'])
            await context.clear()
            raise KeyError
