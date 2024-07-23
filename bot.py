import telebot
from telebot import types
from random import shuffle
import asyncio
import logging
import time

logging.basicConfig(level=logging.INFO)

bot = telebot.TeleBot("7191998889:AAHk1HXznlL0-xI7DDanbPdiYvQLI8zb_Qs")

# Словарь со всеми чатами и игроками в этих чатах
chat_list = {}


is_night = False

class Game:
    def __init__(self):
        self.players = {}
        self.dead = None
        self.sheriff_check = None
        self.doc_target = None  # Новый атрибут для хранения цели доктора
        self.vote_counts = {}
        self.game_running = False
        self.button_id = None
        self.dList_id = None
        self.shList_id = None
        self.docList_id = None  # Новый атрибут для сообщения доктора
        
    def update_player_list(self):
        players_list = ", ".join([player['name'] for player in self.players.values()])
        return players_list

    def remove_player(self, player_id):
        if player_id in self.players:
            del self.players[player_id]
        self.update_player_list()

    def update_player_list(self):
        # Функция для обновления списка игроков
        players_list = ", ".join([player['name'] for player in self.players.values()])
        return players_list

def change_role(player_id, player_dict, new_role, text):
    player_dict[player_id].update({'role': new_role, 'skipped_actions': 0})
    bot.send_message(player_id, text)

def list_btn(player_dict, user_id, player_role, text):
    players_btn = types.InlineKeyboardMarkup()
    for key, val in player_dict.items():
        if val['role'] != player_role and val['role'] != 'dead':
            players_btn.add(types.InlineKeyboardButton(val['name'], callback_data=f'{key}_{player_role[0]}'))
    bot.send_message(user_id, text, reply_markup=players_btn)

def registration_message(players):
    if players:
        player_names = [player['name'] for player in players.values()]
        player_list = ', '.join(player_names)
        return f"Ведётся набор в игру\n\nЗарегистрировались:\n{player_list}\n\nИтого: {len(player_names)} чел."
    else:
        return "*Ведётся набор в игру*"

def night_message(players):
    living_players = [f"{i + 1}. {player['name']}" for i, player in enumerate(players.values()) if player['role'] != 'dead']
    player_list = '\n'.join(living_players)
    return f"*Живые игроки:*\n{player_list}\n\nспать осталось 45 сек.\n"

def day_message(players):
    living_players = [f"{i + 1}. {player['name']}" for i, player in enumerate(players.values()) if player['role'] != 'dead']
    player_list = '\n'.join(living_players)
    roles = [player['role'] for player in players.values() if player['role'] != 'dead']
    role_counts = {role: roles.count(role) for role in set(roles)}
    roles_text = ', '.join([f"{role}: {count}" for role, count in role_counts.items()])
    return f"*Живые игроки:*\n{player_list}\n\nКто-то из них:\n{roles_text}\nВсего: {len(living_players)} чел.\n\nСейчас самое время обсудить результаты ночи, разобраться в причинах и следствиях…"

def players_alive(player_dict, phase):
    if phase == "registration":
        return registration_message(player_dict)
    elif phase == "night":
        return night_message(player_dict)
    elif phase == "day":
        return day_message(player_dict)

def emoji(role):
    emojis = {
        'мафия': '🤵🏻',
        'шериф': '🕵🏼️‍♂️',
        'мирный житель': '👨🏼',
        'доктор': '👨‍⚕️'
    }
    return emojis.get(role, '')

def voice_handler(chat_id):
    global chat_list
    chat = chat_list[chat_id]
    players = chat.players
    votes = []
    for player_id, player in players.items():
        if 'voice' in player:
            votes.append(player['voice'])
            del player['voice']
    if votes:
        dead_id = max(set(votes), key=votes.count)
        dead = players.pop(dead_id)
        return dead

