import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # Base paths
    BASE_DIR: Path = Path(__file__).resolve().parent.parent
    DATA_DIR: Path = BASE_DIR / "chroma_data"
    UPLOAD_DIR: Path = BASE_DIR / "uploaded_docs"

    # Vector store & embeddings
    COLLECTION_NAME: str = "knowledge_base"
    EMBEDDING_MODEL: str = "cointegrated/rubert-tiny2"
    CHUNK_SIZE: int = 750

    CHUNK_OVERLAP: int = 120
    TOP_K: int = 4
    SIMILARITY_THRESHOLD: float = 0.20

    # Optional LLM API Configuration
    OPENAI_API_KEY: str | None = None
    OPENAI_API_BASE: str | None = None
    OPENAI_MODEL: str = "gpt-4o-mini"
    
    # Server settings
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()

# Ensure directories exist
settings.DATA_DIR.mkdir(parents=True, exist_ok=True)
settings.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
