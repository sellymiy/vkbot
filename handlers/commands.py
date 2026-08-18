"""Команды SAINT CRMP | BOT."""
import logging
import re
from datetime import datetime

from sqlalchemy import delete, func, or_, select
from vkbottle.bot import Message

from database.models import (Ban, Conversation, ConversationMember, Level,
                             MonitoringList, Mute, PointHistory, Report, User, Warn)
from services.permissions import allowed, ensure_conversation, ensure_user, get_level
from services.punishments import active_ban, active_mute, parse_duration

log = logging.getLogger(__name__)

COMMANDS = {
    "mypoints": "твои баллы и история", "mywarns": "твои предупреждения", "mynick": "твой ник в беседе",
    "search": "поиск ника в беседе или глобально", "report": "отправить баг или предложение", "online": "онлайн Saint",
    "cmdinfo": "показать алиасы команды", "help": "список доступных команд", "onlinehelp": "помощь по онлайну и спискам",
    "info": "информация о беседе", "staff": "список админов", "staffall": "все глобальные и локальные админы",
    "get": "информация о пользователе", "nicklist": "список ников беседы", "getnick": "ник пользователя",
    "setnick": "установить ник", "removenick": "удалить ник", "kick": "кикнуть пользователя",
    "warn": "выдать предупреждение", "unwarn": "снять предупреждение", "owarn": "выдать устное предупреждение",
    "ounwarn": "снять устное предупреждение", "mute": "выдать мут", "unmute": "снять мут",
    "ban": "забанить в беседе", "unban": "снять бан в беседе", "bans": "список банов",
    "getban": "проверить бан пользователя", "warns": "список пользователей с варнами", "warnings": "история предупреждений",
    "silence": "режим тишины в беседе", "reportlist": "список репортов", "point": "выдать баллы",
    "unpoint": "забрать баллы", "gban": "глобальный бан", "ungban": "снять глобальный бан",
    "gkick": "глобальный кик", "vg": "сообщение в беседы", "msg": "сообщение всем в текущей беседе",
    "welcome": "настройка приветствия", "atools": "ссылка/текст ATools", "monitor": "мониторинг серверов",
    "onlinelist": "список игроков онлайн", "aadm": "онлайн админов", "addadmin": "выдать уровень админки",
    "aadmdel": "удалить админа из списка", "aadmlist": "список админов мониторинга", "leaders": "онлайн лидеров",
    "leadersadd": "добавить лидера", "leadersdel": "удалить лидера", "leaderslist": "список лидеров",
    "media": "онлайн медиа", "mediaadd": "добавить медиа", "mediadel": "удалить медиа", "medialist": "список медиа",
    "supports": "онлайн саппортов", "supportsadd": "добавить саппорта", "supportsdel": "удалить саппорта",
    "supportslist": "список саппортов", "setname": "название беседы",
    "setid": "изменить ID беседы", "ginfo": "список бесед", "gdel": "удалить беседу из базы",
    "botban": "заблокировать беседу для бота", "unbotban": "разблокировать беседу", "botbanlist": "список блокировок бесед",
    "setroot": "выдать root", "delroot": "забрать root", "roots": "список root", "lvllist": "список уровней админки",
    "setlvlname": "переименовать уровень", "addlvl": "добавить уровень", "setlvl": "изменить номер уровня",
    "dellvl": "удалить уровень", "editlvlcmd": "выдать/забрать команду уровню", "lvlcmdlist": "команды выбранного уровня",
    "setgloballvl": "сделать уровень локальным/глобальным", "maintenance": "включить техработы",
    "maintenanceoff": "выключить техработы", "isonline": "проверить игрока на сервере", "lnlist": "ники другой беседы",
    "lwarn": "предупреждение в другой беседе", "lunwarn": "снять предупреждение в другой беседе",
    "lwarns": "варны другой беседы", "lwarnings": "история другой беседы", "lowarn": "устное предупреждение в другой беседе",
    "lounwarn": "снять устное в другой беседе", "lban": "бан в другой беседе", "lunban": "разбанить в другой беседе",
    "lbans": "баны другой беседы", "lmute": "мут в другой беседе", "lunmute": "снять мут в другой беседе",
    "lhelp": "локализованные команды", "lsetadmin": "локальный уровень в другой беседе", "nlistclear": "очистить ники",
    "aadmclear": "очистить админов", "supportsclear": "очистить саппортов", "leadersclear": "очистить лидеров",
    "mediaclear": "очистить медиа", "nlistsyns": "синхронизировать ники", "time": "время и срок мута",
    "quit": "выйти из беседы", "timeban": "запретить /time", "timeunban": "разрешить /time",
    "timebanlist": "запреты /time",
}

