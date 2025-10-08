from pydantic_settings import BaseSettings
from pydantic import ConfigDict

class Settings(BaseSettings):
    CRM_BASE_URL: str = "http://localhost:8001"
    LOG_LEVEL: str = "INFO"
    
    GOOGLE_API_KEY: str                 # This looks for the Google key

    model_config = ConfigDict(env_file=".env", extra='ignore')

settings = Settings()