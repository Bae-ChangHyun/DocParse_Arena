import os
import secrets
from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "DocParse Arena"
    debug: bool = False

    database_url: str = "sqlite+aiosqlite:///./data/docparse_arena.db"

    anthropic_api_key: str = ""
    openai_api_key: str = ""
    google_api_key: str = ""
    mistral_api_key: str = ""

    sample_docs_dir: str = os.path.join(os.path.dirname(os.path.dirname(__file__)), "sample_docs")

    # Benchmark collection uploads (persisted to disk, gitignored under data/)
    batch_uploads_dir: str = "./data/collections"
    # Official benchmark datasets (OmniDocBench, olmOCR-Bench) live here
    benchmarks_dir: str = "./data/benchmarks"
    # Repo-level bench/ dir holding scorer wrappers + olmocr venv
    bench_root: str = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "bench"
    )
    # Max concurrent OCR calls within a single batch run
    batch_concurrency: int = 6
    # OmniDocBench CDM (formula) metric is slow; allow disabling per deployment
    omnidocbench_enable_cdm: bool = True
    omnidocbench_workers: int = 8

    admin_password: str = ""
    allow_unprotected_admin: bool = False

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

    model_config = {"env_file": ".env", "extra": "ignore"}

    def get_jwt_secret(self) -> str:
        if self.jwt_secret:
            return self.jwt_secret
        # Generate a random secret per process (tokens won't survive restart)
        if not hasattr(self, "_runtime_jwt_secret"):
            object.__setattr__(self, "_runtime_jwt_secret", secrets.token_hex(32))
        return self._runtime_jwt_secret

    def provider_api_key(self, provider_type: str) -> str:
        """Return the environment API key for a built-in provider type."""
        return {
            "claude": self.anthropic_api_key,
            "openai": self.openai_api_key,
            "gemini": self.google_api_key,
            "mistral": self.mistral_api_key,
        }.get(provider_type, "").strip()


@lru_cache
def get_settings() -> Settings:
    return Settings()
