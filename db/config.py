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
    TEST: str = os.getenv("DB_HELP", "No lee nada")

    @property
    def database_url(self) -> str:
        url_env = os.getenv("DATABASE_URL")
        if url_env:
            print("TAG: " + self.TEST)
            return url_env
        return f"postgresql+psycopg://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

settings = Settings()
