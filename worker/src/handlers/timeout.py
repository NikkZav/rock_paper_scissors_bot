import asyncio
from shared.utils.enums import PlayerCode
from shared.lexicon.lexicon_ru import LEXICON
from .generals import SessionIDType, TimeLeftType
from bot.src.handlers.user_handlers.game_managers import GameMaster


async def hands_completion_timeout(session_id: SessionIDType,
                                   time_left: TimeLeftType) -> bool:
    self = GameMaster()  #  Надо подумать как это сделать, потому что пока всё через GameMaster
    players_ready = #  Как-то получаем сохранённые состояния и в зависимости от них действуем
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
    return True
