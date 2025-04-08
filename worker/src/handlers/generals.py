from typing import Callable, TypeAlias, Awaitable
from .tick import hands_completion_tick
from .timeout import hands_completion_timeout

TimerNameType: TypeAlias = str
SessionIDType: TypeAlias = str
TimeLeftType: TypeAlias = float
HandlerTickType: TypeAlias = Callable[[SessionIDType, TimeLeftType],
                                      Awaitable[None]]
HandlerTimeoutType: TypeAlias = Callable[[SessionIDType, TimeLeftType],
                                         Awaitable[bool]]

handlers_tick: dict[TimerNameType, HandlerTickType] = {
    "hands_completion": hands_completion_tick,
}

handlers_timeout: dict[TimerNameType, HandlerTimeoutType] = {
    "hands_completion": hands_completion_timeout,
}


# Пример функций-обработчиков, которые вызываются для такта и истечения.
async def handle_tick(session_id: str,
                      timer_name: str, time_left: float) -> None:
    """
    Выполняет такт обновления для активного таймера.
    Параметр time_left показывает, сколько времени осталось до истечения.

    Здесь можно обновлять, например, сообщение с обратным отсчётом.
    """
    if handler := handlers_tick.get(timer_name):
        await handler(session_id, time_left)


async def handle_timeout(session_id: str,
                         timer_name: str, time_left: float) -> bool:
    """
    Обрабатывает истёкший таймер для заданной сессии.

    В зависимости от timer_name выполняется различная логика.
    Если обработка завершена (например, таймаут истёк и условие выполнено),
    функция возвращает True, чтобы сигнализировать, что элемент можно удалить.
    """
    if handler := handlers_timeout.get(timer_name):
        return await handler(session_id, time_left)
    return False
