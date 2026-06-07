import vk_api
import sqlite3
import re
import time
import threading
import os
import hashlib
import secrets
from datetime import datetime, timedelta
from vk_api.bot_longpoll import VkBotLongPoll, VkBotEventType
from vk_api.keyboard import VkKeyboard, VkKeyboardColor

# ================= КОНФИГУРАЦИЯ =================
GROUP_TOKEN = "vk1.a.il01zAU15IjY0-LSKJdu8KsB7-Pe4rfg6SGQU9Squd4eueMyxEW8d-vRCQhezzfykvnN0-DzqcizQSpclUpmhL67-vArn6w_tMJdsvyM8IDl4hecOmwUo-KPD-hsOw9L3xRjh7Avm56sE3QogwkS_4gJADK1tsy-DpKAvKxAq6Uqm3ncPOLpJ8cuDHGqrJ0_wx8fJTag-LJCVoRLfnjrDQ"
GROUP_ID = 238315078

# Пароль для получения прав владельца (ИЗМЕНИТЕ НА СВОЙ!)
OWNER_PASSWORD = "SagePasswordBONUSrcon"  # <--- СЮДА ВСТАВЬТЕ СВОЙ ПАРОЛЬ

# Инициализация
vk_session = vk_api.VkApi(token=GROUP_TOKEN)
vk = vk_session.get_api()
longpoll = VkBotLongPoll(vk_session, group_id=GROUP_ID)

# Словарь для хранения подключений к БД для разных чатов
db_connections = {}
cursors = {}

# Множество для отслеживания уже обработанных чатов (чтобы не выдавать права повторно)
processed_chats = set()


def hash_password(password):
    """Хэширует пароль"""
    return hashlib.sha256(password.encode()).hexdigest()


def check_and_give_owner_rights(chat_id):
    """Проверяет, нужно ли выдать права владельцу для данного чата"""
    # Убрана автоматическая выдача прав
    return False


def get_db_for_chat(chat_id):
    """Возвращает соединение с БД для конкретного чата"""
    if chat_id not in db_connections:
        # Создаём отдельную БД для каждого чата
        db_path = f"admin_bot_chat_{chat_id}.db"
        is_new = not os.path.exists(db_path)

        conn = sqlite3.connect(db_path, check_same_thread=False)
        cursor = conn.cursor()

        # Создаём таблицы
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                first_name TEXT,
                last_name TEXT,
                nick TEXT,
                warns INTEGER DEFAULT 0,
                is_banned BOOLEAN DEFAULT 0,
                banned_until TEXT,
                is_muted BOOLEAN DEFAULT 0,
                muted_until TEXT,
                messages_count INTEGER DEFAULT 0
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS admins (
                user_id INTEGER PRIMARY KEY,
                level INTEGER DEFAULT 0
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS level_names (
                level INTEGER PRIMARY KEY,
                name TEXT DEFAULT ''
            )
        ''')

        # Добавляем названия уровней по умолчанию
        default_level_names = {
            0: "👤 Пользователь",
            1: "🌟 Саппорт",
            2: "📌 Администратор",
            3: "📌 Ст.Администратор",
            4: "📋🕵️ ЗГС крим/госс",
            5: "🏛️🔎 ГС крим/госс",
            6: "⚔️ Заместитель главного администратора",
            7: "🛡️ Главный администратор",
            8: "💎 Спец админ",
            9: "🧠 Руководитель",
            10: "📝 Директор",
            11: "👑 Основатель",
            12: "🧑‍💻 Разработчик"
        }
        for level, name in default_level_names.items():
            cursor.execute('INSERT OR IGNORE INTO level_names (level, name) VALUES (?, ?)', (level, name))

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS chat_owner (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                owner_id INTEGER,
                is_owner_assigned BOOLEAN DEFAULT 0
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS banned_words (
                word TEXT PRIMARY KEY
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS cmd_levels (
                command TEXT PRIMARY KEY,
                min_level INTEGER DEFAULT 0
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS rules (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                text TEXT DEFAULT "Правила чата не установлены."
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS chat_settings (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                welcome_text TEXT,
                silent_mode BOOLEAN DEFAULT 0
            )
        ''')

        # Добавляем команды с уровнями
        default_commands = [
            ('пинг', 0), ('ping', 0), ('статус', 0), ('test', 0), ('тест', 0),
            ('помощь', 0), ('help', 0), ('команды', 0), ('cmds', 0),
            ('правила', 0), ('rules', 0),
            ('админы', 0), ('admins', 0), ('staff', 0),
            ('онлайн', 0), ('online', 0),
            ('стата', 0), ('stats', 0), ('статистика', 0),
            ('чатинфо', 0), ('chatinfo', 0), ('очате', 0), ('инфо', 0), ('info', 0),
            ('рандом', 0), ('roll', 0),
            ('голосование', 0), ('vote', 0),
            ('setowner', 0), ('установитьвладельца', 0),  # Команда для получения прав (доступна всем)
            ('мут', 5), ('mute', 5), ('заткнуть', 5),
            ('унмут', 5), ('unmute', 5), ('разоткнуть', 5),
            ('кик', 5), ('kick', 5), ('исключить', 5),
            ('варн', 5), ('warn', 5), ('пред', 5),
            ('унварн', 5), ('unwarn', 5), ('снятьпред', 5),
            ('варны', 5), ('warns', 5), ('warnlist', 5),
            ('сник', 5), ('snick', 5), ('setnick', 5),
            ('removenick', 5), ('рник', 5),
            ('нлист', 5), ('nlist', 5), ('nicklist', 5),
            ('напомни', 5), ('remind', 5),
            ('бан', 6), ('ban', 6), ('блок', 6),
            ('унбан', 6), ('unban', 6), ('разблок', 6),
            ('banlist', 6),
            ('тишина', 6), ('silence', 6),
            ('админ', 9), ('addadmin', 9),
            ('фильтр', 9), ('filter', 9),
            ('unfilter', 9), ('убратьфильтр', 9),
            ('фильтры', 9), ('filters', 9),
            ('welcome', 9), ('приветствие', 9),
            ('setrules', 9), ('установитьправила', 9), ('srules', 9),
            ('clear', 9), ('очистить', 9),
            ('purge', 9), ('очиститьпользователя', 9),
            ('pin', 9), ('закрепить', 9),
            ('unpin', 9), ('открепить', 9),
            ('gm', 10), ('gamemode', 10), ('иммунитет', 10),
            ('editcmd', 11), ('настройкакоманд', 11),
            ('setlvlname', 11), ('установитьназвание', 11),
            ('lvlnames', 11), ('списокназваний', 11),
            ('setup', 12), ('owner', 12), ('владелец', 12),
        ]
        for cmd, lvl in default_commands:
            cursor.execute('INSERT OR IGNORE INTO cmd_levels (command, min_level) VALUES (?, ?)', (cmd, lvl))

        conn.commit()

        db_connections[chat_id] = conn
        cursors[chat_id] = cursor

    return db_connections[chat_id], cursors[chat_id]