MIN_LEVEL = {
    "kick": 2, "warn": 2, "unwarn": 2, "owarn": 2, "ounwarn": 2, "mute": 2, "unmute": 2,
    "silence": 3, "ban": 5, "unban": 5, "point": 4, "unpoint": 4, "reportlist": 4,
    "gban": 9, "ungban": 9, "gkick": 9, "vg": 7, "msg": 4,
    "setname": 7, "setid": 7, "ginfo": 7, "gdel": 9, "botban": 9, "unbotban": 9,
    "botbanlist": 9, "setroot": 10, "delroot": 10, "roots": 9, "setlvlname": 10,
    "addlvl": 10, "setlvl": 10, "dellvl": 10, "editlvlcmd": 10, "setgloballvl": 10,
    "maintenance": 10, "maintenanceoff": 10, "quit": 9, "timeban": 4, "timeunban": 4,
    "lwarn": 4, "lunwarn": 4, "lowarn": 4, "lounwarn": 4, "lban": 5, "lunban": 5,
    "lmute": 4, "lunmute": 4, "lsetadmin": 8,
    "addadmin": 8, "aadmdel": 4, "leadersadd": 4, "leadersdel": 4,
    "mediaadd": 4, "mediadel": 4, "supportsadd": 4, "supportsdel": 4,
    "aadmclear": 7, "leadersclear": 7, "mediaclear": 7, "supportsclear": 7,
    "nlistsyns": 4, "welcome": 7, "atools": 7, "nlistclear": 7,
}

CATEGORIES = {"aadm": "admin", "leaders": "leader", "media": "media", "supports": "support"}
ALIASES = {
    "онлайн": "online", "ник": "mynick", "помощь": "help", "размут": "unmute",
    "aadmadd": "addadmin", "addmadd": "addadmin",
}

def vk_id(message: Message, text: str = "") -> int:
    if message.reply_message and message.reply_message.from_id:
        return int(message.reply_message.from_id)
    match = re.search(r"\[id(\d+)\|[^]]+]|(?:^|\s)(\d+)(?:\s|$)", text)
    if not match:
        raise ValueError("Ответьте на сообщение или укажите VK ID")
    return int(match.group(1) or match.group(2))

def clean_target(text: str) -> str:
    return re.sub(r"^\s*(?:\[id\d+\|[^]]+]|\d+)\s*", "", text).strip()

def settings_set(conversation: Conversation, key: str, value):
    data = dict(conversation.settings or {}); data[key] = value; conversation.settings = data

def expires_text(value):
    return "навсегда" if value is None else value.strftime("%d.%m.%Y %H:%M")

async def send_long(message: Message, text: str):
    while text:
        cut = min(3800, len(text))
        if cut < len(text): cut = text.rfind("\n", 0, cut) or cut
        await message.answer(text[:cut]); text = text[cut:].lstrip()

async def get_conversation(session, custom_id: str) -> Conversation:
    if not custom_id.isdigit(): raise ValueError("Укажите числовой ID беседы")
    item = await session.scalar(select(Conversation).where(Conversation.custom_id == int(custom_id)))
    if not item: raise ValueError("Беседа с таким ID не найдена")
    return item

async def member_for(session, user: User, conversation: Conversation):
    member = await session.scalar(select(ConversationMember).where(ConversationMember.user_id == user.id,
        ConversationMember.conversation_id == conversation.id))
    if not member:
        member = ConversationMember(user_id=user.id, conversation_id=conversation.id, local_level=1)
        session.add(member); await session.flush()
    return member

async def require(session, message, command):
    if await allowed(session, message.from_id, message.peer_id, command, MIN_LEVEL.get(command, 1)): return
    raise PermissionError("Недостаточно прав")

