"""Точка входа SAINT CRMP | BOT."""
import asyncio
import logging
from vkbottle import Bot
from sqlalchemy import update
from config import settings
from database.db import make_database, init_db
from database.models import User, ConversationMember
from services.permissions import seed_levels
from services.samp import SampQuery
from handlers.commands import register_handlers
from services.permissions import ensure_user

logging.basicConfig(level=getattr(logging, settings.log_level.upper(), logging.INFO), format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("saint_crmp_bot")

async def main():
    if not settings.vk_token: raise RuntimeError("Не задан VK_TOKEN в .env")
    engine, factory = make_database(settings.database_url); await init_db(engine)
    async with factory() as session:
        # Исправляем NULL в уже существующей SQLite-базе до обработки команд.
        await session.execute(update(User).where(User.global_level.is_(None)).values(global_level=1))
        await session.execute(update(User).where(User.points.is_(None)).values(points=0))
        await session.execute(update(User).where(User.is_root.is_(None)).values(is_root=False))
        await session.execute(update(ConversationMember).where(ConversationMember.local_level.is_(None)).values(local_level=1))
        await seed_levels(session)
        for owner_id in settings.owner_ids:
            owner = await ensure_user(session, owner_id)
            owner.is_root = True
            owner.global_level = 10
        await session.commit()
    bot = Bot(settings.vk_token); samp = SampQuery(settings.samp_host, settings.samp_port, settings.samp_timeout)

    await register_handlers(bot.labeler, factory, samp)
    log.info("SAINT CRMP | BOT запускается")
    try: await bot.run_polling()
    finally: await engine.dispose()

if __name__ == "__main__": asyncio.run(main())
