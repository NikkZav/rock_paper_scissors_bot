from collections import ChainMap
from typing import Mapping


LEXICON_COMMANDS: dict[str, str] = {
    '/start': '<b>Привет!</b>\nДавай с тобой сыграем в игру '
              '"Камень, ножницы, бумага"?\n\nЕсли ты, вдруг, '
              'забыл правила, команда /help тебе поможет!\n\n<b>Играем?</b>',
    '/help': 'Это очень простая игра. Мы одновременно должны '
             'сделать выбор одного из трех предметов. Камень, '
             'ножницы или бумага.\n\nЕсли наш выбор '
             'совпадает - ничья, а в остальных случаях камень '
             'побеждает ножницы, ножницы побеждают бумагу, '
             'а бумага побеждает камень.\n\n<b>Играем?</b>',
}

LEXICON_MOVES: dict[str, str] = {
    'rock': '🪨 Камень',
    'paper': '📜 Бумага',
    'scissors': '✂ Ножницы',
}

LEXICON_BUTTONS: dict[str, str] = {
    'yes_button': 'Давай!',
    'no_button': 'Не хочу!',
    'quick_game': 'Быстрая игра',
    'tournir': 'Турнир',
    'matchmaking': 'Подбор случайного соперника',
    'start_game': 'Начать игру',
    'refuse': 'Отказаться',
    'first_hand': 'Первая рука',
    'second_hand': 'Вторая рука',
}

LEXICON_ANSWERS: dict[str, str] = {
    'other_answer': 'Извини, увы, это сообщение мне непонятно...',
    'invitation_choose_action': 'Отлично! Делай свой выбор!',
    'refused_to_play': 'Жаль...\nЕсли захочешь сыграть, просто разверни '
                       'клавиатуру и нажми кнопку "Давай!"',
    'bot_won': 'Я победил!\n\nСыграем еще?',
    'user_won': 'Ты победил! Поздравляю!\n\nДавай сыграем еще?',
    'nobody_won': 'Ничья!\n\nПродолжим?',
    'bot_choice': 'Мой выбор',
    'user_choice': 'Твой выбор',
    'choice_game_mode': 'Выбери режим игры',
    'choice_user_search': 'Выбери способ поиска соперника',
    'your_opponent': 'Твой <a href="tg://user?id={opponent_id}">соперник</a>',
    'you_are_chosen': '<a href="tg://user?id={user_id}">Игрок</a> '
                      'бросает тебе вызов! '
                      'Готов принять его и сразиться с ним?',
    'waiting_opponent': 'Ждем пока соперник примет игру...',
    'opponent_refused': 'Соперник отказался от игры',
    'opponent_ready_to_play': 'Соперник готов к игре',
    'too_long_waiting_response': 'Слишком долгое ожидание ответа соперника',
    'game_cancelled': 'Игра отменена',
    'opponent_made_move': 'Соперник уже сделал свой ход! Скорее выбирай!',
}

LEXICON_WARNINGS: dict[str, str] = {
    'invalid_move_choise': 'Такой выбор невозможен, '
                           'выбери что-то из предложенного!',
    'no_online_users': 'Нет онлайн пользователей',
    'opponent_not_found': 'Соперник не найден',
}

LEXICON: Mapping[str, str] = ChainMap(
    LEXICON_COMMANDS,
    LEXICON_MOVES,
    LEXICON_BUTTONS,
    LEXICON_ANSWERS,
    LEXICON_WARNINGS
)
