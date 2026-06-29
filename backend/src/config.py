"""Configuration typee de l'application.

Toutes les valeurs proviennent de variables d'environnement (ou du `.env` a la
racine du depot en developpement). Aucune valeur metier n'est codee en dur dans
le code applicatif : les defauts ici presents sont des defauts de developpement
local, surcharges par l'environnement en production.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Racine du depot : backend/src/config.py -> parents[2] = racine (el-haress-app).
# Permet de lire le .env quel que soit le repertoire de lancement.
_REPO_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    """Parametres applicatifs, charges depuis l'environnement et le .env."""

    model_config = SettingsConfigDict(
        env_file=str(_REPO_ROOT / ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # -- Application --------------------------------------------------------
    environment: str = "development"
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    log_level: str = "INFO"

    # -- Base de donnees (TimescaleDB) -------------------------------------
    database_url: str = "postgresql+asyncpg://el_haress:dev_password@localhost:5432/el_haress"
    readings_retention_days: int = 30

    # -- Redis --------------------------------------------------------------
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_password: str = ""
    redis_db_cache: int = 0
    redis_db_ratelimit: int = 1
    redis_db_alert_dedup: int = 2
    redis_db_jwt_blacklist: int = 3

    # -- Authentification (JWT RS256) --------------------------------------
    jwt_private_key_path: str = "./keys/private.pem"
    jwt_public_key_path: str = "./keys/public.pem"
    jwt_access_expires_minutes: int = 15
    jwt_refresh_expires_days: int = 7
    bcrypt_rounds: int = 12
    max_login_attempts: int = 5
    account_lock_minutes: int = 15
    login_rate_limit_per_minute: int = 10
    jwt_issuer: str = "el-haress"
    default_phone_region: str = "MR"
    refresh_cookie_name: str = "el_haress_refresh"
    cookie_secure: bool = False  # force a True via l'environnement en production

    # -- CORS ---------------------------------------------------------------
    cors_origins: str = "http://localhost:5173"

    # -- Collector / passerelle capteurs (STE2 LITE) -----------------------
    ste2_base_url: str = "http://192.168.1.105"
    collector_poll_interval_seconds: int = 10

    # -- Notifications (optionnel) -----------------------------------------
    twilio_account_sid: str = ""
    twilio_auth_token: str = ""
    twilio_whatsapp_from: str = ""
    twilio_sms_from: str = ""
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = ""

    # -- Observabilite ------------------------------------------------------
    sentry_dsn: str = ""

    @property
    def is_production(self) -> bool:
        return self.environment.lower() == "production"

    @property
    def cors_origins_list(self) -> list[str]:
        """Liste des origines CORS autorisees (jamais '*' en production)."""
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    """Retourne l'instance unique des parametres (mise en cache)."""
    return Settings()
