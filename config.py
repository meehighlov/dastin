import dotenv

from pydantic import BaseSettings


dotenv.load_dotenv()


class Config(BaseSettings):
    BOTTOKEN_DASTIN: str  # noqa
    TEAM_CHAT_ID: str = ''
    TEAM_CHAT_NAME: str = ''
    TEAM_DAILY_MEETING_URL: str = ''
    TEAM_EVENT_DAILY_NAME: str = ''


config = Config()
