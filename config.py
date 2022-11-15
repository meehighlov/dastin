import dotenv

from pydantic import BaseSettings
from pydantic import validator
from pydantic import ValidationError


dotenv.load_dotenv()


class Config(BaseSettings):
    BOTTOKEN_DASTIN: str  # noqa
    TEAM_CHAT_ID: str = ''
    TEAM_DAILY_MEETING_URL: str
    TEAM_EVENT_DAILY_NAME: str
    TEAM_EVENT_TIMESHEETS_NAME: str
    ALLOWED_USERNAMES: str

    @property
    def ALLOWED_USERNAMES_LIST(self):
        return self.ALLOWED_USERNAMES.split(',')


config = Config()
