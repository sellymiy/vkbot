"""Настройки приложения. Секреты берутся только из переменных окружения."""
from dataclasses import dataclass
import os
from dotenv import load_dotenv

load_dotenv()

@dataclass(frozen=True)
class Settings:
    vk_token: str = os.getenv("VK_TOKEN", "")
    database_url: str = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./saint_crmp_bot.db")
    samp_host: str = os.getenv("SAMP_HOST", "185.207.214.14")
    samp_port: int = int(os.getenv("SAMP_PORT", "3561"))
    samp_timeout: float = float(os.getenv("SAMP_TIMEOUT", "5"))
    community_id: int = int(os.getenv("COMMUNITY_ID", "238315078"))
    owner_ids: tuple[int, ...] = tuple(int(x) for x in os.getenv("OWNER_IDS", "").split(",") if x.strip())
    log_level: str = os.getenv("LOG_LEVEL", "INFO")

settings = Settings()
