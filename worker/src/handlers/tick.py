import asyncio
from shared.utils.enums import PlayerCode
from shared.states import FSMPlay
from .generals import SessionIDType, TimeLeftType


async def hands_completion_tick(session_id: SessionIDType,
                                time_left: TimeLeftType) -> PlayerCode:
    """
    Ожидает, пока оба игрока выберут два хода (first_hand и second_hand)
    в течение timeout секунд. Если оба выбрали – возвращает BOTH.
    Если только один – возвращает USER или OPPONENT того, кто успел.
    """
    user_state, opp_state = get_state_both()  #  Надо подумать как это сделать

    user_complete = (user_state == FSMPlay.both_hands_ready)
    opp_complete = (opp_state == FSMPlay.both_hands_ready)

    if user_complete and opp_complete:
        return PlayerCode.BOTH  # А здесь должна быть особоая обрабортка с отключением таймера
        # В принципе можно искусвтенно вызывать timeout handler на следующем такте
        # Проосто указав внутри таймера expire_at = time.now()
        # Чтобы не обрабатывать этот случай как-то по особенному
        # Т.е. на тиках мы проверяем состояние и сохраняем его
        # Если удовлетворительное состояние (т.е. нет смысла ждать) - то имитируем таймаут
        # А уже обработчик таймаута в зависимости от состояния делает нужные действия
    elif user_complete and not opp_complete:
        return PlayerCode.USER  # Теперь это надо не возвращать, а сохранять куда-то
    elif opp_complete and not user_complete:
        return PlayerCode.OPPONENT  # Теперь это надо не возвращать, а сохранять куда-то
    else:
        return PlayerCode.NOBODY  # Теперь это надо не возвращать, а сохранять куда-то