async def kick(api, peer_id: int, user_id: int):
    if peer_id < 2_000_000_000: raise ValueError("Команда доступна только в беседе")
    await api.messages.remove_chat_user(chat_id=peer_id - 2_000_000_000, member_id=user_id)

async def register_handlers(labeler, factory, samp):
    @labeler.message(regex=r"^/([a-zа-яё0-9_]+)(?:\s+([\s\S]*))?$")
    async def dispatch(message: Message):
        # В разных версиях vkbottle regex-параметр может быть tuple, поэтому
        # разбираем исходный текст самостоятельно и не используем match.group().
        parts = (message.text or "").strip().split(maxsplit=1)
        command_name = parts[0][1:].lower() if parts and parts[0].startswith("/") else ""
        command = ALIASES.get(command_name, command_name)
        args = parts[1].strip() if len(parts) > 1 else ""
        if command not in COMMANDS:
            await message.answer("❌ Неизвестная команда. Используйте /help")
            return
        try:
            # VK может передать @domain как обычный текст, а не [id123|name].
            domain = re.match(r"^@([A-Za-z0-9_.]+)(?=\s|$)", args)
            if domain:
                profiles = await message.ctx_api.users.get(user_ids=[domain.group(1)])
                if not profiles:
                    raise ValueError("Пользователь VK не найден")
                args = re.sub(r"^@[A-Za-z0-9_.]+", str(profiles[0].id), args, count=1)
            async with factory() as session:
                actor = await ensure_user(session, message.from_id)
                conv = await ensure_conversation(session, message.peer_id)
                if conv.is_bot_banned and not actor.is_root:
                    raise PermissionError("Эта беседа заблокирована для бота")
                if (conv.settings or {}).get("maintenance") and not actor.is_root:
                    raise PermissionError("В боте включены технические работы")
                if await active_ban(session, message.from_id, conv.id) and command not in {"getban", "time"}:
                    raise PermissionError("У вас активный бан")
                if await active_mute(session, message.from_id, conv.id) and command not in {"unmute", "getban", "time"}:
                    raise PermissionError("У вас активный мут")
                await require(session, message, command)
                result = await execute(command, args, message, session, actor, conv, samp)
                await session.commit()
            if result: await send_long(message, result)
        except PermissionError as exc: await message.answer(f"⛔ {exc}")
        except ValueError as exc: await message.answer(f"❌ {exc}")
        except Exception as exc:
            log.exception("Ошибка команды /%s", command)
            await message.answer(f"❌ Ошибка выполнения /{command}: {exc}")

