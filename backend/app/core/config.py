"""全局配置管理。

统一从环境变量读取配置，支持两种运行模式：
- USE_DOCKER=true  : 使用 PostgreSQL / Milvus / Neo4j / Redis / Celery 完整架构
- USE_DOCKER=false : 本地降级模式（SQLite + 内存向量库），零外部依赖

用法：
    from app.core.config import settings
    settings.LLM_API_KEY
"""
from functools import lru_cache
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # ---- 运行模式 ----
    USE_DOCKER: bool = False

    # ---- 应用 ----
    APP_NAME: str = "企业合同智能审查与风险辅助 Agent"
    APP_ENV: str = "development"
    DEBUG: bool = True
    SECRET_KEY: str = "change-me-to-a-random-secret"
    API_PREFIX: str = "/api"

    # ---- 大模型 ----
    LLM_PROVIDER: str = "openai"
    LLM_API_KEY: str = ""
    LLM_BASE_URL: str = "https://api.openai.com/v1"
    LLM_MODEL: str = "gpt-4o-mini"
    LLM_EMBEDDING_MODEL: str = "text-embedding-3-small"
    LLM_TEMPERATURE: float = 0.1
    LLM_MAX_TOKENS: int = 4096

    # ---- PostgreSQL ----
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_DB: str = "contract_review"

    # ---- Redis ----
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0

    # ---- Milvus ----
    MILVUS_HOST: str = "localhost"
    MILVUS_PORT: int = 19530
    MILVUS_COLLECTION: str = "legal_knowledge_collection"

    # ---- Neo4j ----
    NEO4J_URI: str = "bolt://localhost:7687"
    NEO4J_USER: str = "neo4j"
    NEO4J_PASSWORD: str = "password"

    # ---- 文件存储 ----
    STORAGE_BACKEND: str = "local"
    STORAGE_DIR: str = "../storage"

    # ---- 派生属性 ----
    @property
    def database_url(self) -> str:
        """数据库连接串，根据模式自动切换。"""
        if self.USE_DOCKER:
            return (
                f"postgresql+psycopg2://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
                f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
            )
        # 本地降级：SQLite
        return "sqlite:///./contract_review.db"

    @property
    def redis_url(self) -> str:
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    @property
    def use_mock_llm(self) -> bool:
        """未配置 API Key 时，自动进入 Mock 模式。"""
        return not bool(self.LLM_API_KEY)


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