@bot.message_handler(commands=['start'])
def start_message(message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    text = message.text

    # Проверяем, есть ли параметр после команды /start
    if len(text.split()) > 1:
        param = text.split()[1]
        if param.startswith("join_"):
            game_chat_id = int(param.split('_')[1])
            chat = chat_list.get(game_chat_id)
            if chat and user_id not in chat.players:
                user_name = message.from_user.first_name
                chat.players[user_id] = {'name': user_name, 'role': 'ждет', 'skipped_actions': 0}
                bot.send_message(user_id, f"Вы присоединились в чате «{bot.get_chat(game_chat_id).title}»")
                bot.edit_message_text(chat_id=game_chat_id, message_id=chat.button_id, text=players_alive(chat.players, "registration"), reply_markup=types.InlineKeyboardMarkup([[types.InlineKeyboardButton('Присоединиться к игре', url=f'https://t.me/{bot.get_me().username}?start=join_{game_chat_id}')]]))
            else:
                bot.send_message(user_id, "Вы уже зарегистрированы в этой игре или игра не найдена.")
            return

    # Создаем клавиатуру для кнопок "🎲 Войти в чат", "📰 Новости" и "🤵🏻 Добавить игру в свой чат"
    keyboard = types.InlineKeyboardMarkup()
    
    # Кнопка "🎲 Войти в чат"
    join_chat_btn = types.InlineKeyboardButton('🎲 Войти в чат', callback_data='join_chat')
    keyboard.add(join_chat_btn)
    
    # Кнопка "📰 Новости"
    news_btn = types.InlineKeyboardButton('📰 Новости', url='https://t.me/RealMafiaNews')
    keyboard.add(news_btn)

    # Формируем ссылку для добавления бота в группу
    bot_username = bot.get_me().username
    add_to_group_url = f'https://t.me/{bot_username}?startgroup=bot_command'
    
    # Кнопка "🤵🏻 Добавить игру в свой чат" (добавление бота в группу)
    add_to_group_btn = types.InlineKeyboardButton('🤵🏻 Добавить игру в свой чат', url=add_to_group_url)
    keyboard.add(add_to_group_btn)

    # Отправляем сообщение с приветствием и клавиатурой
    bot.send_message(chat_id, 'Привет!\nЯ ведущий бот по игре мафия🤵🏻. Начнем играть?', reply_markup=keyboard)

    else:
        bot.send_message(message.chat.id, "Команда /start доступна только в приватном чате с ботом.")

@bot.callback_query_handler(func=lambda call: call.data == 'join_chat')
def join_chat_callback(call):
    chat_id = call.message.chat.id
    message_id = call.message.message_id


    # Создаем клавиатуру для кнопки "🛠️ Тестовый"
    test_button = types.InlineKeyboardMarkup()
    test_btn = types.InlineKeyboardButton('🛠️ Тестовый', url='https://t.me/+ZAgUMKzgjKRkNTli')
    test_button.add(test_btn)

    # Отправляем сообщение с кнопкой "🛠️ Тестовый"
    bot.send_message(chat_id, 'Выберите чат для общения:', reply_markup=test_button)

@bot.message_handler(commands=['game'])
def create_game(message):
    chat_id = message.chat.id
    if chat_id not in chat_list:
        chat_list[chat_id] = Game()

    chat = chat_list[chat_id]

    if chat.game_running or chat.button_id:
        # Игнорируем команду и удаляем сообщение, если игра уже начата или регистрация уже открыта
        bot.delete_message(chat_id, message.message_id)
        return

    join_btn = types.InlineKeyboardMarkup()
    bot_username = bot.get_me().username
    join_url = f'https://t.me/{bot_username}?start=join_{chat_id}'
    item1 = types.InlineKeyboardButton('Присоединиться к игре', url=join_url)
    join_btn.add(item1)

    # Отправляем начальное сообщение о наборе
    msg_text = registration_message(chat.players)
    msg = bot.send_message(chat_id, msg_text, reply_markup=join_btn, parse_mode="Markdown")
    chat.button_id = msg.message_id

    # Удаляем сообщение с командой /game
    bot.delete_message(chat_id, message.message_id)

@bot.message_handler(commands=['start_game'])
def start_game(message):
    chat_id = message.chat.id
    if chat_id not in chat_list:
        bot.send_message(chat_id, 'Сначала создайте игру с помощью команды /game.')
        return

    chat = chat_list[chat_id]
    if chat.game_running:
        bot.send_message(chat_id, 'Игра уже начата.')
        return

    if len(chat.players) < 4:
        bot.send_message(chat_id, 'Недостаточно игроков для начала игры (минимум 4).')
        if chat.button_id:
            bot.delete_message(chat_id, chat.button_id)
            chat.button_id = None
        return

    chat.game_running = True
    bot.send_message(chat_id, '*Игра начинается!*', parse_mode="Markdown")

    players_list = list(chat.players.items())
    shuffle(players_list)

    # Удаляем сообщение о регистрации
    if chat.button_id:
        bot.delete_message(chat_id, chat.button_id)
        chat.button_id = None

    # Назначение ролей
    change_role(players_list[0][0], chat.players, '🤵🏻 Мафия', 'Ты - 🤵🏻мафия! Твоя задача убрать всех мирных жителей.')

    if len(players_list) >= 6:
        change_role(players_list[1][0], chat.players, '🕵️‍♂️ Шериф', 'Ты - 🕵🏼️‍♂️шериф! Твоя задача вычислить мафию и спасти город.')
        start_index = 2
    else:
        start_index = 1

    doctor_assigned = False
    for i in range(start_index, len(players_list)):
        if len(players_list) >= 4 and not doctor_assigned:
            change_role(players_list[i][0], chat.players, '👨‍⚕️ Доктор', 'Ты - 👨‍⚕️доктор! Твоя задача спасать жителей от рук мафии.')
            doctor_assigned = True
        else:
            change_role(players_list[i][0], chat.players, '👱‍♂️ Мирный житель', 'Ты - 👨🏼мирный житель! Твоя задача найти мафию и защитить город.')

    asyncio.run(game_cycle(chat_id))

    # Удаляем сообщение с командой /start_game
    bot.delete_message(chat_id, message.message_id)

@bot.message_handler(commands=['leave'])
def leave_game(message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    chat = chat_list.get(chat_id)

    if not chat:
        bot.send_message(chat_id, "Игра не найдена.")
        return

    if user_id not in chat.players:
        bot.send_message(chat_id, "Вы не зарегистрированы в этой игре.")
        return

    role = chat.players[user_id]['role']
    name = chat.players[user_id]['name']
    
    # Удаление пользователя из списка игроков
    del chat.players[user_id]
    chat.update_player_list()
    
    if chat.game_running:
        bot.send_message(user_id, "Вы вышли из игры.")
        bot.send_message(chat_id, f"{name} не выдержал гнетущей атмосферы этого города и повесился. Он был {emoji(role)} {role}")
    else:
        bot.send_message(user_id, "Вы вышли из регистрации.")
        bot.edit_message_text(chat_id=chat_id, message_id=chat.button_id, text=players_alive(chat.players, "registration"), reply_markup=types.InlineKeyboardMarkup([[types.InlineKeyboardButton('Присоединиться к игре', url=f'https://t.me/{bot.get_me().username}?start=join_{chat_id}')]]))

    # Удаление сообщения пользователя из общего чата
    bot.delete_message(chat_id, message.message_id)
    

@bot.message_handler(commands=['game', 'start_game', 'leave'])
def game_commands(message):
    if message.chat.type == "private":
        bot.send_message(message.chat.id, "Эти команды доступны только в общем чате.")
    else:
        # Обработка команд в общем чате
        if message.text.startswith('/game'):
            create_game(message)
        elif message.text.startswith('/start_game'):
            start_game(message)
        elif message.text.startswith('/leave'):
            leave_game(message)

bot_username = "@nrlv_bot"

# Обновленный код для функции game_cycle
async def game_cycle(chat_id):
    global chat_list, is_night
    chat = chat_list[chat_id]
    game_start_time = time.time()
    
    day_count = 1  # Инициализация счётчика дней

    while chat.game_running:
        await asyncio.sleep(5)

        is_night = True
        players_alive_text = players_alive(chat.players, "night")

        # Создаем клавиатуру с кнопкой "Перейти к боту"
        keyboard_night = types.InlineKeyboardMarkup()
        button = types.InlineKeyboardButton('Перейти к боту', url=f'https://t.me/{bot.get_me().username}')
        keyboard_night.add(button)

        # Отправляем сообщение с кнопкой и списком живых игроков
        bot.send_animation(chat_id, 'https://t.me/Hjoxbednxi/13', caption='🌃 Наступает ночь\nНа улицы города выходят лишь самые отважные и бесстрашные.\nУтром попробуем сосчитать их головы...', parse_mode="Markdown", reply_markup=keyboard_night)
        msg = bot.send_message(chat_id=chat_id, text=players_alive_text, parse_mode="Markdown", reply_markup=keyboard_night)
        chat.button_id = msg.message_id

        chat.dead = None
        chat.sheriff_check = None
        chat.doc_target = None

        for player_id, player in chat.players.items():
            if player['role'] == '🤵🏻 Мафия':
                chat.dList_id = list_btn(chat.players, player_id, 'мафия', 'Кого будем устранять?')
            elif player['role'] == '🕵️‍♂️ Шериф':
                chat.shList_id = list_btn(chat.players, player_id, 'шериф', 'Кого будем проверять?')
            elif player['role'] == '👨‍⚕️ Доктор':
                chat.docList_id = list_btn(chat.players, player_id, 'доктор', 'Кого будем лечить?')

        await asyncio.sleep(30)

        is_night = False

        to_remove = []
        for player_id, player in chat.players.items():
            if player['role'] != '👱‍♂️ Мирный житель' and not player.get('action_taken', False):
                player['skipped_actions'] += 1
                if player['skipped_actions'] >= 2:
                    to_remove.append(player_id)
            else:
                player['action_taken'] = False

        bot.send_animation(chat_id, 'https://t.me/Hjoxbednxi/14', caption=f'🏙 День {day_count}\nСолнце всходит,\nподсушивая на тротуарах пролитую ночью кровь...', parse_mode="Markdown")

        if chat.dead:
            dead_id, dead = chat.dead
            if chat.doc_target and chat.doc_target == dead_id:
                bot.send_message(chat_id, '👨‍⚕️ Доктор кого-то спас', parse_mode="Markdown")
            else:
                bot.send_message(chat_id, f'Сегодня жестоко убит {dead["name"]}...\nГоворят, у него в гостях был 🤵🏻 Мафия', parse_mode="Markdown")
                chat.remove_player(dead_id)
                players_list_text = chat.update_player_list()

        players_alive_text = players_alive(chat.players, "day")
        msg = bot.send_message(chat_id=chat_id, text=players_alive_text, parse_mode="Markdown")
        chat.button_id = msg.message_id

        chat.dead = None
        chat.sheriff_check = None

        await asyncio.sleep(40)

        # Обновляем голосование
        bot.send_message(chat_id, '🌅 Пришло время голосования!\nВыберите игрока, которого хотите изгнать.',
                         reply_markup=types.InlineKeyboardMarkup([
                             [types.InlineKeyboardButton('🗳️ Голосование', url=f'https://t.me/{bot.get_me().username}')]
                         ]))

        for player_id in chat.players:
            try:
                bot.send_message(player_id, 'Пришло время искать виноватых!\nКого ты хочешь повесить?', reply_markup=types.InlineKeyboardMarkup(
                    [[types.InlineKeyboardButton(chat.players[pid]['name'], callback_data=f"{pid}_vote")] for pid in chat.players]
                ))
            except Exception as e:
                logging.error(f"Не удалось отправить сообщение игроку {player_id}: {e}")

        await asyncio.sleep(45)

        # Обработка голосов
        max_votes = 0
        to_kill = None
        for player_id, votes in chat.vote_counts.items():
            if votes > max_votes:
                max_votes = votes
                to_kill = player_id

        if to_kill is not None:
            dead = chat.players[to_kill]
            bot.send_message(chat_id, f'🌅 {dead["name"]} этим вечером покидает\nгород | Его роль {dead["role"]}', parse_mode="Markdown")
            chat.remove_player(to_kill)
            players_list_text = chat.update_player_list()
        else:
            bot.send_message(chat_id, 'Жители города не смогли прийти к единому решению.')

        chat.vote_counts.clear()
        for player in chat.players.values():
            player['has_voted'] = False

        # Проверка на завершение игры
        mafia_count = len([p for p in chat.players.values() if p['role'] == '🤵🏻 Мафия'])
        non_mafia_count = len(chat.players) - mafia_count

        if mafia_count == 0 or mafia_count >= non_mafia_count:
            winners = [f"{v['name']} - {v['role']}" for k, v in chat.players.items() if v['role'] == '🤵🏻 Мафия']
            losers = [f"{v['name']} - {v['role']}" for k, v in chat.players.items() if v['role'] != '🤵🏻 Мафия']

            game_duration = time.time() - game_start_time
            minutes = int(game_duration // 60)
            seconds = int(game_duration % 60)

            result_text = f"Игра окончена!\nПобедила {'Мафия' if mafia_count > 0 else 'Мирные жители'}\n\nПобедители:\n{', '.join(winners) if winners else 'Нет победителей'}\n\nОстальные участники:\n{', '.join(losers) if losers else 'Нет проигравших'}\n\nИгра длилась: {minutes} мин. {seconds} сек."

            # Отправляем сообщение о завершении игры в общий чат
            bot.send_message(chat_id, result_text)

            # Отправляем сообщение "Игра окончена!" всем участникам в приватных чатах
            for player_id in chat.players:
                try:
                    bot.send_message(player_id, "Игра окончена!\n\nПодпишитесь на наш новостной канал,\nгде вы там можете узнавать игровые обновление!\n\n@RealMafiaNrws")
                except Exception as e:
                    logging.error(f"Не удалось отправить сообщение игроку {player_id}: {e}")

            # Убедитесь, что игра может быть запущена снова
            chat_list[chat_id] = Game()
            break

        day_count += 1  # Увеличиваем счётчик дней
        

@bot.callback_query_handler(func=lambda call: call.data.startswith('join_'))
def join_game(call):
    chat_id = int(call.data.split('_')[1])
    chat = chat_list[chat_id]
    user_id = call.from_user.id
    user_name = call.from_user.first_name

    if user_id not in chat.players:
        chat.players[user_id] = {'name': user_name, 'role': 'ждет', 'skipped_actions': 0}
        bot.answer_callback_query(call.id, text="Вы присоединились к игре!")

        # Обновляем сообщение о наборе
        new_msg_text = registration_message(chat.players)
        bot.edit_message_text(chat_id=chat_id, message_id=chat.button_id, text=new_msg_text, reply_markup=call.message.reply_markup, parse_mode="Markdown")
    else:
        bot.answer_callback_query(call.id, text="Вы уже зарегистрированы в этой игре.")

@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    global chat_list
    from_id = call.from_user.id

    chat = None
    for c_id, c in chat_list.items():
        if from_id in c.players:
            chat = c
            chat_id = c_id
            break

    if not chat:
        return

    try:
        data_parts = call.data.split('_')
        target_id = int(data_parts[0])
        action = data_parts[1]

        player_role = chat.players[from_id]['role']

        if player_role == '🤵🏻 Мафия' and action == 'м':  # Мафия выбирает жертву
            chat.dead = (target_id, chat.players[target_id])
            bot.send_message(chat_id, "🤵🏻 Мафия выбрала жертву...")
            bot.send_message(from_id, f"Вы выбрали убить {chat.players[target_id]['name']}")
            bot.delete_message(from_id, call.message.message_id)

        elif player_role == '🕵️‍♂️ Шериф' and action == 'ш':  # Шериф проверяет игрока
            chat.sheriff_check = target_id
            bot.send_message(chat_id, "🕵️‍♂️ Шериф ушел искать злодеев...")
            bot.send_message(from_id, f"Вы проверили {chat.players[target_id]['name']}, он - {chat.players[target_id]['role']}")
            bot.delete_message(from_id, call.message.message_id)

        elif player_role == '👨‍⚕️ Доктор' and action == 'д':  # Доктор выбирает цель для лечения
            chat.doc_target = target_id
            bot.send_message(chat_id, "👨‍⚕️ Доктор выбрал цель для лечения...")
            bot.send_message(from_id, f"Вы выбрали лечить {chat.players[target_id]['name']}")
            bot.delete_message(from_id, call.message.message_id)

        elif action == 'vote':  # Голосование
            if 'vote_counts' not in chat.__dict__:
                chat.vote_counts = {}  # Создаем vote_counts, если его нет

            if not chat.players[from_id].get('has_voted', False):
                chat.vote_counts[target_id] = chat.vote_counts.get(target_id, 0) + 1
                chat.players[from_id]['has_voted'] = True
                bot.send_message(chat_id, f"{chat.players[from_id]['name']} проголосовал(а) за {chat.players[target_id]['name']}")
                bot.send_message(from_id, f"Ты выбрал(а) {chat.players[target_id]['name']}")
                bot.delete_message(from_id, call.message.message_id)

    except Exception as e:
        logging.error(f"Ошибка при обработке callback: {e}")

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    global is_night
    chat_id = message.chat.id
    user_id = message.from_user.id

    if message.chat.type != "private":
        chat = chat_list.get(chat_id)
        if chat:
            if chat.game_running:  # Проверка, что игра идет
                # Проверяем, является ли пользователь администратором
                chat_member = bot.get_chat_member(chat_id, user_id)
                is_admin = chat_member.status in ['administrator', 'creator']

                if is_night:
                    if message.text.startswith('!') or is_admin:
                        # Если сообщение начинается с ! или пользователь администратор, не удаляем сообщение
                        return
                    else:
                        bot.delete_message(chat_id, message.message_id)
                else:
                    if user_id in chat.players:
                        if chat.players[user_id]['role'] != 'dead':
                            return
                    bot.delete_message(chat_id, message.message_id)
            else:
                # Разрешить сообщения, если игра не идет
                return
        else:
            bot.delete_message(chat_id, message.message_id)

bot.infinity_polling()