# ================= ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ =================

def get_user_name(user_id):
    try:
        user = vk.users.get(user_ids=user_id)[0]
        return f"{user.get('first_name', '')} {user.get('last_name', '')}".strip()
    except:
        return f"id{user_id}"


def get_user_username(user_id):
    try:
        user = vk.users.get(user_ids=user_id, fields=['screen_name'])[0]
        screen_name = user.get('screen_name', '')
        if screen_name:
            return f"@{screen_name}"
        return get_user_name(user_id)
    except:
        return get_user_name(user_id)


def get_user_link(user_id):
    try:
        user = vk.users.get(user_ids=user_id)[0]
        name = f"{user.get('first_name', '')} {user.get('last_name', '')}".strip()
        return f"[id{user_id}|{name}]"
    except:
        return f"[id{user_id}|id{user_id}]"


def get_level_name(chat_id, level):
    conn, cursor = get_db_for_chat(chat_id)
    cursor.execute('SELECT name FROM level_names WHERE level = ?', (level,))
    res = cursor.fetchone()
    if res and res[0]:
        return res[0]
    return f"Уровень {level}"


def get_admin_level(chat_id, user_id):
    conn, cursor = get_db_for_chat(chat_id)
    cursor.execute('SELECT level FROM admins WHERE user_id = ?', (user_id,))
    res = cursor.fetchone()
    if res:
        return res[0]
    return 0


def get_user_level_in_chat(chat_id, user_id):
    conn, cursor = get_db_for_chat(chat_id)
    cursor.execute('SELECT owner_id FROM chat_owner WHERE id = 1')
    res = cursor.fetchone()
    if res and res[0] == user_id:
        return 12
    return get_admin_level(chat_id, user_id)


def can_execute(chat_id, user_id, command):
    user_level = get_user_level_in_chat(chat_id, user_id)
    conn, cursor = get_db_for_chat(chat_id)
    cursor.execute('SELECT min_level FROM cmd_levels WHERE command = ?', (command,))
    res = cursor.fetchone()
    required_level = res[0] if res else 0
    return user_level >= required_level


def send_message(chat_id, text, keyboard=None):
    try:
        params = {
            'peer_id': chat_id,
            'message': text,
            'random_id': 0
        }
        if keyboard:
            params['keyboard'] = keyboard.get_keyboard()
        vk.messages.send(**params)
    except Exception as e:
        print(f"Ошибка отправки: {e}")


def kick_user(chat_id, user_id):
    try:
        vk.messages.removeChatUser(chat_id=chat_id, user_id=user_id)
        return True
    except:
        return False


def extract_user_id_from_text(text):
    username_match = re.search(r'@([a-zA-Z0-9_]+)', text)
    if username_match:
        username = username_match.group(1)
        try:
            user = vk.users.get(user_ids=username)[0]
            return user['id']
        except:
            pass
    id_match = re.search(r'\[id(\d+)\|', text)
    if id_match:
        return int(id_match.group(1))
    return None


def add_warn(chat_id, user_id):
    conn, cursor = get_db_for_chat(chat_id)
    cursor.execute('SELECT warns FROM users WHERE user_id = ?', (user_id,))
    res = cursor.fetchone()
    warns = (res[0] if res else 0) + 1
    cursor.execute('INSERT OR REPLACE INTO users (user_id, warns) VALUES (?, ?)', (user_id, warns))
    conn.commit()
    send_message(chat_id, f"⚠️ {get_user_link(user_id)} получил предупреждение. {warns}/3")
    if warns >= 3:
        kick_user(chat_id, user_id)
        send_message(chat_id, f"🚫 {get_user_link(user_id)} получил 3 варна и был исключён!")
    return warns


# ================= НОВАЯ КОМАНДА ДЛЯ ВЫДАЧИ ПРАВ =================

def handle_setowner(chat_id, from_id, args, reply_msg=None):
    """Обработчик команды /setowner - выдает права владельца по паролю (только 1 раз)"""

    if len(args) < 2:
        send_message(chat_id, "🔐 **Получение прав владельца**\n\n"
                              "Используйте: `/setowner [пароль]`\n\n"
                              "⚠️ Права выдаются только **ОДИН РАЗ** первому, кто введет правильный пароль!\n"
                              "После выдачи команда станет недоступной.")
        return

    password = args[1]

    # Проверяем пароль
    if password != OWNER_PASSWORD:
        send_message(chat_id, "❌ Неверный пароль! Доступ запрещен.")
        return

    conn, cursor = get_db_for_chat(chat_id)

    # Проверяем, не выдавались ли уже права в этом чате
    cursor.execute('SELECT is_owner_assigned FROM chat_owner WHERE id = 1')
    result = cursor.fetchone()

    if result and result[0] == 1:
        send_message(chat_id, "⚠️ Права владельца уже были выданы ранее!\n"
                              "Команда `/setowner` больше недоступна в этом чате.\n\n"
                              "Для передачи прав используйте: `/owner @username` (только текущий владелец)")
        return

    # Проверяем, не является ли пользователь уже владельцем
    cursor.execute('SELECT owner_id FROM chat_owner WHERE id = 1')
    existing_owner = cursor.fetchone()

    if existing_owner and existing_owner[0]:
        send_message(chat_id, f"⚠️ В этом чате уже есть владелец: {get_user_link(existing_owner[0])}\n"
                              f"Права не могут быть выданы повторно.")
        return

    # Выдаем права владельца
    cursor.execute('INSERT OR REPLACE INTO chat_owner (id, owner_id, is_owner_assigned) VALUES (1, ?, 1)', (from_id,))
    cursor.execute('INSERT OR REPLACE INTO admins (user_id, level) VALUES (?, ?)', (from_id, 12))
    conn.commit()

    # Отправляем сообщение о успешной выдаче прав
    welcome_text = f"""👑 **ПРАВА ВЛАДЕЛЬЦА ПОЛУЧЕНЫ!**

{get_user_link(from_id)}, вам успешно выдан максимальный 12 уровень доступа!

📊 **Ваши возможности:**
• Полный доступ ко всем командам бота
• Назначение и снятие администраторов
• Настройка прав команд
• Передача прав другому владельцу

🔧 **Быстрая настройка:**
• /setup — быстрая настройка бота
• /админ @user [уровень] — назначить администратора
• /setrules [текст] — установить правила
• /filter [слово] — добавить слово в фильтр

📋 Полный список команд: /help

⚠️ **ВНИМАНИЕ!** 
Команда `/setowner` больше недоступна в этом чате.
Передать права можно через: `/owner @username`"""

    send_message(chat_id, welcome_text)

    print(f"✅ Владельцем чата {chat_id} стал пользователь {from_id}")


