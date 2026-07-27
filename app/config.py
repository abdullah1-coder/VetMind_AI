#%%
import os
from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from app.services.logging_config import logger

class Settings(BaseSettings):
    # Core API Keys & Credentials
    groq_api_key: Optional[str] = None
    
    VECTOR_DB_DIR: str = r"C:\VetMind AI\app\data\vector_store"
    # LangChain / LangSmith Tracing
    langchain_tracing_v2: Optional[str] = "false"
    langsmith_tracing: Optional[str] = "false"
    langsmith_endpoint: Optional[str] = "https://api.smith.langchain.com"
    langsmith_api_key: Optional[str] = None
    langsmith_project: Optional[str] = "VetMind AI"

    # Pydantic v2 Settings Config: Allow extra variables without throwing validation errors
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",            # Ignore any other keys in .env that aren't defined here
        case_sensitive=False       # Matches GROQ_API_KEY to groq_api_key automatically
    )


# Singleton settings instance
settings = Settings()
# %%
