import json
import time
import asyncio
import uuid
from multiprocessing import Process

from shared.repositories.redis import rdb
from .src.handlers.generals import handle_tick, handle_timeout


async def global_tick():
    """
    Выполняет один такт обновления для всех таймеров, хранящихся в Sorted Set "game_timers".

    Шаги:
    1. Получаем текущее время.
    2. Извлекаем все элементы, у которых next_tick (score) <= now.
    3. Для каждого элемента:
       - Если время истекло (now >= expire_at), вызываем обработчик истечения (handle_timeout).
       - Если ещё не истекло, вызываем функцию такта обновления (handle_tick) и пересчитываем next_tick.
    4. Обновляем элемент в Sorted Set.
    """
    key = "game_timers"  # Название Sorted Set, где хранятся все таймеры.
    now = time.time()  # Получаем текущее время (timestamp в секундах).

    # Получаем список элементов, у которых score (next_tick) <= now.
    due_elements = await rdb.zrangebyscore(key, 0, now)

    for element in due_elements:
        try:
            timer_data = json.loads(element)  # Десериализуем элемент из JSON в словарь.
        except json.JSONDecodeError:
            # Если элемент невозможно десериализовать, удаляем его, чтобы не мешал дальнейшей обработке.
            await rdb.zrem(key, element)
            continue

        session_id = timer_data["session_id"]  # Уникальный идентификатор сессии (например, "123:456").
        timer_name = timer_data["timer_name"]  # Имя таймера (например, "wait_opponent_consent").
        expire_at = timer_data["expire_at"]      # Время, когда таймер должен истечь.
        frequency = timer_data["frequency"]      # Интервал между тактами, задаёт период обновления.

        if now >= expire_at:
            # Если текущее время больше или равно времени истечения, таймер истёк.
            # Вызываем обработчик истечения.
            done = await handle_timeout(session_id, timer_name)
            # Если обработчик сигнализировал, что задача выполнена, удаляем элемент из Sorted Set.
            if done:
                await rdb.zrem(key, element)
        else:
            # Таймер ещё активен, поэтому выполняем такт обновления.
            await handle_tick(session_id, timer_name, expire_at - now)
            # Обновляем поле next_tick: следующий такт будет через frequency секунд от текущего момента.
            timer_data["next_tick"] = now + frequency
            new_element = json.dumps(timer_data)
            # Обновляем элемент в Sorted Set: удаляем старый элемент и добавляем новый с новым значением score.
            async with rdb.pipeline() as pipe:
                pipe.zrem(key, element)
                pipe.zadd(key, {new_element: timer_data["next_tick"]})
                await pipe.execute()


def worker(worker_id: str):
    async def worker_async(worker_id: str):
        while True:
            # Каждый воркер вызывает функцию global_tick()
            await global_tick()
    asyncio.run(worker_async(worker_id))


if __name__ == '__main__':

    processes = []
    # Создаём, например, 10 воркеров
    for i in range(10):
        worker_id = str(uuid.uuid4().hex)
        processes.append(Process(target=worker, args=(worker_id,)))

    try:
        for p in processes:
            p.start()
        for p in processes:
            p.join()
    except KeyboardInterrupt:
        for p in processes:
            p.terminate()