# ================= ВСЕ ОБРАБОТЧИКИ КОМАНД =================

def handle_ping(chat_id, from_id, args, reply_msg=None):
    send_message(chat_id, "🏓 Понг! Бот работает.")


def handle_help(chat_id, from_id, args, reply_msg=None):
    user_level = get_user_level_in_chat(chat_id, from_id)

    # Проверяем, есть ли уже владелец в чате
    conn, cursor = get_db_for_chat(chat_id)
    cursor.execute('SELECT owner_id, is_owner_assigned FROM chat_owner WHERE id = 1')
    owner_data = cursor.fetchone()
    has_owner = owner_data and owner_data[0] is not None

    text = f"""📋 **ПОЛНЫЙ СПИСОК КОМАНД БОТА**

👤 **Ваш уровень:** {get_level_name(chat_id, user_level)} ({user_level})

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🔹 **👤 ПОЛЬЗОВАТЕЛЬСКИЕ (уровень 0)**
/пинг | /ping — проверка работы бота
/помощь | /help — этот список
/правила | /rules — показать правила чата
/админы | /admins — список администрации
/онлайн | /online — кто сейчас в сети
/стата | /stats [@user] — статистика пользователя
/чатинфо | /info — информация о беседе
/рандом | /roll 🎲 — случайное число 1-100
/голосование | /vote — создать голосование"""

    # Показываем команду /setowner только если владелец еще не назначен
    if not has_owner:
        text += f"""

🔐 **🔥 ПОЛУЧЕНИЕ ПРАВ (доступно всем)**
/setowner [пароль] — получить права владельца (только 1 раз!)"""

    text += """

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🔹 **🛡️ УРОВЕНЬ 5+**
/мут | /mute [@user] [1m/1h/1d] — замутить
/унмут | /unmute [@user] — размутить
/кик | /kick [@user] — кикнуть
/варн | /warn [@user] — выдать варн (3 = кик)
/унварн | /unwarn [@user] — снять варн
/варны | /warns — список варнов
/сник | /snick [@user] [ник] — установить ник
/removenick | /рник [@user] — удалить ник
/нлист | /nlist — список ников
/напомни | /remind [Текст. 5m. 1. 3] — напоминание

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🔹 **🔨 УРОВЕНЬ 6+**
/бан | /ban [@user] — забанить
/унбан | /unban [ID] — разбанить
/banlist — список забаненных
/тишина | /silence — режим тишины

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🔹 **💎 УРОВЕНЬ 9+**
/админ | /addadmin [@user] [уровень] — назначить админа
/фильтр | /filter [слово] — добавить в фильтр
/unfilter | /убратьфильтр [слово] — удалить из фильтра
/фильтры | /filters — список фильтров
/welcome | /приветствие [текст] — приветствие
/setrules | /установитьправила [текст] — правила
/clear | /очистить [1-100] — очистка чата
/purge | /очиститьпользователя [@user] — очистить сообщения
/pin | /закрепить (ответом) — закрепить
/unpin | /открепить — открепить

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🔹 **⭐ УРОВЕНЬ 10+**
/gm | /gamemode [@user] — иммунитет

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🔹 **🔥 УРОВЕНЬ 11+**
/editcmd [команда] [уровень] — настроить права команды
/setlvlname [уровень] [название] — переименовать уровень
/lvlnames — список названий уровней

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🔹 **👸 УРОВЕНЬ 12 (Владелец)**
/setup — быстрая настройка
/owner | /владелец [@user] — передать права

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📌 **ФОРМАТЫ ИСПОЛЬЗОВАНИЯ:**

• Ответом на сообщение: (ответ) /кик
• С упоминанием: /бан @durov
• С аргументами: /мут @user 1h"""

    send_message(chat_id, text)


def handle_rules(chat_id, from_id, args, reply_msg=None):
    conn, cursor = get_db_for_chat(chat_id)
    cursor.execute('SELECT text FROM rules WHERE id = 1')
    res = cursor.fetchone()
    text = res[0] if res else "Правила не установлены."
    send_message(chat_id, f"📜 **Правила чата:**\n{text}")


def handle_admins(chat_id, from_id, args, reply_msg=None):
    conn, cursor = get_db_for_chat(chat_id)
    cursor.execute('SELECT owner_id FROM chat_owner WHERE id = 1')
    owner = cursor.fetchone()
    owner_id = owner[0] if owner else None

    cursor.execute('SELECT user_id, level FROM admins ORDER BY level DESC')
    admins = cursor.fetchall()

    text = "👑 **Администрация беседы:**\n\n"

    admin_list = []

    if owner_id:
        admin_list.append((owner_id, 12, True))

    for uid, level in admins:
        if uid != owner_id:
            admin_list.append((uid, level, False))

    admin_list.sort(key=lambda x: x[1], reverse=True)

    for uid, level, is_owner in admin_list:
        level_name = get_level_name(chat_id, level)
        if is_owner:
            text += f"👑 {get_user_username(uid)} — {level_name}\n"
        else:
            text += f"👤 {get_user_username(uid)} — {level_name}\n"

    if not admin_list:
        text = "Нет назначенных администраторов."

    send_message(chat_id, text)


def handle_online(chat_id, from_id, args, reply_msg=None):
    try:
        users = vk.messages.getConversationMembers(peer_id=chat_id, group_id=GROUP_ID)
        online_count = 0
        online_list = []
        for user in users.get('items', []):
            if user.get('is_online', False):
                online_count += 1
                online_list.append(get_user_link(user['member_id']))

        text = f"🟢 **Онлайн ({online_count}):**\n" + "\n".join(online_list[:20])
        if len(online_list) > 20:
            text += f"\n... и ещё {len(online_list) - 20}"
        send_message(chat_id, text)
    except:
        send_message(chat_id, "Не удалось получить список онлайн")


def handle_stats(chat_id, from_id, args, reply_msg=None):
    target_id = from_id
    if len(args) > 1:
        target_id = extract_user_id_from_text(' '.join(args[1:]))
        if not target_id and args[1].isdigit():
            target_id = int(args[1])
    if not target_id:
        send_message(chat_id, "ℹ️ Используйте: /стата @username")
        return

    conn, cursor = get_db_for_chat(chat_id)
    cursor.execute('SELECT warns, messages_count FROM users WHERE user_id = ?', (target_id,))
    res = cursor.fetchone()
    warns = res[0] if res else 0
    msgs = res[1] if res else 0
    level = get_user_level_in_chat(chat_id, target_id)
    level_name = get_level_name(chat_id, level)
    text = f"📊 **Статистика {get_user_link(target_id)}**\n\n"
    text += f"👤 Уровень: {level_name}\n"
    text += f"⚠️ Варнов: {warns}/3\n"
    text += f"💬 Сообщений: {msgs}\n"
    send_message(chat_id, text)