async def execute(cmd, args, message, session, actor, conv, samp):
    if cmd == "help":
        number = await get_level(session, message.from_id, message.peer_id)
        level = await session.scalar(select(Level).where(Level.number == number))
        available = [f"/{name} — {desc}" for name, desc in COMMANDS.items() if MIN_LEVEL.get(name, 1) <= number or actor.is_root]
        return f"SAINT CRMP | BOT — доступные команды\nВаша роль — {level.name if level else 'Пользователь'} ({number}lvl)\n\n" + "\n".join(available)
    if cmd == "cmdinfo":
        name = args.lstrip("/").lower(); canonical = ALIASES.get(name, name)
        if canonical not in COMMANDS: raise ValueError("Команда не найдена")
        aliases = [f"/{key}" for key, value in ALIASES.items() if value == canonical]
        return f"/{canonical} — {COMMANDS[canonical]}\nАлиасы: {', '.join(aliases) or 'нет'}"
    if cmd == "time":
        blocked = set((conv.settings or {}).get("time_bans", []))
        if message.from_id in blocked: raise PermissionError("Команда /time для вас запрещена")
        mute = await session.scalar(select(Mute).where(Mute.user_id == actor.id, Mute.conversation_id == conv.id, Mute.is_active.is_(True)))
        suffix = f"\nМут до: {expires_text(mute.expires_at)}" if mute else ""
        return f"🕒 {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}{suffix}"
    if cmd in {"online", "onlinelist", "monitor", "isonline", "onlinehelp"}:
        if cmd == "onlinehelp": return "/online — сводка\n/onlinelist — игроки\n/isonline <ник> — проверка ника\n/aadm, /leaders, /media, /supports — списки"
        info = await samp.info()
        if cmd == "isonline":
            found = next((p for p in info.players if p.name.lower() == args.lower()), None)
            return f"✅ {found.name} онлайн, score: {found.score}" if found else f"❌ {args or 'Игрок'} не найден"
        if cmd == "onlinelist":
            players = "\n".join(f"[{p.player_id}] {p.name} (score: {p.score})" for p in info.players) or "Игроков нет"
            return f"SAINT ONLINE LIST\n🌐 {samp.host}:{samp.port}\n🖥️ {info.hostname}\n📊 {info.online}/{info.max_players}\n\n{players}"
        return f"SAINT ONLINE\n🌐 {samp.host}:{samp.port}\n🖥️ {info.hostname}\n📊 Онлайн: {info.online}/{info.max_players}\n📶 Ping: {info.ping} ms"
    if cmd == "info": return f"ℹ️ Информация о беседе:\n🏷️ {conv.title or 'Без названия'} [ID: {conv.custom_id or 'не задан'}]\n🧩 peer_id: {conv.peer_id}"
    if cmd == "report":
        if not args: raise ValueError("Использование: /report <текст>")
        session.add(Report(user_id=actor.id, text=args)); return "✅ Репорт принят"
    if cmd == "reportlist":
        rows = (await session.execute(select(Report, User.vk_id).join(User).order_by(Report.id.desc()).limit(30))).all()
        return "📨 Репорты:\n" + ("\n".join(f"#{x.id} [{x.status}] VK ID {uid}: {x.text}" for x, uid in rows) or "Нет репортов")
    if cmd in {"mynick", "setnick", "removenick", "getnick", "nicklist", "search", "nlistclear"}:
        member = await member_for(session, actor, conv)
        if cmd == "mynick": return f"Ваш ник: {member.local_nickname or 'не установлен'}"
        if cmd == "setnick":
            if not args: raise ValueError("Использование: /setnick [@пользователь] <ник>")
            target_match = re.match(r"^(?:\[id\d+\|[^]]+]|\d+)\s+(.+)$", args)
            target = actor
            nickname = args
            if target_match:
                target = await ensure_user(session, vk_id(message, args))
                nickname = target_match.group(1).strip()
                if target.id != actor.id and not await allowed(session, message.from_id, message.peer_id, "setnick", 2):
                    raise PermissionError("Для установки чужого ника нужен 2 уровень")
            if not nickname: raise ValueError("Укажите ник")
            target_member = await member_for(session, target, conv)
            target_member.local_nickname = nickname[:80]
            target.nickname = nickname[:80]
            return f"✅ Ник [id{target.vk_id}|пользователя] установлен: {nickname[:80]}"
        if cmd == "removenick": member.local_nickname = None; return "✅ Ник удалён"
        if cmd == "nlistclear":
            await session.execute(select(ConversationMember).where(ConversationMember.conversation_id == conv.id))
            members = (await session.scalars(select(ConversationMember).where(ConversationMember.conversation_id == conv.id))).all()
            for item in members: item.local_nickname = None
            return "✅ Список ников очищен"
        if cmd == "getnick":
            user = await ensure_user(session, vk_id(message, args)); item = await member_for(session, user, conv)
            return f"Ник [id{user.vk_id}|пользователя]: {item.local_nickname or user.nickname or 'не установлен'}"
        if cmd == "nicklist":
            rows = (await session.execute(select(User.vk_id, ConversationMember.local_nickname).join(ConversationMember).where(ConversationMember.conversation_id == conv.id, ConversationMember.local_nickname.is_not(None)))).all()
            return "📋 Ники беседы:\n" + ("\n".join(f"[id{uid}|{nick}]" for uid, nick in rows) or "Список пуст")
        if not args: raise ValueError("Укажите часть ника")
        pattern = f"%{args}%"; query = select(User.vk_id, ConversationMember.local_nickname, Conversation.peer_id).join(ConversationMember).join(Conversation).where(ConversationMember.local_nickname.ilike(pattern))
        if "global" not in args.lower(): query = query.where(Conversation.id == conv.id)
        rows = (await session.execute(query.limit(30))).all()
        return "🔎 Результаты:\n" + ("\n".join(f"[id{uid}|{nick}] — peer {peer}" for uid, nick, peer in rows) or "Ничего не найдено")
    if cmd in {"mypoints", "point", "unpoint"}:
        if cmd == "mypoints":
            history = (await session.scalars(select(PointHistory).where(PointHistory.user_id == actor.id).order_by(PointHistory.id.desc()).limit(10))).all()
            return f"⭐ Баллы: {actor.points or 0}\n" + ("\n".join(f"{x.amount:+} — {x.reason}" for x in history) or "История пуста")
        target = await ensure_user(session, vk_id(message, args)); rest = clean_target(args).split(maxsplit=1)
        if not rest or not rest[0].lstrip("-").isdigit(): raise ValueError(f"Использование: /{cmd} <user> <количество> [причина]")
        amount = abs(int(rest[0])) * (1 if cmd == "point" else -1); target.points = (target.points or 0) + amount
        session.add(PointHistory(user_id=target.id, moderator_id=message.from_id, amount=amount, reason=rest[1] if len(rest)>1 else ""))
        return f"✅ Баллы [id{target.vk_id}|пользователя]: {target.points}"
    if cmd in {"get", "staff", "staffall", "aadmlist"}:
        if cmd == "get":
            target = await ensure_user(session, vk_id(message, args)); item = await member_for(session, target, conv)
            return f"👤 VK ID: {target.vk_id}\nНик: {item.local_nickname or target.nickname or 'нет'}\nGlobal lvl: {target.global_level or 1}\nLocal lvl: {item.local_level or 1}\nБаллы: {target.points or 0}\nRoot: {'да' if target.is_root else 'нет'}"
        query = select(
            User.vk_id,
            User.nickname,
            User.global_level,
            ConversationMember.local_level,
            ConversationMember.local_nickname,
        ).outerjoin(
            ConversationMember,
            (ConversationMember.user_id == User.id) &
            (ConversationMember.conversation_id == conv.id),
        ).where(or_(User.global_level > 1, ConversationMember.local_level > 1))
        rows = (await session.execute(query)).all()
        level_rows = (await session.scalars(select(Level))).all()
        level_names = {item.number: item.name for item in level_rows}
        formatted = []
        for uid, user_nick, global_level, local_level, local_nick in rows:
            level_number = max(global_level or 1, local_level or 1)
            display_name = local_nick or user_nick or f"VK ID {uid}"
            level_name = level_names.get(level_number, "Без названия")
            formatted.append(f"[id{uid}|{display_name}] — {level_number} lvl ({level_name})")
        return "👮 Администрация:\n" + ("\n".join(formatted) or "Список пуст")
    if cmd in {"warn", "owarn", "unwarn", "ounwarn", "mywarns", "warns", "warnings"}:
        if cmd == "mywarns":
            rows = (await session.scalars(select(Warn).where(Warn.user_id == actor.id, Warn.conversation_id == conv.id, Warn.is_active.is_(True)))).all()
            return "⚠️ Ваши предупреждения:\n" + ("\n".join(f"#{x.id} {x.reason}" for x in rows) or "Нет")
        if cmd in {"warns", "warnings"}:
            query = select(Warn, User.vk_id).join(User).where(Warn.conversation_id == conv.id)
            if cmd == "warns": query = query.where(Warn.is_active.is_(True))
            rows = (await session.execute(query.order_by(Warn.id.desc()).limit(50))).all()
            return "⚠️ Предупреждения:\n" + ("\n".join(f"#{w.id} [id{uid}|user] {'устное' if w.is_verbal else 'warn'}: {w.reason} ({'активно' if w.is_active else 'снято'})" for w, uid in rows) or "Нет")
        target = await ensure_user(session, vk_id(message, args))
        if cmd in {"warn", "owarn"}:
            session.add(Warn(user_id=target.id, conversation_id=conv.id, moderator_id=message.from_id, reason=clean_target(args) or "Не указана", is_verbal=cmd=="owarn")); return "✅ Предупреждение выдано"
        warning = await session.scalar(select(Warn).where(Warn.user_id == target.id, Warn.conversation_id == conv.id, Warn.is_verbal.is_(cmd=="ounwarn"), Warn.is_active.is_(True)).order_by(Warn.id.desc()))
        if not warning: raise ValueError("Активное предупреждение не найдено")
        warning.is_active = False; return "✅ Предупреждение снято"
    if cmd in {"mute", "unmute", "ban", "unban", "gban", "ungban", "getban", "bans"}:
        if cmd == "bans":
            rows = (await session.execute(select(Ban, User.vk_id).join(User).where(Ban.conversation_id == conv.id, Ban.is_active.is_(True)))).all()
            return "⛔ Баны:\n" + ("\n".join(f"#{b.id} [id{uid}|user] до {expires_text(b.expires_at)}: {b.reason}" for b,uid in rows) or "Нет")
        target = await ensure_user(session, vk_id(message, args))
        if cmd == "getban":
            rows = (await session.scalars(select(Ban).where(Ban.user_id == target.id, Ban.is_active.is_(True)))).all()
            return "⛔ Баны:\n" + ("\n".join(f"#{x.id} {'global' if x.is_global else 'local'} до {expires_text(x.expires_at)}: {x.reason}" for x in rows) or "Нет")
        if cmd in {"unmute", "unban", "ungban"}:
            model = Mute if cmd == "unmute" else Ban
            query = select(model).where(model.user_id == target.id, model.is_active.is_(True))
            if model is Mute: query = query.where(Mute.conversation_id == conv.id)
            elif cmd == "ungban": query = query.where(Ban.is_global.is_(True))
            else: query = query.where(Ban.conversation_id == conv.id, Ban.is_global.is_(False))
            rows = (await session.scalars(query)).all()
            for row in rows: row.is_active = False
            return f"✅ Снято записей: {len(rows)}"
        rest = clean_target(args).split(maxsplit=2); duration = rest[0] if rest else "навсегда"
        expires = parse_duration(duration); reason = " ".join(rest[1:]) if len(rest)>1 else "Не указана"
        if cmd == "mute": session.add(Mute(user_id=target.id, conversation_id=conv.id, moderator_id=message.from_id, expires_at=expires, reason=reason))
        else: session.add(Ban(user_id=target.id, conversation_id=None if cmd=="gban" else conv.id, moderator_id=message.from_id, expires_at=expires, reason=reason, is_global=cmd=="gban"))
        return "✅ Наказание выдано"
    if cmd in {"kick", "gkick"}:
        target = vk_id(message, args)
        if cmd == "kick": await kick(message.ctx_api, conv.peer_id, target); return "✅ Пользователь исключён"
        conversations = (await session.scalars(select(Conversation))).all(); done = 0
        for item in conversations:
            try: await kick(message.ctx_api, item.peer_id, target); done += 1
            except Exception: pass
        return f"✅ Исключён из бесед: {done}"
    return await execute_admin(cmd, args, message, session, actor, conv, samp)

