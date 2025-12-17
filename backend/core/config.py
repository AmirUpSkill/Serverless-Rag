import base64
import json
from functools import lru_cache
from typing import List, Literal, Union

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # --- Gemini ---
    gemini_api_key: SecretStr
    gemini_model: str = "gemini-2.5-pro"

    # --- Firebase ---
    firebase_service_account_base64: SecretStr

    # --- Object Storage (MinIO / S3-compatible) ---
    # Used for storing raw file contents. Defaults are suitable for local MinIO
    # running via docker-compose.
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: SecretStr = SecretStr("minioadmin123")
    minio_bucket: str = "servless-rag"
    minio_use_ssl: bool = False
    # Optional public base URL for generating file URLs, e.g. "http://localhost:9000"
    minio_public_url: str | None = None

    # --- Server ---
    host: str = "0.0.0.0"
    port: int = 8000
    log_level: Literal["critical", "error", "warning", "info", "debug"] = "info"

    # --- CORS ---
    cors_origins: List[str] = Field(default_factory=lambda: ["*"])

    @field_validator("log_level", mode="before")
    @classmethod
    def normalize_log_level(cls, v: str) -> str:
        if isinstance(v, str):
            v = v.lower().strip()
        return v

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: Union[str, List[str], None]):
        if v is None or v == "" or v == ["*"] or v == "*":
            return ["*"]
        if isinstance(v, list):
            return v
        if isinstance(v, str):
            s = v.strip()
            if s.startswith("["):
                try:
                    parsed = json.loads(s)
                    if isinstance(parsed, list):
                        return [str(x).strip() for x in parsed if str(x).strip()]
                except json.JSONDecodeError:
                    pass
            return [part.strip() for part in s.split(",") if part.strip()]
        return v

    @property
    def firebase_service_account(self) -> dict:
        """Decode BASE64 service account JSON to a dict."""
        try:
            raw = self.firebase_service_account_base64.get_secret_value()
            decoded = base64.b64decode(raw).decode("utf-8")
            data = json.loads(decoded)
            if not isinstance(data, dict):
                raise ValueError("Decoded service account is not a JSON object")
            return data
        except Exception as e:
            raise ValueError(
                "Invalid FIREBASE_SERVICE_ACCOUNT_BASE64: unable to decode/parse JSON"
            ) from e

    model_config = SettingsConfigDict(
        env_file=("../.env", ".env"),
        env_ignore_empty=True,
        extra="ignore",
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()