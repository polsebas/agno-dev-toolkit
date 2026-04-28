from pydantic_settings import BaseSettings
from typing import Literal, Optional


class Settings(BaseSettings):
    vector_backend: Literal["chroma", "milvus"] = "chroma"
    milvus_host: str = "localhost"
    milvus_port: int = 19530
    chroma_persist_path: str = "data/chroma_db"
    collection_name: str = "agno_framework_knowledge"
    embedding_model: str = "all-MiniLM-L6-v2"
    mcp_tool_timeout: int = 30
    log_level: str = "INFO"
    ingest_docs: bool = False
    hf_token: Optional[str] = None

    class Config:
        env_file = ".env"


settings = Settings()
