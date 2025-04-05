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
    'scissors': '✂ Ножницы',
    'paper': '📜 Бумага',
}

LEXICON_BUTTONS: dict[str, str] = {
    'yes_button': 'Давай!',
    'no_button': 'Не хочу!',
    'quick_game': 'Быстрая игра',
    'tournir': 'Турнир',
    'matchmaking': 'Случайно',
    'start_game': 'Начать игру',
    'refuse': 'Отказаться',
    'first_hand': '✋ Левая рука',
    'second_hand': 'Правая рука 🤚',
}

LEXICON_ANSWERS: dict[str, str] = {
    'other_answer': 'Извини, увы, это сообщение мне непонятно...',
    'invitation_choose_action': 'Отлично! Делай свой выбор!',
    'choose_action_for_first_hand':
        'Bыбери действие для первой руки!',
    'choose_action_for_second_hand':
        'Bыбери действие для второй руки!',
    'invitation_choose_remaining_hand': 'Выбери руку, которую ты оставишь',
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
    'user_wait_you': 'Игрок ждет твоего решения',
    'seconds_left': 'Осталось {seconds} секунд',
    'game_will_cancel': 'Игра будет отменена через {seconds} секунд',
    'opponent_cancelled_game': 'Соперник отказался от игры',
    'opponent_ready_to_play': 'Соперник готов к игре',
    'too_long_waiting_response': 'Слишком долгое ожидание ответа соперника',
    'you_are_too_long': 'Ты слишком долго не отвечаешь',
    'opponent_is_too_long': 'Соперник слишком долго не отвечал, поэтому',
    'both_are_too_long': 'Вы оба слишком долго не отвечаете, поэтому ничья!',
    'game_finished': 'Игра завершена',
    'opponent_made_move': 'Соперник уже сделал свой ход! Скорее выбирай!',
    'you_win': 'Ты выиграл!',
    'you_lose': 'Ты проиграл!',
    'your_hands': 'Твои ходы:\n\n✋ {hand1}       {hand2} 🤚',
    'opponent_hands': 'Ходы соперника:\n\n✋ {hand1}       {hand2} 🤚',
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
