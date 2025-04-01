from aiogram import F, Router
from aiogram.types import Message, CallbackQuery
from keyboards.keyboards import yes_no_kb
from lexicon.lexicon_ru import LEXICON, LEXICON_MOVES
from services.services import get_bot_choice, get_winner
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from states.states import FSMPlay


router = Router()


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