def handle_chatinfo(chat_id, from_id, args, reply_msg=None):
    try:
        chat = vk.messages.getConversationsById(peer_ids=chat_id, group_id=GROUP_ID)
        if chat and 'items' in chat and chat['items']:
            chat_info = chat['items'][0]
            chat_settings = chat_info.get('chat_settings', {})
            title = chat_settings.get('title', 'Название не установлено')
            members_count = chat_settings.get('members_count', 0)
            owner_id = chat_settings.get('owner_id', 0)
            text = f"📋 **Информация о беседе**\n\n"
            text += f"📝 Название: {title}\n"
            text += f"👥 Участников: {members_count}\n"
            text += f"👑 Владелец ВК: {get_user_link(owner_id)}\n"
            send_message(chat_id, text)
    except:
        send_message(chat_id, "Не удалось получить информацию")


def handle_roll(chat_id, from_id, args, reply_msg=None):
    import random
    num = random.randint(1, 100)
    send_message(chat_id, f"🎲 {get_user_link(from_id)} выбросил {num} из 100")


def handle_vote(chat_id, from_id, args, reply_msg=None):
    if len(args) < 2:
        send_message(chat_id, "📊 /vote Вопрос. Вариант1. Вариант2")
        return
    full_text = ' '.join(args[1:])
    parts = [p.strip() for p in full_text.split('.')]
    if len(parts) < 3:
        send_message(chat_id, "📊 /vote Вопрос. Вариант1. Вариант2")
        return
    title = parts[0]
    options = parts[1:4]
    keyboard = VkKeyboard()
    for i, opt in enumerate(options):
        keyboard.add_button(opt, color=VkKeyboardColor.PRIMARY)
        if i < len(options) - 1:
            keyboard.add_line()
    send_message(chat_id, f"🗳 **{title}**\n\nГолосуйте:", keyboard)


def handle_lvlnames(chat_id, from_id, args, reply_msg=None):
    conn, cursor = get_db_for_chat(chat_id)
    cursor.execute('SELECT level, name FROM level_names ORDER BY level')
    levels = cursor.fetchall()

    text = "📊 **Названия уровней:**\n\n"
    for level, name in levels:
        text += f"**{level}** — {name}\n"

    send_message(chat_id, text)


def handle_nlist(chat_id, from_id, args, reply_msg=None):
    if not can_execute(chat_id, from_id, 'nlist'):
        send_message(chat_id, f"⛔ Недостаточно прав! Требуется уровень 5+")
        return

    conn, cursor = get_db_for_chat(chat_id)
    cursor.execute('SELECT user_id, nick FROM users WHERE nick IS NOT NULL AND nick != "" ORDER BY user_id')
    users = cursor.fetchall()
    if not users:
        send_message(chat_id, "📋 Ники не установлены.")
        return

    admin_levels = {}
    cursor.execute('SELECT user_id, level FROM admins')
    for uid, level in cursor.fetchall():
        admin_levels[uid] = level

    cursor.execute('SELECT owner_id FROM chat_owner WHERE id = 1')
    owner = cursor.fetchone()
    owner_id = owner[0] if owner else None

    text = "📋 **Список пользователей с ником:**\n\n"
    for i, (uid, nick) in enumerate(users, 1):
        if uid == owner_id:
            level_display = get_level_name(chat_id, 12)
        elif uid in admin_levels:
            level_display = get_level_name(chat_id, admin_levels[uid])
        else:
            level_display = get_level_name(chat_id, 0)

        text += f"{i}. {get_user_link(uid)} — {nick} | {level_display}\n"

        if i >= 50:
            text += f"\n... и ещё {len(users) - 50} пользователей"
            break

    send_message(chat_id, text)


def handle_removenick(chat_id, from_id, args, reply_msg=None):
    if not can_execute(chat_id, from_id, 'removenick'):
        send_message(chat_id, f"⛔ Недостаточно прав! Требуется уровень 5+")
        return

    target_id = None
    if reply_msg and 'reply_message' in reply_msg:
        target_id = reply_msg['reply_message']['from_id']
    else:
        target_id = extract_user_id_from_text(' '.join(args[1:]))

    if not target_id:
        send_message(chat_id, "ℹ️ /removenick @username   или   ответьте на сообщение")
        return

    conn, cursor = get_db_for_chat(chat_id)
    cursor.execute('SELECT nick FROM users WHERE user_id = ?', (target_id,))
    res = cursor.fetchone()

    if not res or not res[0]:
        send_message(chat_id, f"❌ У {get_user_link(target_id)} нет ника для удаления")
        return

    cursor.execute('UPDATE users SET nick = NULL WHERE user_id = ?', (target_id,))
    conn.commit()
    send_message(chat_id, f"✅ Удалён ник у {get_user_link(target_id)}")


def handle_mute(chat_id, from_id, args, reply_msg=None):
    if not can_execute(chat_id, from_id, 'mute'):
        send_message(chat_id, f"⛔ Недостаточно прав! Требуется уровень 5+")
        return
    target_id = None
    if reply_msg and 'reply_message' in reply_msg:
        target_id = reply_msg['reply_message']['from_id']
    else:
        target_id = extract_user_id_from_text(' '.join(args[1:]))
    if not target_id:
        send_message(chat_id, "ℹ️ /мут @username 1m/1h/1d")
        return
    time_found = None
    for arg in args:
        if re.match(r"\d+[mhd]", arg):
            time_found = arg
            break
    if not time_found:
        send_message(chat_id, "❌ Укажите время: 1m, 2h, 3d")
        return
    match = re.match(r"(\d+)([mhd])", time_found)
    if not match:
        send_message(chat_id, "❌ Формат: 1m, 2h, 3d")
        return
    amount, unit = int(match[1]), match[2]
    if unit == 'm':
        delay = timedelta(minutes=amount)
    elif unit == 'h':
        delay = timedelta(hours=amount)
    else:
        delay = timedelta(days=amount)
    until = datetime.now() + delay
    conn, cursor = get_db_for_chat(chat_id)
    cursor.execute('INSERT OR REPLACE INTO users (user_id, is_muted, muted_until) VALUES (?, ?, ?)',
                   (target_id, 1, until.isoformat()))
    conn.commit()
    send_message(chat_id, f"🔇 {get_user_link(target_id)} замучен до {until.strftime('%Y-%m-%d %H:%M')}")


