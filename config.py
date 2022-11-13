import dotenv

from pydantic import BaseSettings


dotenv.load_dotenv()


class Config(BaseSettings):
    DASTIN_TOKEN: str  # noqa


config = Config()
