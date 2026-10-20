import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
env_path = BASE_DIR / '.env'
load_dotenv(dotenv_path=env_path)

class Settings:
    DB_USER: str = os.getenv("DB_USER", "usuario")
    DB_PASSWORD: str = os.getenv("DB_PASSWORD", "c4f3s1t10s!")
    DB_HOST: str = os.getenv("DB_HOST", "localhost")
    DB_PORT: str = os.getenv("DB_PORT", "5432")
    DB_NAME: str = os.getenv("DB_NAME", "cafesitios_db")

    @property
    def database_url(self) -> str:
        url_env = os.getenv("DATABASE_URL")
        if url_env:
            return url_env
        return f"postgresql+psycopg://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    @property
    def is_production(self) -> bool:
        is_render = os.getenv("RENDER", "").strip().lower() == "true"
        is_vercel = os.getenv("VERCEL", "").strip().lower() in ("1", "true")
        is_koyeb = bool(os.getenv("KOYEB_SERVICE_NAME", "").strip() or os.getenv("KOYEB_APP_NAME", "").strip())
        env_values = (
            os.getenv("ENVIRONMENT", "").strip().lower(),
            os.getenv("ENV", "").strip().lower(),
            os.getenv("APP_ENV", "").strip().lower(),
            os.getenv("NODE_ENV", "").strip().lower(),
        )
        return (
            is_render
            or is_vercel
            or is_koyeb
            or any(val in ("production", "prod", "produccion", "producción") for val in env_values)
        )

    @property
    def is_local_admin_enabled(self) -> bool:
        if self.is_production:
            return False
        raw_flag = os.getenv("ENABLE_LOCAL_ADMIN")
        if raw_flag is not None and raw_flag.strip() != "":
            return raw_flag.strip().lower() in ("true", "1", "yes", "on")
        return True

    @property
    def is_analytics_enabled(self) -> bool:
        if self.is_production:
            return False
        raw_flag = os.getenv("ENABLE_SYNC_ANALYTICS")
        if raw_flag is not None and raw_flag.strip() != "":
            return raw_flag.strip().lower() in ("true", "1", "yes", "on")
        return True

    @property
    def is_recipes_enabled(self) -> bool:
        raw_flag = os.getenv("ENABLE_RECIPES")
        if raw_flag is not None and raw_flag.strip() != "":
            return raw_flag.strip().lower() in ("true", "1", "yes", "on")
        return True

    @property
    def is_calibrator_enabled(self) -> bool:
        raw_flag = os.getenv("ENABLE_CALIBRATOR")
        if raw_flag is not None and raw_flag.strip() != "":
            return raw_flag.strip().lower() in ("true", "1", "yes", "on")
        return True

    @property
    def is_whatsapp_orders_enabled(self) -> bool:
        raw_flag = os.getenv("ENABLE_WHATSAPP_ORDERS")
        if raw_flag is not None and raw_flag.strip() != "":
            return raw_flag.strip().lower() in ("true", "1", "yes", "on")
        return True

settings = Settings()

