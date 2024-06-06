from pydantic.v1 import BaseSettings

from src import commands

BOT_COMMANDS = [commands.START, commands.HELP]


class Settings(BaseSettings):
    ASVTTK_DATABASE_URL: str
    ADMIN_ACCESS_KEY: str
    BOT_TOKEN: str

    class Config:
        env_file = ".env"


settings = Settings()