def handle_unmute(chat_id, from_id, args, reply_msg=None):
    if not can_execute(chat_id, from_id, 'unmute'):
        send_message(chat_id, f"⛔ Недостаточно прав! Требуется уровень 5+")
        return
    target_id = None
    if reply_msg and 'reply_message' in reply_msg:
        target_id = reply_msg['reply_message']['from_id']
    else:
        target_id = extract_user_id_from_text(' '.join(args[1:]))
    if not target_id:
        send_message(chat_id, "ℹ️ /унмут @username")
        return
    conn, cursor = get_db_for_chat(chat_id)
    cursor.execute('UPDATE users SET is_muted = 0, muted_until = NULL WHERE user_id = ?', (target_id,))
    conn.commit()
    send_message(chat_id, f"🔊 {get_user_link(target_id)} размучен")


def handle_kick(chat_id, from_id, args, reply_msg=None):
    if not can_execute(chat_id, from_id, 'kick'):
        send_message(chat_id, f"⛔ Недостаточно прав! Требуется уровень 5+")
        return
    target_id = None
    if reply_msg and 'reply_message' in reply_msg:
        target_id = reply_msg['reply_message']['from_id']
    else:
        target_id = extract_user_id_from_text(' '.join(args[1:]))
    if not target_id:
        send_message(chat_id, "ℹ️ /кик @username")
        return
    if kick_user(chat_id, target_id):
        send_message(chat_id, f"👢 {get_user_link(target_id)} кикнут")
    else:
        send_message(chat_id, "❌ Не удалось кикнуть пользователя")


def handle_warn(chat_id, from_id, args, reply_msg=None):
    if not can_execute(chat_id, from_id, 'warn'):
        send_message(chat_id, f"⛔ Недостаточно прав! Требуется уровень 5+")
        return
    target_id = None
    if reply_msg and 'reply_message' in reply_msg:
        target_id = reply_msg['reply_message']['from_id']
    else:
        target_id = extract_user_id_from_text(' '.join(args[1:]))
    if not target_id:
        send_message(chat_id, "ℹ️ /варн @username")
        return
    add_warn(chat_id, target_id)


def handle_unwarn(chat_id, from_id, args, reply_msg=None):
    if not can_execute(chat_id, from_id, 'unwarn'):
        send_message(chat_id, f"⛔ Недостаточно прав! Требуется уровень 5+")
        return
    target_id = None
    if reply_msg and 'reply_message' in reply_msg:
        target_id = reply_msg['reply_message']['from_id']
    else:
        target_id = extract_user_id_from_text(' '.join(args[1:]))
    if not target_id:
        send_message(chat_id, "ℹ️ /унварн @username")
        return
    conn, cursor = get_db_for_chat(chat_id)
    cursor.execute('SELECT warns FROM users WHERE user_id = ?', (target_id,))
    res = cursor.fetchone()
    warns = max(0, (res[0] if res else 0) - 1)
    cursor.execute('UPDATE users SET warns = ? WHERE user_id = ?', (warns, target_id))
    conn.commit()
    send_message(chat_id, f"✅ Снят варн. Осталось: {warns}/3")


def handle_warns(chat_id, from_id, args, reply_msg=None):
    if not can_execute(chat_id, from_id, 'warns'):
        send_message(chat_id, f"⛔ Недостаточно прав! Требуется уровень 5+")
        return
    conn, cursor = get_db_for_chat(chat_id)
    cursor.execute('SELECT user_id, warns FROM users WHERE warns > 0')
    users = cursor.fetchall()
    if not users:
        send_message(chat_id, "Нет пользователей с предупреждениями.")
        return
    text = "⚠️ **Список предупреждений:**\n"
    for uid, warns in users:
        text += f"{get_user_link(uid)} — {warns}/3\n"
    send_message(chat_id, text)


def handle_snick(chat_id, from_id, args, reply_msg=None):
    if not can_execute(chat_id, from_id, 'snick'):
        send_message(chat_id, f"⛔ Недостаточно прав! Требуется уровень 5+")
        return
    target_id = None
    if reply_msg and 'reply_message' in reply_msg:
        target_id = reply_msg['reply_message']['from_id']
    else:
        target_id = extract_user_id_from_text(' '.join(args[1:]))
    if not target_id:
        send_message(chat_id, "ℹ️ /сник @username [ник]")
        return
    if len(args) < 2:
        send_message(chat_id, "ℹ️ Укажите ник: /сник @username НовыйНик")
        return
    new_nick = args[-1]
    conn, cursor = get_db_for_chat(chat_id)
    cursor.execute('INSERT OR REPLACE INTO users (user_id, nick) VALUES (?, ?)', (target_id, new_nick))
    conn.commit()
    send_message(chat_id, f"✅ Установлен ник '{new_nick}' для {get_user_link(target_id)}")


def handle_remind(chat_id, from_id, args, reply_msg=None):
    if not can_execute(chat_id, from_id, 'remind'):
        send_message(chat_id, f"⛔ Недостаточно прав! Требуется уровень 5+")
        return
    if len(args) < 2:
        send_message(chat_id, "📌 /remind Текст. 5m. 1. 1")
        return
    full_text = ' '.join(args[1:])
    parts = [p.strip() for p in full_text.split('.')]
    if len(parts) < 4:
        send_message(chat_id, "📌 Формат: /remind Текст. 5m. 1. 1\n(1=упомянуть, 2=не упоминать)")
        return
    reminder_text = parts[0]
    duration_str = parts[1]
    online_notify = parts[2] == '1'
    repeat_count = int(parts[3]) if parts[3].isdigit() else 1
    match = re.match(r"(\d+)([mhd])", duration_str)
    if not match:
        send_message(chat_id, "📌 Формат времени: 10m, 2h, 1d")
        return
    amount, unit = int(match[1]), match[2]
    if unit == 'm':
        delay = timedelta(minutes=amount)
    elif unit == 'h':
        delay = timedelta(hours=amount)
    else:
        delay = timedelta(days=amount)
    send_message(chat_id, f"⏰ Напомню через {duration_str}: {reminder_text} (повторов: {repeat_count})")

    def remind():
        for i in range(repeat_count):
            time.sleep(delay.total_seconds())
            mention = f" {get_user_link(from_id)}" if online_notify else ""
            send_message(chat_id, f"🔔 Напоминание{mention}:\n{reminder_text} (повтор {i + 1}/{repeat_count})")

    thread = threading.Thread(target=remind)
    thread.daemon = True
    thread.start()


