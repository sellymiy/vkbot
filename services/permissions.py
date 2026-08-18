"""Проверка глобальных/локальных уровней и динамических команд."""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from database.models import User, Conversation, ConversationMember, Level

DEFAULT_LEVELS = [(1, "Пользователь", True), (2, "Администратор", False), (3, "Старший администратор", False),
                  (4, "ЗГА", True), (5, "ГА", True), (6, "Спец. админ", True), (7, "Руководитель", True),
                  (8, "Разработчик", True), (9, "Сооснователь", True), (10, "Основатель", True)]

async def seed_levels(session: AsyncSession):
    if not (await session.scalar(select(Level.id).limit(1))):
        session.add_all([Level(number=n, name=name, is_global=global_) for n, name, global_ in DEFAULT_LEVELS])

async def ensure_user(session, vk_id: int) -> User:
    user = await session.scalar(select(User).where(User.vk_id == vk_id))
    if not user:
        user = User(vk_id=vk_id)
        session.add(user)
        await session.flush()
    return user

async def ensure_conversation(session, peer_id: int) -> Conversation:
    conversation = await session.scalar(select(Conversation).where(Conversation.peer_id == peer_id))
    if not conversation:
        conversation = Conversation(peer_id=peer_id)
        session.add(conversation)
        await session.flush()
    return conversation

async def get_level(session, user_id: int, peer_id: int) -> int:
    user = await ensure_user(session, user_id)
    conversation = await ensure_conversation(session, peer_id)
    member = await session.scalar(select(ConversationMember).where(ConversationMember.user_id == user.id,
        ConversationMember.conversation_id == conversation.id))
    if member is None:
        member = ConversationMember(user_id=user.id, conversation_id=conversation.id)
        session.add(member)
    # Старые записи базы могли содержать NULL вместо уровня.
    global_level = user.global_level or 1
    local_level = member.local_level or 1
    if user.global_level is None:
        user.global_level = global_level
    if member.local_level is None:
        member.local_level = local_level
    return max(global_level, local_level)

async def allowed(session, user_id: int, peer_id: int, command: str, minimum: int) -> bool:
    user = await ensure_user(session, user_id)
    if user.is_root:
        return True
    level = await get_level(session, user_id, peer_id)
    custom = await session.scalars(select(Level).where(Level.number <= level))
    for item in custom:
        if command.lstrip("/") in (item.commands or []):
            return True
    return level >= minimum
