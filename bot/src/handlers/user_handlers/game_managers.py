import asyncio
from aiogram import Bot
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import default_state
from aiogram.fsm.storage.base import StateType, StorageKey
from typing import TypeAlias
from src.lexicon.lexicon_ru import LEXICON, LEXICON_MOVES
from src.keyboards.keyboards import create_inline_kb
from src.states.states import FSMPlay
from src.utils.enums import PlayerCode


class GameSession:

    # Уникальный идентификатор сессии (tuple из двух id)
    SessionId: TypeAlias = tuple[int, int]

    # Хранилище сеансов по уникальному идентификатору (tuple из двух id)
    sessions: dict[SessionId, 'GameSession'] = {}

    def __init__(self, session_id: SessionId):
        self.session_id = session_id
        self.lock = asyncio.Lock()  # Блокировка для атомарных операций
        self.__class__.sessions[session_id] = self
        self.running_tasks: dict[str, asyncio.Task] = {}

    def kill_task(self, task_name: str) -> None:
        if task := self.running_tasks.get(task_name):
            task.cancel()
            del self.running_tasks[task_name]

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

    async def send_message(self, chat_id: int, *args, **kwargs) -> Message:
        return await self.bot.send_message(chat_id, *args, **kwargs)

    async def answer(self, whom: PlayerCode, *args, **kwargs) -> int:
        match whom:
            case PlayerCode.USER:
                message = await self.message.answer(*args, **kwargs)
            case PlayerCode.OPPONENT:
                message = await self.send_message(
                    self.opponent_id, *args, **kwargs)
            case PlayerCode.BOTH:
                message = await self.message.answer(*args, **kwargs)
                message = await self.send_message(
                    self.opponent_id, *args, **kwargs)
        return message.message_id

    async def update_date(self, whom: PlayerCode, **kwargs) -> None:
        match whom:
            case PlayerCode.USER:
                await self.user_context.update_data(**kwargs)
            case PlayerCode.OPPONENT:
                await self.opponent_context.update_data(**kwargs)
            case PlayerCode.BOTH:
                await self.user_context.update_data(**kwargs)
                await self.opponent_context.update_data(**kwargs)

    async def get_data(self, whom: PlayerCode) -> dict:
        match whom:
            case PlayerCode.USER:
                return await self.user_context.get_data()
            case PlayerCode.OPPONENT:
                return await self.opponent_context.get_data()
            case _: return {}

    async def get_data_both(self) -> tuple[dict, dict]:
        return (await self.get_data(PlayerCode.USER),
                await self.get_data(PlayerCode.OPPONENT))

    async def set_state(self, whom: PlayerCode, state_type: StateType) -> None:
        match whom:
            case PlayerCode.USER:
                await self.user_context.set_state(state_type)
            case PlayerCode.OPPONENT:
                await self.opponent_context.set_state(state_type)
            case PlayerCode.BOTH:
                await self.user_context.set_state(state_type)
                await self.opponent_context.set_state(state_type)

    async def get_state(self, whom: PlayerCode) -> StateType:
        match whom:
            case PlayerCode.USER:
                return await self.user_context.get_state()
            case PlayerCode.OPPONENT:
                return await self.opponent_context.get_state()
            case _: return default_state

    async def get_state_both(self) -> tuple[StateType, StateType]:
        return (await self.get_state(PlayerCode.USER),
                await self.get_state(PlayerCode.OPPONENT))

    async def delete_message(self, whom: PlayerCode,
                             key: str = 'message_id') -> None:
        match whom:
            case PlayerCode.USER:
                whom_chat_id = ((PlayerCode.USER, self.user_id),)
            case PlayerCode.OPPONENT:
                whom_chat_id = ((PlayerCode.OPPONENT, self.opponent_id),)
            case PlayerCode.BOTH:
                whom_chat_id: tuple[tuple[PlayerCode, int], ...] = (
                    (PlayerCode.USER, self.user_id),
                    (PlayerCode.OPPONENT, self.opponent_id))
        # Удаляем сообщение
        for whom, chat_id in whom_chat_id:
            message_id = (
                await self.get_data(whom=whom)
            ).get(key)
            await self.bot.delete_message(
                chat_id=chat_id,
                message_id=message_id if type(message_id) is int else 0
            )
            await self.update_date(whom=whom, message_edited_id=None)

    async def announce_winner(self, winner_id: int) -> None:
        await self.send_message(winner_id, LEXICON['you_win'])
        winner_context = self._get_context(winner_id)
        winner_data = await winner_context.get_data()
        winner_opponent_id = winner_data.get('opponent_id')
        if winner_opponent_id:
            await self.send_message(winner_opponent_id, LEXICON['you_lose'])
        await winner_context.set_state(FSMPlay.winner)

    async def show_players_hands(self) -> None:
        user_data = await self.get_data(PlayerCode.USER)
        opponent_data = await self.get_data(PlayerCode.OPPONENT)
        user_hands = {
            'hand1': LEXICON[user_data['first_hand']],
            'hand2': LEXICON[user_data['second_hand']]
        }
        opponent_hands = {
            'hand1': LEXICON[opponent_data['first_hand']],
            'hand2': LEXICON[opponent_data['second_hand']]
        }
        await self.answer(whom=PlayerCode.USER,
                          text=LEXICON['your_hands'].format(**user_hands))
        await self.answer(whom=PlayerCode.USER,
                          text=LEXICON['opponent_hands'].format(
                              **opponent_hands))
        await self.answer(whom=PlayerCode.OPPONENT,
                          text=LEXICON['your_hands'].format(**opponent_hands))
        await self.answer(whom=PlayerCode.OPPONENT,
                          text=LEXICON['opponent_hands'].format(**user_hands))

    async def wait_for_hands_completion(self, timeout: int = 10,
                                        check_interval: float = 0.1
                                        ) -> PlayerCode:
        """
        Ожидает, пока оба игрока выберут два хода (first_hand и second_hand)
        в течение timeout секунд. Если оба выбрали – возвращает BOTH.
        Если только один – возвращает USER или OPPONENT того, кто успел.
        """
        start_time = asyncio.get_event_loop().time()
        while True:
            user_state, opp_state = await self.get_state_both()

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
        """Запускает задачу на ожидание выбора хода соперником"""
        if 'wait_for_hands_completion_task' in self.session.running_tasks:
            print('--- Задача уже запущена другим игроком ---')
            return  # Если задача уже запущена, выходим из функции
        wait_for_hands_completion_task = asyncio.create_task(
            self.wait_for_hands_completion(timeout, check_interval)
        )
        self.session.running_tasks[
            'wait_for_hands_completion_task'
        ] = wait_for_hands_completion_task
        players_ready = await wait_for_hands_completion_task
        self.session.kill_task('wait_for_hands_completion_task')
        match players_ready:
            case PlayerCode.BOTH:  # Оба игрока выбрали обе руки вовремя
                await self.show_players_hands()
                await self.start_hand_choice_round()
                return  # Игра продолжается
            case PlayerCode.USER:  # Пользователь успел, а соперник не нет
                await self.answer(whom=PlayerCode.OPPONENT,
                                  text=LEXICON['you_are_too_long'])
                await self.answer(whom=PlayerCode.USER,
                                  text=LEXICON['opponent_is_too_long'])
                await self.announce_winner(winner_id=self.user_id)
            case PlayerCode.OPPONENT:  # Соперник успел, а пользователь нет
                await self.answer(whom=PlayerCode.USER,
                                  text=LEXICON['you_are_too_long'])
                await self.answer(whom=PlayerCode.OPPONENT,
                                  text=LEXICON['opponent_is_too_long'])
                await self.announce_winner(winner_id=self.opponent_id)
            case PlayerCode.NOBODY:  # Никто не успел — игра отменяется
                await self.answer(whom=PlayerCode.BOTH,
                                  text=LEXICON['both_are_too_long'])
        await self.finish_game()  # Игра завершается

    async def start_first_hand_round(self) -> None:
        # Создаем клавиатуру для выбора действия у первой руки
        game_kb = create_inline_kb(*LEXICON_MOVES.keys())
        await self.answer(whom=PlayerCode.USER,
                          text=LEXICON['choose_action_for_first_hand'],
                          reply_markup=game_kb)
        await self.set_state(whom=PlayerCode.USER,
                             state_type=FSMPlay.choice_action_for_first_hand)

    async def start_second_hand_round(self) -> None:
        # Создаем клавиатуру для выбора действия у второй руки
        game_kb = create_inline_kb(*LEXICON_MOVES.keys())
        await self.answer(whom=PlayerCode.USER,
                          text=LEXICON['choose_action_for_second_hand'],
                          reply_markup=game_kb)
        await self.set_state(whom=PlayerCode.USER,
                             state_type=FSMPlay.choice_action_for_second_hand)

    async def start_hand_choice_round(self) -> None:
        # Создаем клавиатуру для выбора оставшейся руки
        game_kb = create_inline_kb('first_hand', 'second_hand')
        await self.answer(whom=PlayerCode.BOTH,
                          text=LEXICON['invitation_choose_remaining_hand'],
                          reply_markup=game_kb)
        await self.set_state(whom=PlayerCode.BOTH,
                             state_type=FSMPlay.choice_hand)

    async def process_first_hand(self) -> None:
        '''Обработка хода первой руки'''
        first_hand: str = str(self.callback.data)
        await self.update_date(whom=PlayerCode.USER,
                               first_hand=first_hand)

    async def process_second_hand(self) -> None:
        '''Обработка хода второй руки'''
        second_hand: str = str(self.callback.data)
        await self.update_date(whom=PlayerCode.USER,
                               second_hand=second_hand)
        await self.set_state(whom=PlayerCode.USER,
                             state_type=FSMPlay.both_hands_ready)

    async def clear_states(self) -> None:
        '''Очистка состояний игроков'''
        await self.user_context.clear()
        await self.opponent_context.clear()

    async def finish_game(self) -> None:
        """Завершает игру атомарно"""
        async with self.session.lock:
            # Проверяем, что игра еще не была завершена
            if self.session_id not in GameSession.sessions:
                return  # Значит игра уже была завершена оппонентом

            # Завершаем игру для обоих игроков (т.к. она еще не завершена)
            await self.answer(whom=PlayerCode.BOTH,
                              text=LEXICON['game_finished'])
            await self.clear_states()
            await self.session.delete()

    async def react_to_cancellation(self, who_cancelled: PlayerCode) -> None:
        '''Реакция на отмену игры'''
        match who_cancelled:
            case PlayerCode.OPPONENT:
                await self.answer(whom=PlayerCode.USER,
                                  text=LEXICON['opponent_cancelled_game'])
            case PlayerCode.USER:
                await self.answer(whom=PlayerCode.OPPONENT,
                                  text=LEXICON['opponent_cancelled_game'])
        await self.finish_game()

    async def react_to_timeout(self, who_timeout: PlayerCode) -> None:
        '''Реакция на таймаут'''
        # Удаляем сообщения с таймером для обоих игроков
        await self.delete_message(whom=PlayerCode.BOTH, key='message_edited_id')

        match who_timeout:
            case PlayerCode.OPPONENT:
                await self.answer(whom=PlayerCode.USER,
                                  text=LEXICON['too_long_waiting_response'])
                await self.answer(whom=PlayerCode.OPPONENT,
                                  text=LEXICON['you_are_too_long'])
            case PlayerCode.USER:
                await self.answer(whom=PlayerCode.OPPONENT,
                                  text=LEXICON['too_long_waiting_response'])
                await self.answer(whom=PlayerCode.USER,
                                  text=LEXICON['you_are_too_long'])
        await self.finish_game()

    async def wait_opponent_consent(self, send_every_n_seconds: int = 1,
                                    check_interval: float = 0.1,
                                    timeout: int = 10) -> None:
        """Ожидание ответа соперника с обновлениями статуса"""
        steps: int = 0
        send_every_step: int = int(send_every_n_seconds / check_interval)
        start_time: float = asyncio.get_event_loop().time()
        first_message: bool = True
        while True:
            opponent_data = await self.get_data(PlayerCode.OPPONENT)
            decision: bool | None = opponent_data.get('ready_to_play')

            # Проверяем не отменил ли соперник игру
            if decision is False or 'opponent_id' not in opponent_data:
                raise asyncio.CancelledError  # Вызываем отмену задачи

            if decision is True:  # Если соперник готов к игре
                return  # Выходим из функции и завершаем задачу

            if steps % send_every_step == 0:
                now_time = asyncio.get_event_loop().time()
                left: int = timeout - int(now_time - start_time)
                if first_message:  # Если это первое сообщение,
                    # то отправляем его (обоим игрокам)
                    message_id_user = await self.answer(
                        whom=PlayerCode.USER,
                        text=LEXICON['waiting_opponent'] + "\n" +
                        LEXICON['seconds_left'].format(seconds=left))
                    message_id_opp = await self.answer(
                        whom=PlayerCode.OPPONENT,
                        text=LEXICON['user_wait_you'] + "\n" +
                        LEXICON['game_will_cancel'].format(seconds=left))
                    # Сохраняем id сообщения для последующего удаления
                    await self.update_date(whom=PlayerCode.USER,
                                           message_edited_id=message_id_user)
                    await self.update_date(whom=PlayerCode.OPPONENT,
                                           message_edited_id=message_id_opp)
                    first_message = False
                else:  # Если это не первое сообщение, то редактируем его
                    await self.bot.edit_message_text(
                        chat_id=self.user_id, message_id=message_id_user,
                        text=LEXICON['waiting_opponent'] + "\n" +
                        LEXICON['seconds_left'].format(seconds=left))
                    await self.bot.edit_message_text(
                        chat_id=self.opponent_id, message_id=message_id_opp,
                        text=LEXICON['user_wait_you'] + "\n" +
                        LEXICON['game_will_cancel'].format(seconds=left))

            await asyncio.sleep(check_interval)
            steps += 1

    async def run_waiting_opponent_consent_task(self,
                                                timeout: int = 10) -> None:
        '''Запуск задачи на ожидание согласия соперника с таймаутом'''
        wait_opponent_consent_task = asyncio.create_task(
            self.wait_opponent_consent(timeout=timeout)
        )
        if 'wait_opponent_consent_task' in self.session.running_tasks:
            return  # Если задача уже запущена, то выходим из функции
        self.session.running_tasks[
            'wait_opponent_consent_task'
        ] = wait_opponent_consent_task
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
