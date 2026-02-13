import os
import secrets

from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    app_name: str = "DocParse Arena"
    debug: bool = False

    database_url: str = "sqlite+aiosqlite:///./docparse_arena.db"

    anthropic_api_key: str = ""
    openai_api_key: str = ""
    google_api_key: str = ""
    mistral_api_key: str = ""
    ollama_base_url: str = "http://localhost:11434"

    sample_docs_dir: str = os.path.join(os.path.dirname(os.path.dirname(__file__)), "sample_docs")

    admin_password: str = ""

    cors_origins: list[str] = ["http://localhost:3000"]

    # JWT settings
    jwt_secret: str = ""
    jwt_expiry_minutes: int = 1440  # 24 hours

    # Upload limits
    max_upload_size: int = 50 * 1024 * 1024  # 50 MB

    # PDF processing
    max_pdf_pages: int = 50
    pdf_dpi: float = 216.0

    # ELO
    elo_k_factor: int = 20

    # Privacy / security
    store_ocr_results: bool = True  # Save OCR text to DB; disable for sensitive docs

    # Streaming
    stream_timeout_seconds: int = 300

    # Ollama timeouts
    ollama_connect_timeout: float = 10.0
    ollama_read_timeout: float = 120.0

    model_config = {"env_file": ".env", "extra": "ignore"}

    def get_jwt_secret(self) -> str:
        if self.jwt_secret:
            return self.jwt_secret
        # Generate a random secret per process (tokens won't survive restart)
        if not hasattr(self, "_runtime_jwt_secret"):
            object.__setattr__(self, "_runtime_jwt_secret", secrets.token_hex(32))
        return self._runtime_jwt_secret


@lru_cache
def get_settings() -> Settings:
    return Settings()
