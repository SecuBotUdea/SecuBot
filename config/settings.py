"""
SecuBot - Settings Configuration
Manejo centralizado de configuración usando Pydantic Settings
"""

from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuración global de la aplicación"""

    model_config = SettingsConfigDict(
        env_file='.env', env_file_encoding='utf-8', case_sensitive=False, extra='ignore'
    )

    # ============================================
    # Application Settings
    # ============================================
    app_name: str = Field(default='SecuBot')
    app_version: str = Field(default='1.0.0')
    environment: str = Field(default='development')
    debug: bool = Field(default=True)
    log_level: str = Field(default='INFO')

    # ============================================
    # Server Settings
    # ============================================
    host: str = Field(default='0.0.0.0')
    port: int = Field(default=8000)

    # ============================================
    # MongoDB Settings
    # ============================================
    mongodb_uri: str = Field(
        default='mongodb://localhost:27017', description='MongoDB connection URI'
    )
    database_name: str = Field(default='secubot_dev')

    @field_validator('mongodb_uri')
    @classmethod
    def validate_mongodb_uri(cls, v: str) -> str:
        if not v.startswith(('mongodb://', 'mongodb+srv://')):
            raise ValueError('MongoDB URI must start with mongodb:// or mongodb+srv://')
        return v

    # ============================================
    # Slack Integration
    # ============================================
    slack_webhook_url: str | None = Field(default=None)
    slack_notifications_enabled: bool = Field(default=False)

    # ============================================
    # Rules Configuration
    # ============================================
    rules_config_path: Path = Field(default=Path('config/rules.yaml'))
    badges_config_path: Path = Field(default=Path('config/badges.yaml'))

    # ============================================
    # Rescan Configuration
    # ============================================
    rescan_delay_seconds: int = Field(
        default=300, description='Delay antes de ejecutar rescan (5 minutos default)'
    )
    rescan_timeout_hours: int = Field(
        default=72, description='Timeout para remediación sin verificar (PEN-001)'
    )

    # ============================================
    # Gamification Settings
    # ============================================
    enable_speed_bonus: bool = Field(default=True)
    speed_bonus_threshold_hours: int = Field(
        default=24, description='Umbral para bonus de velocidad (PTS-004)'
    )
    speed_bonus_multiplier: float = Field(
        default=1.5, description='Multiplicador del bonus de velocidad'
    )

    # ============================================
    # Task Scheduler
    # ============================================
    enable_scheduler: bool = Field(default=True)
    timeout_check_interval_minutes: int = Field(
        default=60, description='Intervalo para verificar timeouts (cada hora)'
    )
    leaderboard_update_cron: str = Field(
        default='0 0 * * 0',
        description='Cron expression para actualizar leaderboard (Domingos medianoche)',
    )

    # ============================================
    # Security (futuro)
    # ============================================
    secret_key: str = Field(
        default='your-secret-key-here-change-in-production',
        description='Secret key para JWT tokens',
    )
    algorithm: str = Field(default='HS256')
    access_token_expire_minutes: int = Field(default=30)

    # ============================================
    # CORS
    # ============================================
    allowed_origins: list[str] = Field(default=['http://localhost:3000', 'http://localhost:8080'])

    @field_validator('allowed_origins', mode='before')
    @classmethod
    def parse_origins(cls, v):
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(',')]
        return v

    # ============================================
    # Rate Limiting (futuro)
    # ============================================
    rate_limit_enabled: bool = Field(default=False)
    rate_limit_per_minute: int = Field(default=60)

    # ============================================
    # Computed Properties
    # ============================================
    @property
    def is_production(self) -> bool:
        """Check if running in production"""
        return self.environment.lower() == 'production'

    @property
    def is_development(self) -> bool:
        """Check if running in development"""
        return self.environment.lower() == 'development'

    @property
    def mongodb_config(self) -> dict:
        """Get MongoDB configuration dict"""
        return {
            'uri': self.mongodb_uri,
            'database': self.database_name,
        }


# Instancia global de settings
settings = Settings()


# ============================================
# Utility Functions
# ============================================


def get_settings() -> Settings:
    """
    Dependency para FastAPI
    Permite inyectar settings en endpoints
    """
    return settings


def reload_settings() -> Settings:
    """
    Recarga la configuración (útil para tests)
    """
    global settings
    settings = Settings()
    return settings