async def execute_admin(cmd, args, message, session, actor, conv, samp):
    if cmd in {"addadmin", "setroot", "delroot", "roots"}:
        if cmd == "roots":
            rows = (await session.scalars(select(User).where(User.is_root.is_(True)))).all()
            return "🔑 Root:\n" + ("\n".join(f"[id{x.vk_id}|Пользователь]" for x in rows) or "Нет")
        target = await ensure_user(session, vk_id(message,args))
        if cmd == "setroot": target.is_root=True; target.global_level=10; return "✅ Root выдан"
        if cmd == "delroot": target.is_root=False; return "✅ Root снят"
        # При ответе на сообщение аргументы содержат только уровень: /addadmin 9.
        # Без reply используется полный формат: /addadmin @user 9.
        rest = args.split() if message.reply_message else clean_target(args).split()
        if not rest or not rest[0].isdigit(): raise ValueError(f"Использование: /addadmin <user> <lvl> или ответом /addadmin <lvl>")
        level=int(rest[0]); definition=await session.scalar(select(Level).where(Level.number==level))
        if not definition: raise ValueError("Уровень не найден")
        target_member = await member_for(session, target, conv)
        if definition.is_global:
            target.global_level = level
            target_member.local_level = max(target_member.local_level or 1, level)
        else:
            target_member.local_level = level
        return "✅ Уровень выдан"
    if cmd in {"lvllist","lvlcmdlist","setlvlname","addlvl","setlvl","dellvl","editlvlcmd","setgloballvl"}:
        if cmd=="lvllist":
            rows=(await session.scalars(select(Level).order_by(Level.number))).all(); return "📋 Уровни:\n"+"\n".join(f"{x.number} — {x.name} ({'global' if x.is_global else 'local'}, команд: {len(x.commands or [])})" for x in rows)
        parts=args.split(maxsplit=2)
        if not parts or not parts[0].isdigit(): raise ValueError("Первым аргументом укажите уровень")
        level=await session.scalar(select(Level).where(Level.number==int(parts[0])))
        if cmd=="addlvl":
            if level: raise ValueError("Уровень уже существует")
            session.add(Level(number=int(parts[0]),name=parts[1] if len(parts)>1 else f"Уровень {parts[0]}",is_global=False)); return "✅ Уровень добавлен"
        if not level: raise ValueError("Уровень не найден")
        if cmd=="lvlcmdlist": return f"Команды {level.number}: "+(", ".join(level.commands or []) or "нет")
        if cmd=="setlvlname": level.name=" ".join(parts[1:]); return "✅ Название изменено"
        if cmd=="dellvl": await session.delete(level); return "✅ Уровень удалён"
        if cmd=="setlvl": level.number=int(parts[1]); return "✅ Номер изменён"
        if cmd=="setgloballvl": level.is_global=(parts[1].lower() in {"global","глобальный","1","on"}); return "✅ Тип уровня изменён"
        command=parts[1].lstrip("/") if len(parts)>1 else ""; commands=list(level.commands or [])
        if command in commands: commands.remove(command); action="забрана"
        else: commands.append(command); action="выдана"
        level.commands=commands; return f"✅ Команда {action}"
    if cmd in {"setname","setid","ginfo","gdel","botban","unbotban","botbanlist","maintenance","maintenanceoff","welcome","atools","silence"}:
        if cmd=="setname": conv.title=args[:200]; return "✅ Название установлено"
        if cmd=="setid": conv.custom_id=int(args); return "✅ ID установлен"
        if cmd=="ginfo":
            rows=(await session.scalars(select(Conversation).order_by(Conversation.custom_id))).all(); return "💬 Беседы:\n"+"\n".join(f"{x.custom_id or '-'} — {x.title or 'Без названия'} ({x.peer_id})" for x in rows)
        if cmd=="botbanlist":
            rows=(await session.scalars(select(Conversation).where(Conversation.is_bot_banned.is_(True)))).all(); return "⛔ Блокировки:\n"+("\n".join(str(x.peer_id) for x in rows) or "Нет")
        if cmd in {"maintenance","maintenanceoff"}: settings_set(conv,"maintenance",cmd=="maintenance"); return "✅ Режим изменён"
        if cmd=="welcome": settings_set(conv,"welcome",args); return "✅ Приветствие сохранено"
        if cmd=="atools":
            if args: settings_set(conv,"atools",args); return "✅ ATools сохранён"
            return (conv.settings or {}).get("atools","ATools не настроен")
        if cmd=="silence": settings_set(conv,"silence",not (conv.settings or {}).get("silence",False)); return "✅ Режим тишины переключён"
        target=conv if not args else await get_conversation(session,args.split()[0])
        if cmd=="gdel": await session.delete(target); return "✅ Беседа удалена из базы"
        target.is_bot_banned=cmd=="botban"; return "✅ Статус беседы изменён"
    if cmd in {"vg","msg"}:
        if cmd=="msg": await message.ctx_api.messages.send(peer_id=conv.peer_id,random_id=0,message=f"@all {args}"); return None
        destination,text=(args.split(maxsplit=1)+[""])[:2]
        rows=(await session.scalars(select(Conversation))).all() if destination in {"all","все","ку"} else [await get_conversation(session,x) for x in destination.split(",")]
        sent=0
        for item in rows:
            try: await message.ctx_api.messages.send(peer_id=item.peer_id,random_id=0,message=text); sent+=1
            except Exception: pass
        return f"✅ Отправлено в бесед: {sent}"
    if cmd in {"aadm","leaders","media","supports","aadmlist","leaderslist","medialist","supportslist","leadersadd","mediaadd","supportsadd","aadmdel","leadersdel","mediadel","supportsdel","aadmclear","leadersclear","mediaclear","supportsclear","nlistsyns"}:
        base=next((key for key in CATEGORIES if cmd.startswith(key)),None)
        if cmd=="nlistsyns":
            rows=(await session.execute(select(User.id,ConversationMember.local_nickname).join(ConversationMember).where(ConversationMember.conversation_id==conv.id,ConversationMember.local_nickname.is_not(None)))).all(); existing=set((await session.scalars(select(MonitoringList.samp_nick).where(MonitoringList.conversation_id==conv.id))).all())
            for uid,nick in rows:
                if nick not in existing: session.add(MonitoringList(conversation_id=conv.id,user_id=uid,category="admin",samp_nick=nick))
            return "✅ Ники синхронизированы"
        category=CATEGORIES[base]
        if cmd.endswith("clear"): await session.execute(delete(MonitoringList).where(MonitoringList.conversation_id==conv.id,MonitoringList.category==category)); return "✅ Список очищен"
        if cmd.endswith("add"):
            target=await ensure_user(session,vk_id(message,args)); nick=clean_target(args) or target.nickname
            if not nick: raise ValueError("Укажите ник после пользователя")
            session.add(MonitoringList(conversation_id=conv.id,user_id=target.id,category=category,samp_nick=nick)); return "✅ Добавлено"
        if cmd.endswith("del"):
            nick=clean_target(args) or args; result=await session.execute(delete(MonitoringList).where(MonitoringList.conversation_id==conv.id,MonitoringList.category==category,MonitoringList.samp_nick==nick)); return f"✅ Удалено: {result.rowcount}"
        rows=(await session.scalars(select(MonitoringList).where(MonitoringList.conversation_id==conv.id,MonitoringList.category==category))).all()
        if cmd.endswith("list"): return "📋 Список:\n"+("\n".join(x.samp_nick for x in rows) or "Пуст")
        info=await samp.info(); names={p.name.lower():p for p in info.players}; online=[names[x.samp_nick.lower()] for x in rows if x.samp_nick.lower() in names]
        return "🟢 Онлайн:\n"+("\n".join(f"{x.name} (score: {x.score})" for x in online) or "Никого")
    if cmd in {"timeban","timeunban","timebanlist"}:
        values=set((conv.settings or {}).get("time_bans",[]))
        if cmd=="timebanlist": return "⏱ Запрет /time:\n"+("\n".join(f"[id{x}|user]" for x in values) or "Нет")
        target=vk_id(message,args); values.add(target) if cmd=="timeban" else values.discard(target); settings_set(conv,"time_bans",list(values)); return "✅ Список обновлён"
    if cmd in {"lnlist","lwarn","lunwarn","lwarns","lwarnings","lowarn","lounwarn","lban","lunban","lbans","lmute","lunmute","lsetadmin"}:
        parts=args.split(maxsplit=1); target_conv=await get_conversation(session,parts[0]); tail=parts[1] if len(parts)>1 else ""
        mapped={"lnlist":"nicklist","lwarn":"warn","lunwarn":"unwarn","lwarns":"warns","lwarnings":"warnings","lowarn":"owarn","lounwarn":"ounwarn","lban":"ban","lunban":"unban","lbans":"bans","lmute":"mute","lunmute":"unmute","lsetadmin":"addadmin"}[cmd]
        original=message.peer_id; message.peer_id=target_conv.peer_id
        try: return await execute(mapped,tail,message,session,actor,target_conv,samp)
        finally: message.peer_id=original
    if cmd=="lhelp": return "Локальные команды: /lnlist /lwarn /lunwarn /lwarns /lwarnings /lowarn /lounwarn /lban /lunban /lbans /lmute /lunmute /lsetadmin"
    if cmd=="quit":
        if conv.peer_id < 2_000_000_000: raise ValueError("Команда доступна только в беседе")
        # Для выхода сообщества VK принимает его отрицательный ID как member_id.
        from config import settings
        await kick(message.ctx_api, conv.peer_id, -settings.community_id)
        return "✅ Бот вышел из беседы"
    raise ValueError("Команда пока не поддерживается")
