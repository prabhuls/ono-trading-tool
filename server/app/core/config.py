from typing import List, Optional, Dict, Any
from pathlib import Path
import os
from pydantic import BaseModel, Field, validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class LoggingConfig(BaseModel):
    """Logging configuration"""
    level: str = "INFO"
    format: str = "json"  # json or text
    handlers: List[str] = ["console", "file"]
    file_path: str = "logs/app.log"
    max_file_size: int = 10_485_760  # 10MB
    backup_count: int = 5
    include_context: bool = True
    
    # Sentry integration
    sentry_enabled: bool = True
    sentry_attach_stacktrace: bool = True
    sentry_send_default_pii: bool = False


class CacheConfig(BaseModel):
    """Cache configuration"""
    default_ttl: int = 300  # 5 minutes
    max_ttl: int = 86400  # 24 hours
    namespace_separator: str = ":"
    key_prefix: str = "app"
    
    # TTL by data type
    ttl_mapping: Dict[str, int] = {
        "market_data": 60,      # 1 minute
        "user_data": 300,       # 5 minutes
        "static_data": 3600,    # 1 hour
        "calculations": 300,    # 5 minutes
    }


class DatabaseConfig(BaseModel):
    """Database configuration"""
    echo: bool = False
    pool_size: int = 10
    max_overflow: int = 20
    pool_timeout: int = 30
    pool_recycle: int = 1800
    
    @validator("echo", pre=True)
    def validate_echo(cls, v, values):
        # Force echo to False in production
        if os.getenv("ENVIRONMENT") == "production":
            return False
        return v


class APIConfig(BaseModel):
    """API configuration"""
    title: str = "Trading Tools API"
    description: str = "Backend API for Trading and Investment Tools"
    version: str = "1.0.0"
    prefix: str = "/api/v1"
    
    # Rate limiting
    rate_limit_enabled: bool = True
    rate_limit_requests: int = 100
    rate_limit_period: int = 60  # seconds
    
    # Pagination
    default_page_size: int = 50
    max_page_size: int = 100


class SecurityConfig(BaseModel):
    """Security configuration"""
    algorithm: str = "RS256"  # Changed to RS256 for RSA public key verification
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7
    
    # JWT RSA Public Key for verification (from one-click trading service)
    jwt_public_key: str = """-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAtSt0xH5N6SOVXY4E2h1X
WE6edernQCmw2kfg6023C64hYR4PZH8XM2P9qoyAzq19UDJZbVj4hi/75GKHEFBC
zL+SrJLgc/6jZoMpOYtEhDgzEKKdfFtgpGD18Idc5IyvBLeW2d8gvfIJMuxRUnT6
K3spmisjdZtd+7bwMKPl6BGAsxZbhlkGjLI1gP/fHrdfU2uoL5okxbbzg1NH95xc
LSXX2JJ+q//t8vLGy+zMh8HPqFM9ojsxzT97AiR7uZZPBvR6c/rX5GDIFPvo5QVr
crCucCyTMeYqwyGl14zN0rArFi6eFXDn+JWTs3Qf04F8LQn7TiwxKV9KRgPHYFtG
qwIDAQAB
-----END PUBLIC KEY-----"""
    
    # OAuth Configuration (removed - using simple JWT verification)
    # oauth_client_id: Optional[str] = None
    # oauth_client_secret: Optional[str] = None
    # oauth_redirect_uri: Optional[str] = None
    # oauth_authorize_url: str = "https://auth.tradingservice.com/authorize"
    # oauth_token_url: str = "https://auth.tradingservice.com/token"
    
    # CORS
    allowed_origins: List[str] = []
    allowed_methods: List[str] = ["GET", "POST", "PUT", "DELETE", "PATCH"]
    allowed_headers: List[str] = ["*"]
    allow_credentials: bool = True