def handle_ban(chat_id, from_id, args, reply_msg=None):
    if not can_execute(chat_id, from_id, 'ban'):
        send_message(chat_id, f"⛔ Недостаточно прав! Требуется уровень 6+")
        return
    target_id = None
    if reply_msg and 'reply_message' in reply_msg:
        target_id = reply_msg['reply_message']['from_id']
    else:
        target_id = extract_user_id_from_text(' '.join(args[1:]))
    if not target_id:
        send_message(chat_id, "ℹ️ /бан @username")
        return
    if kick_user(chat_id, target_id):
        conn, cursor = get_db_for_chat(chat_id)
        cursor.execute('INSERT OR REPLACE INTO users (user_id, is_banned) VALUES (?, ?)', (target_id, 1))
        conn.commit()
        send_message(chat_id, f"🚫 {get_user_link(target_id)} забанен")
    else:
        send_message(chat_id, "❌ Не удалось забанить")


def handle_unban(chat_id, from_id, args, reply_msg=None):
    if not can_execute(chat_id, from_id, 'unban'):
        send_message(chat_id, f"⛔ Недостаточно прав! Требуется уровень 6+")
        return
    if len(args) < 2:
        send_message(chat_id, "ℹ️ /унбан 123456789")
        return
    target_id = int(args[1])
    conn, cursor = get_db_for_chat(chat_id)
    cursor.execute('UPDATE users SET is_banned = 0 WHERE user_id = ?', (target_id,))
    conn.commit()
    send_message(chat_id, f"✅ Пользователь {target_id} разбанен")


def handle_banlist(chat_id, from_id, args, reply_msg=None):
    if not can_execute(chat_id, from_id, 'banlist'):
        send_message(chat_id, f"⛔ Недостаточно прав! Требуется уровень 6+")
        return
    conn, cursor = get_db_for_chat(chat_id)
    cursor.execute('SELECT user_id FROM users WHERE is_banned = 1')
    users = cursor.fetchall()
    if not users:
        send_message(chat_id, "Нет забаненных пользователей.")
        return
    text = "🚫 **Забаненные пользователи:**\n"
    for (uid,) in users:
        text += f"{get_user_link(uid)}\n"
    send_message(chat_id, text)


def handle_silence(chat_id, from_id, args, reply_msg=None):
    if not can_execute(chat_id, from_id, 'silence'):
        send_message(chat_id, f"⛔ Недостаточно прав! Требуется уровень 6+")
        return
    conn, cursor = get_db_for_chat(chat_id)
    cursor.execute('SELECT silent_mode FROM chat_settings WHERE id = 1')
    res = cursor.fetchone()
    current = res[0] if res else False
    new_mode = not current
    cursor.execute('INSERT OR REPLACE INTO chat_settings (id, silent_mode) VALUES (1, ?)', (new_mode,))
    conn.commit()
    status = "включён" if new_mode else "выключен"
    send_message(chat_id, f"🔇 Режим тишины {status}")


def handle_addadmin(chat_id, from_id, args, reply_msg=None):
    if not can_execute(chat_id, from_id, 'addadmin'):
        send_message(chat_id, f"⛔ Недостаточно прав! Требуется уровень 9+")
        return
    if len(args) < 3:
        send_message(chat_id, "ℹ️ /админ @username [уровень]\nУровни: 0-12")
        return
    target_id = extract_user_id_from_text(' '.join(args[1:-1]))
    if not target_id:
        send_message(chat_id, "❌ Пользователь не найден")
        return
    try:
        level = int(args[-1])
        if level < 0 or level > 12:
            send_message(chat_id, "❌ Уровень должен быть от 0 до 12")
            return
    except:
        send_message(chat_id, "❌ Уровень должен быть числом")
        return
    conn, cursor = get_db_for_chat(chat_id)
    cursor.execute('INSERT OR REPLACE INTO admins (user_id, level) VALUES (?, ?)', (target_id, level))
    conn.commit()
    level_name = get_level_name(chat_id, level)
    send_message(chat_id, f"👑 {get_user_link(target_id)} назначен на уровень {level} ({level_name})")


def handle_filter(chat_id, from_id, args, reply_msg=None):
    if not can_execute(chat_id, from_id, 'filter'):
        send_message(chat_id, f"⛔ Недостаточно прав! Требуется уровень 9+")
        return
    if len(args) < 2:
        send_message(chat_id, "ℹ️ /filter мат")
        return
    word = args[1].lower()
    conn, cursor = get_db_for_chat(chat_id)
    cursor.execute('INSERT OR IGNORE INTO banned_words (word) VALUES (?)', (word,))
    conn.commit()
    send_message(chat_id, f"➕ Слово '{word}' добавлено в фильтр")


def handle_unfilter(chat_id, from_id, args, reply_msg=None):
    if not can_execute(chat_id, from_id, 'unfilter'):
        send_message(chat_id, f"⛔ Недостаточно прав! Требуется уровень 9+")
        return
    if len(args) < 2:
        send_message(chat_id, "ℹ️ /unfilter мат")
        return
    word = args[1].lower()
    conn, cursor = get_db_for_chat(chat_id)
    cursor.execute('DELETE FROM banned_words WHERE word = ?', (word,))
    conn.commit()
    send_message(chat_id, f"➖ Слово '{word}' удалено из фильтра")


def handle_filters(chat_id, from_id, args, reply_msg=None):
    conn, cursor = get_db_for_chat(chat_id)
    cursor.execute('SELECT word FROM banned_words')
    words = cursor.fetchall()
    if not words:
        send_message(chat_id, "📋 Фильтр пуст.")
        return
    text = "🚫 **Запрещенные слова:**\n" + "\n".join([f"• {w[0]}" for w in words])
    send_message(chat_id, text)


def handle_welcome(chat_id, from_id, args, reply_msg=None):
    if not can_execute(chat_id, from_id, 'welcome'):
        send_message(chat_id, f"⛔ Недостаточно прав! Требуется уровень 9+")
        return
    if len(args) < 2:
        conn, cursor = get_db_for_chat(chat_id)
        cursor.execute('DELETE FROM chat_settings WHERE id = 1')
        conn.commit()
        send_message(chat_id, "✅ Приветствие отключено")
        return
    text = ' '.join(args[1:])
    conn, cursor = get_db_for_chat(chat_id)
    cursor.execute('INSERT OR REPLACE INTO chat_settings (id, welcome_text) VALUES (1, ?)', (text,))
    conn.commit()
    send_message(chat_id, f"✅ Приветствие установлено!")


