"""Сроки наказаний и операции с банами/мутами."""
from datetime import datetime, timedelta
import re
from sqlalchemy import select
from database.models import Ban, Mute, User

def parse_duration(value: str) -> datetime | None:
    """Понимает 1d2h30m, русское 'навсегда' и возвращает дату окончания."""
    value = value.lower().strip()
    if value in {"навсегда", "навсегда!", "perm", "permanent"}:
        return None
    matches = re.findall(r"(\d+)\s*([dhm])", value)
    if not matches or "".join(n + u for n, u in matches) not in value.replace(" ", ""):
        raise ValueError("Срок должен быть вида 1d, 2h, 30m или навсегда")
    seconds = sum(int(number) * {"d": 86400, "h": 3600, "m": 60}[unit] for number, unit in matches)
    return datetime.utcnow() + timedelta(seconds=seconds)

async def active_ban(session, vk_id: int, conversation_id: int | None = None):
    user = await session.scalar(select(User).where(User.vk_id == vk_id))
    if not user:
        return None
    query = select(Ban).where(Ban.user_id == user.id, Ban.is_active.is_(True),
        (Ban.expires_at.is_(None) | (Ban.expires_at > datetime.utcnow())))
    bans = (await session.scalars(query)).all()
    return next((ban for ban in bans if ban.is_global or ban.conversation_id == conversation_id), None)

async def active_mute(session, vk_id: int, conversation_id: int):
    user = await session.scalar(select(User).where(User.vk_id == vk_id))
    if not user:
        return None
    return await session.scalar(select(Mute).where(Mute.user_id == user.id, Mute.conversation_id == conversation_id,
        Mute.is_active.is_(True), (Mute.expires_at.is_(None) | (Mute.expires_at > datetime.utcnow()))))
