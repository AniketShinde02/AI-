from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional
import os

class Settings(BaseSettings):
    # Core API Keys (Matching .env)
    STREAM_API_KEY: Optional[str] = None
    STREAM_API_SECRET: Optional[str] = None
    
    # Aliases for backward compatibility or different naming conventions
    @property
    def GETSTREAM_API_KEY(self): return self.STREAM_API_KEY
    @property
    def GETSTREAM_API_SECRET(self): return self.STREAM_API_SECRET


    DATABASE_URL: Optional[str] = None
    FIREBASE_PROJECT_ID: str = "studio-8908067992-4e114"
    FIREBASE_CREDENTIALS: Optional[str] = None # JSON string
    
    # AI Providers
    OPENAI_API_KEY: Optional[str] = None
    GROQ_API_KEY: Optional[str] = None
    CARTESIA_API_KEY: Optional[str] = None
    
    # Voice Config
    DEEPGRAM_API_KEY: Optional[str] = None
    DEEPGRAM_MODEL: str = "nova-3"
    
    ELEVENLABS_API_KEY: Optional[str] = None
    ELEVENLABS_MODEL: str = "eleven_multilingual_v2"
    ELEVENLABS_VOICE_ID: str = "VR6AewLTigWG4xSOukaG" # Default Nexus Voice

    NEXUS_VOICE_TYPE: str = "female" # default to female as requested
    
    # Environment
    ENV: str = "development"
    DEBUG: bool = True
    
    # App Settings
    PROJECT_NAME: str = "Nexus AI"
    VERSION: str = "2.0.0"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()