def handle_setrules(chat_id, from_id, args, reply_msg=None):
    if not can_execute(chat_id, from_id, 'setrules'):
        send_message(chat_id, f"⛔ Недостаточно прав! Требуется уровень 9+")
        return
    if len(args) < 2:
        send_message(chat_id, "ℹ️ /setrules Текст правил")
        return
    text = ' '.join(args[1:])
    conn, cursor = get_db_for_chat(chat_id)
    cursor.execute('INSERT OR REPLACE INTO rules (id, text) VALUES (1, ?)', (text,))
    conn.commit()
    send_message(chat_id, "✅ Правила обновлены!")


def handle_clear(chat_id, from_id, args, reply_msg=None):
    if not can_execute(chat_id, from_id, 'clear'):
        send_message(chat_id, f"⛔ Недостаточно прав! Требуется уровень 9+")
        return
    if len(args) < 2 or not args[1].isdigit():
        send_message(chat_id, "ℹ️ /clear 50 (от 1 до 100)")
        return
    count = min(100, int(args[1]))
    send_message(chat_id, f"🗑 Очищено {count} сообщений")


def handle_purge(chat_id, from_id, args, reply_msg=None):
    if not can_execute(chat_id, from_id, 'purge'):
        send_message(chat_id, f"⛔ Недостаточно прав! Требуется уровень 9+")
        return
    target_id = None
    if reply_msg and 'reply_message' in reply_msg:
        target_id = reply_msg['reply_message']['from_id']
    else:
        target_id = extract_user_id_from_text(' '.join(args[1:]))
    if not target_id:
        send_message(chat_id, "ℹ️ /purge @username")
        return
    send_message(chat_id, f"🧹 История сообщений {get_user_link(target_id)} очищена")


def handle_pin(chat_id, from_id, args, reply_msg=None):
    if not can_execute(chat_id, from_id, 'pin'):
        send_message(chat_id, f"⛔ Недостаточно прав! Требуется уровень 9+")
        return
    if not reply_msg or 'reply_message' not in reply_msg:
        send_message(chat_id, "ℹ️ Ответьте на сообщение, которое хотите закрепить: /pin")
        return
    msg_id = reply_msg['reply_message']['id']
    try:
        vk.messages.pin(peer_id=chat_id, message_id=msg_id)
        send_message(chat_id, "📌 Сообщение закреплено!")
    except:
        send_message(chat_id, "❌ Не удалось закрепить сообщение")


def handle_unpin(chat_id, from_id, args, reply_msg=None):
    if not can_execute(chat_id, from_id, 'unpin'):
        send_message(chat_id, f"⛔ Недостаточно прав! Требуется уровень 9+")
        return
    try:
        vk.messages.unpin(peer_id=chat_id)
        send_message(chat_id, "📌 Закреплённое сообщение откреплено!")
    except:
        send_message(chat_id, "❌ Не удалось открепить сообщение")


def handle_gm(chat_id, from_id, args, reply_msg=None):
    if not can_execute(chat_id, from_id, 'gm'):
        send_message(chat_id, f"⛔ Недостаточно прав! Требуется уровень 10+")
        return
    send_message(chat_id, "🛡️ Режим иммунитета (заглушка)")


def handle_editcmd(chat_id, from_id, args, reply_msg=None):
    if not can_execute(chat_id, from_id, 'editcmd'):
        send_message(chat_id, f"⛔ Недостаточно прав! Требуется уровень 11+")
        return
    if len(args) < 3:
        send_message(chat_id, "ℹ️ /editcmd [команда] [уровень]\nУровни: 0-12\nПример: /editcmd mute 7")
        return
    cmd = args[1].lower()
    try:
        new_level = int(args[2])
        if new_level < 0 or new_level > 12:
            send_message(chat_id, "❌ Уровень должен быть от 0 до 12")
            return
    except:
        send_message(chat_id, "❌ Уровень должен быть числом от 0 до 12")
        return
    conn, cursor = get_db_for_chat(chat_id)
    cursor.execute('INSERT OR REPLACE INTO cmd_levels (command, min_level) VALUES (?, ?)', (cmd, new_level))
    conn.commit()
    level_name = get_level_name(chat_id, new_level)
    send_message(chat_id, f"✅ Команда /{cmd} теперь доступна с уровня: {level_name} ({new_level})")


def handle_setlvlname(chat_id, from_id, args, reply_msg=None):
    if not can_execute(chat_id, from_id, 'setlvlname'):
        send_message(chat_id, f"⛔ Недостаточно прав! Требуется уровень 11+")
        return
    if len(args) < 3:
        send_message(chat_id, "ℹ️ /setlvlname [уровень] [название]\nПример: /setlvlname 5 🛡️ Модератор")
        return
    try:
        level = int(args[1])
        if level < 0 or level > 12:
            send_message(chat_id, "❌ Уровень должен быть от 0 до 12")
            return
    except:
        send_message(chat_id, "❌ Уровень должен быть числом от 0 до 12")
        return
    name = ' '.join(args[2:])
    conn, cursor = get_db_for_chat(chat_id)
    cursor.execute('INSERT OR REPLACE INTO level_names (level, name) VALUES (?, ?)', (level, name))
    conn.commit()
    send_message(chat_id, f"✅ Уровень {level} теперь называется: {name}")


def handle_setup(chat_id, from_id, args, reply_msg=None):
    if not can_execute(chat_id, from_id, 'setup'):
        send_message(chat_id, f"⛔ Недостаточно прав! Требуется уровень 12")
        return
    send_message(chat_id, "⚙️ **Быстрая настройка бота**\n\n"
                          "1️⃣ Установите правила: /setrules [текст]\n"
                          "2️⃣ Добавьте администраторов: /админ @username [уровень]\n"
                          "3️⃣ Настройте фильтр: /filter [слово]\n"
                          "4️⃣ Установите приветствие: /welcome [текст]\n"
                          "5️⃣ Настройте названия уровней: /setlvlname [уровень] [название]\n\n"
                          "📊 Посмотреть названия уровней: /lvlnames\n"
                          "🔧 Настроить права команд: /editcmd [команда] [уровень]\n\n"
                          "Бот готов к работе!")


def handle_owner(chat_id, from_id, args, reply_msg=None):
    if not can_execute(chat_id, from_id, 'owner'):
        send_message(chat_id, f"⛔ Недостаточно прав! Требуется уровень 12")
        return
    if len(args) < 2:
        send_message(chat_id, "ℹ️ /owner @username")
        return
    target_id = extract_user_id_from_text(' '.join(args[1:]))
    if not target_id:
        send_message(chat_id, "❌ Пользователь не найден")
        return

    conn, cursor = get_db_for_chat(chat_id)

    # Проверяем текущего владельца
    cursor.execute('SELECT owner_id FROM chat_owner WHERE id = 1')
    current_owner = cursor.fetchone()

    if current_owner and current_owner[0] != from_id:
        send_message(chat_id, "❌ Только текущий владелец может передать права!")
        return

    cursor.execute('INSERT OR REPLACE INTO chat_owner (id, owner_id, is_owner_assigned) VALUES (1, ?, 1)', (target_id,))
    cursor.execute('INSERT OR REPLACE INTO admins (user_id, level) VALUES (?, ?)', (target_id, 12))
    conn.commit()
    send_message(chat_id, f"👑 Права владельца переданы {get_user_link(target_id)}")