class Settings(BaseSettings):
    """Main application settings"""
    
    # Environment
    environment: str = Field(default="development", validation_alias="ENVIRONMENT")
    debug: bool = Field(default=False, validation_alias="DEBUG")
    
    # API Configuration
    api: APIConfig = APIConfig()
    
    # Security
    secret_key: str = Field(..., validation_alias="SECRET_KEY")
    security: SecurityConfig = SecurityConfig()
    
    # Frontend URLs (comma-separated for multiple frontends)
    frontend_url: Optional[str] = Field(None, validation_alias="FRONTEND_URL")
    additional_frontend_urls: Optional[str] = Field(None, validation_alias="ADDITIONAL_FRONTEND_URLS")
    
    # Database
    database_url: Optional[str] = Field(None, validation_alias="DATABASE_URL")
    database: DatabaseConfig = DatabaseConfig()
    enable_database: bool = Field(default=True, validation_alias="ENABLE_DATABASE")
    
    # Redis
    redis_url: Optional[str] = Field(None, validation_alias="REDIS_URL")
    cache: CacheConfig = CacheConfig()
    enable_caching: bool = Field(default=True, validation_alias="ENABLE_CACHING")
    
    # External APIs
    polygon_api_key: Optional[str] = Field(None, validation_alias="POLYGON_API_KEY")
    polygon_base_url: str = Field(default="https://api.polygon.io", validation_alias="POLYGON_BASE_URL")
    
    # OAuth configuration (removed - using simple JWT verification)
    # trading_service_auth_url: str = Field(default="https://auth.tradingservice.com", validation_alias="TRADING_SERVICE_AUTH_URL")
    # trading_service_client_id: Optional[str] = Field(None, validation_alias="TRADING_SERVICE_CLIENT_ID")
    # trading_service_client_secret: Optional[str] = Field(None, validation_alias="TRADING_SERVICE_CLIENT_SECRET")
    
    # Add more external API configs as needed
    external_api_timeout: int = Field(default=30, validation_alias="EXTERNAL_API_TIMEOUT")
    external_api_retry_count: int = Field(default=3, validation_alias="EXTERNAL_API_RETRY_COUNT")
    
    # Logging
    logging: LoggingConfig = LoggingConfig()
    
    # Sentry
    sentry_dsn: Optional[str] = Field(None, validation_alias="SENTRY_DSN")
    sentry_traces_sample_rate: float = Field(default=0.1, validation_alias="SENTRY_TRACES_SAMPLE_RATE")
    sentry_profiles_sample_rate: float = Field(default=0.1, validation_alias="SENTRY_PROFILES_SAMPLE_RATE")
    sentry_environment: Optional[str] = Field(None, validation_alias="SENTRY_ENVIRONMENT")
    
    # Authentication
    enable_auth: bool = Field(default=True, validation_alias="ENABLE_AUTH")
    
    # Feature Flags
    features: Dict[str, bool] = {
        "enable_websockets": True,
        "enable_rate_limiting": True,
        "enable_metrics": True,
    }
    
    model_config = SettingsConfigDict(
        env_file=str(Path(__file__).parent.parent.parent / ".env"),
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="allow"
    )
    
    @model_validator(mode='after')
    def validate_database_config(self):
        """Validate database configuration"""
        if self.enable_database and not self.database_url:
            raise ValueError("DATABASE_URL is required when ENABLE_DATABASE=true")
        return self
    
    @model_validator(mode='after')
    def validate_cache_config(self):
        """Validate cache configuration"""
        if self.enable_caching and not self.redis_url:
            raise ValueError("REDIS_URL is required when ENABLE_CACHING=true")
        return self
    
    @property
    def async_database_url(self) -> Optional[str]:
        """Convert sync DATABASE_URL to async format for SQLAlchemy"""
        if not self.database_url:
            return None
        if self.database_url.startswith("postgresql://"):
            return self.database_url.replace("postgresql://", "postgresql+asyncpg://")
        return self.database_url
    
    @property
    def cors_origins(self) -> List[str]:
        """Get CORS origins based on environment"""
        origins = []
        
        if self.environment == "development":
            # Development origins
            origins = [
                "http://localhost:3000",
                "http://localhost:3001",
                "http://127.0.0.1:3000",
                "http://127.0.0.1:3001",
            ]
        else:
            # Production origins from settings
            origins = self.security.allowed_origins.copy()
        
        # Add FRONTEND_URL if specified
        if self.frontend_url:
            # Parse the URL to ensure it's properly formatted
            frontend_origin = self.frontend_url
            if not frontend_origin.startswith(("http://", "https://")):
                frontend_origin = f"https://{frontend_origin}"
            if frontend_origin not in origins:
                origins.append(frontend_origin)
        
        # Add additional frontend URLs if specified
        if self.additional_frontend_urls:
            additional_urls = [url.strip() for url in self.additional_frontend_urls.split(',')]
            for url in additional_urls:
                if url:
                    if not url.startswith(("http://", "https://")):
                        url = f"https://{url}"
                    if url not in origins:
                        origins.append(url)
        
        # Add specific Railway app domains if in production
        # Note: Wildcards don't work with FastAPI CORS, must use exact domains
        if self.environment == "production":
            # Add any known Railway domains here
            known_railway_domains = [
                "https://cashflowagent-vip-production.up.railway.app",
                "https://cfa-frontend-production.up.railway.app",
                "https://client2-production.up.railway.app"
            ]
            for domain in known_railway_domains:
                if domain not in origins:
                    origins.append(domain)
        
        return origins
    
    @property
    def logging_config(self) -> LoggingConfig:
        """Get environment-specific logging configuration"""
        if self.environment == "production":
            return LoggingConfig(
                level="WARNING",
                format="json",
                handlers=["console", "file", "sentry"],
                include_context=True,
                sentry_enabled=True
            )
        elif self.environment == "development":
            return LoggingConfig(
                level="DEBUG",
                format="text",
                handlers=["console"],
                include_context=True,
                sentry_enabled=False
            )
        return self.logging
    
    @property
    def is_production(self) -> bool:
        """Check if running in production"""
        return self.environment == "production"
    
    @property
    def is_development(self) -> bool:
        """Check if running in development"""
        return self.environment == "development"
    
    @property
    def is_testing(self) -> bool:
        """Check if running in test environment"""
        return self.environment == "testing"
    
    def get_external_api_config(self, service_name: str) -> Dict[str, Any]:
        """Get configuration for external API service"""
        configs = {
            "polygon": {
                "api_key": self.polygon_api_key,
                "base_url": self.polygon_base_url,
                "timeout": self.external_api_timeout,
                "retry_count": self.external_api_retry_count,
            },
            # Add more service configurations here
        }
        return configs.get(service_name, {})


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()  # type: ignore[call-arg]


# Create a global settings instance
settings = get_settings()
