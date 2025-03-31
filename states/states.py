from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import default_state, State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage


# Инициализируем хранилище (создаем экземпляр класса MemoryStorage)
storage = MemoryStorage()


class FSMMenu(StatesGroup):
    game_consent = State()
    choice_game_mode = State()
    quick_game = State()
    matchmaking = State()


class FSMPlay(StatesGroup):
    waiting_game_start = State()
    choice_action_for_first_hand = State()
    choice_action_for_second_hand = State()
    choice_hand = State()