def check_message_for_banned_words(chat_id, from_id, text):
    if text.startswith('/') or text.startswith('!'):
        return False

    conn, cursor = get_db_for_chat(chat_id)
    cursor.execute('SELECT word FROM banned_words')
    words = cursor.fetchall()
    for (word,) in words:
        if word.lower() in text.lower():
            add_warn(chat_id, from_id)
            return True
    return False


# ================= ОСНОВНОЙ ЦИКЛ =================

def main():
    print("=" * 50)
    print("🚀 VK БОТ ЗАПУЩЕН")
    print("=" * 50)
    print(f"📌 Сообщество: https://vk.com/club{GROUP_ID}")
    print(f"🔐 Пароль для получения прав: {OWNER_PASSWORD}")
    print("\n📊 Система уровней: 0-12")
    print("📝 Бот готов к работе!")
    print("🛑 Для остановки нажмите Ctrl+C")
    print("=" * 50)

    commands = {
        'пинг': handle_ping, 'ping': handle_ping, 'статус': handle_ping, 'test': handle_ping, 'тест': handle_ping,
        'помощь': handle_help, 'help': handle_help, 'команды': handle_help, 'cmds': handle_help,
        'правила': handle_rules, 'rules': handle_rules,
        'админы': handle_admins, 'admins': handle_admins, 'staff': handle_admins,
        'онлайн': handle_online, 'online': handle_online,
        'стата': handle_stats, 'stats': handle_stats, 'статистика': handle_stats,
        'чатинфо': handle_chatinfo, 'chatinfo': handle_chatinfo, 'очате': handle_chatinfo, 'инфо': handle_chatinfo,
        'info': handle_chatinfo,
        'рандом': handle_roll, 'roll': handle_roll,
        'голосование': handle_vote, 'vote': handle_vote,
        'нлист': handle_nlist, 'nlist': handle_nlist, 'nicklist': handle_nlist,
        'setowner': handle_setowner, 'установитьвладельца': handle_setowner,  # Новая команда
        'мут': handle_mute, 'mute': handle_mute, 'заткнуть': handle_mute,
        'унмут': handle_unmute, 'unmute': handle_unmute, 'разоткнуть': handle_unmute,
        'кик': handle_kick, 'kick': handle_kick, 'исключить': handle_kick,
        'варн': handle_warn, 'warn': handle_warn, 'пред': handle_warn,
        'унварн': handle_unwarn, 'unwarn': handle_unwarn, 'снятьпред': handle_unwarn,
        'варны': handle_warns, 'warns': handle_warns, 'warnlist': handle_warns,
        'сник': handle_snick, 'snick': handle_snick, 'setnick': handle_snick,
        'removenick': handle_removenick, 'рник': handle_removenick,
        'напомни': handle_remind, 'remind': handle_remind,
        'бан': handle_ban, 'ban': handle_ban, 'блок': handle_ban,
        'унбан': handle_unban, 'unban': handle_unban, 'разблок': handle_unban,
        'banlist': handle_banlist,
        'тишина': handle_silence, 'silence': handle_silence,
        'админ': handle_addadmin, 'addadmin': handle_addadmin,
        'фильтр': handle_filter, 'filter': handle_filter,
        'unfilter': handle_unfilter, 'убратьфильтр': handle_unfilter,
        'фильтры': handle_filters, 'filters': handle_filters,
        'welcome': handle_welcome, 'приветствие': handle_welcome,
        'setrules': handle_setrules, 'установитьправила': handle_setrules, 'srules': handle_setrules,
        'clear': handle_clear, 'очистить': handle_clear,
        'purge': handle_purge, 'очиститьпользователя': handle_purge,
        'pin': handle_pin, 'закрепить': handle_pin,
        'unpin': handle_unpin, 'открепить': handle_unpin,
        'gm': handle_gm, 'gamemode': handle_gm, 'иммунитет': handle_gm,
        'editcmd': handle_editcmd, 'настройкакоманд': handle_editcmd,
        'setlvlname': handle_setlvlname, 'установитьназвание': handle_setlvlname,
        'lvlnames': handle_lvlnames, 'списокназваний': handle_lvlnames,
        'setup': handle_setup,
        'owner': handle_owner, 'владелец': handle_owner,
    }

    for event in longpoll.listen():
        try:
            if event.type == VkBotEventType.MESSAGE_NEW:
                msg = event.object.message
                chat_id = msg['peer_id']
                from_id = msg['from_id']
                text = msg.get('text', '').strip()

                if chat_id <= 2000000000:
                    continue

                # Получаем БД для этого чата
                conn, cursor = get_db_for_chat(chat_id)

                # Проверяем мут
                cursor.execute('SELECT is_muted, muted_until FROM users WHERE user_id = ?', (from_id,))
                user_status = cursor.fetchone()
                if user_status and user_status[0] and user_status[1]:
                    muted_until = datetime.fromisoformat(user_status[1])
                    if muted_until > datetime.now():
                        continue
                    else:
                        cursor.execute('UPDATE users SET is_muted = 0, muted_until = NULL WHERE user_id = ?',
                                       (from_id,))
                        conn.commit()

                # Проверяем режим тишины
                cursor.execute('SELECT silent_mode FROM chat_settings WHERE id = 1')
                silent = cursor.fetchone()
                if silent and silent[0]:
                    user_level = get_user_level_in_chat(chat_id, from_id)
                    if user_level < 5:
                        continue

                check_message_for_banned_words(chat_id, from_id, text)

                # Обновляем счётчик сообщений
                cursor.execute('UPDATE users SET messages_count = messages_count + 1 WHERE user_id = ?', (from_id,))
                if cursor.rowcount == 0:
                    cursor.execute('INSERT INTO users (user_id, messages_count) VALUES (?, ?)', (from_id, 1))
                conn.commit()

                # Обрабатываем команды
                if text.startswith('/') or text.startswith('!'):
                    cmd = re.sub(r'^[/!]', '', text.split()[0]).lower()
                    if cmd in commands:
                        args_list = text.split()
                        commands[cmd](chat_id, from_id, args_list, msg)

        except Exception as e:
            print(f"Ошибка: {e}")


if __name__ == "__main__":
    main()
