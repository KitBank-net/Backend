from pydantic_settings import BaseSettings
from typing import List, Optional
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # Database
    DATABASE_URL: str = "postgresql+asyncpg://kitbank:kitbank_password@localhost:5432/kitbank_db"
    DATABASE_SYNC_URL: str = "postgresql://kitbank:kitbank_password@localhost:5432/kitbank_db"
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # JWT
    SECRET_KEY: str = "your-secret-key-here-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # Security
    BCRYPT_ROUNDS: int = 12
    MAX_LOGIN_ATTEMPTS: int = 5
    ACCOUNT_LOCK_DURATION_MINUTES: int = 30
    
    # AWS S3
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    AWS_S3_BUCKET_NAME: str = "kitbank-documents"
    AWS_REGION: str = "us-east-1"
    USE_LOCAL_STORAGE: bool = True
    LOCAL_STORAGE_PATH: str = "./uploads"
    
    # Email (SendGrid)
    SENDGRID_API_KEY: str = ""
    SENDGRID_FROM_EMAIL: str = "noreply@kitbank.net"
    SENDGRID_FROM_NAME: str = "KitBank"
    
    # SMS (Twilio)
    TWILIO_ACCOUNT_SID: str = ""
    TWILIO_AUTH_TOKEN: str = ""
    TWILIO_PHONE_NUMBER: str = ""
    
    # Application
    APP_NAME: str = "KitBank.net"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    ENVIRONMENT: str = "development"
    FRONTEND_URL: str = "http://localhost:3000"
    
    # CORS
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:8000"
    CORS_ALLOW_CREDENTIALS: bool = True
    
    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = 60
    RATE_LIMIT_PER_HOUR: int = 1000
    
    # OTP
    OTP_EXPIRY_MINUTES: int = 10
    OTP_LENGTH: int = 6
    
    # ============================================================
    # Mobile Money Providers
    # ============================================================
    
    # M-Pesa
    MPESA_CONSUMER_KEY: str = ""
    MPESA_CONSUMER_SECRET: str = ""
    MPESA_SHORTCODE: str = ""
    MPESA_PASSKEY: str = ""
    MPESA_ENVIRONMENT: str = "sandbox"
    MPESA_CALLBACK_URL: str = ""
    
    # MTN Mobile Money
    MTN_MOMO_SUBSCRIPTION_KEY: str = ""
    MTN_MOMO_API_USER: str = ""
    MTN_MOMO_API_KEY: str = ""
    MTN_MOMO_ENVIRONMENT: str = "sandbox"
    MTN_MOMO_CALLBACK_URL: str = ""
    
    # Airtel Money
    AIRTEL_MONEY_CLIENT_ID: str = ""
    AIRTEL_MONEY_CLIENT_SECRET: str = ""
    AIRTEL_MONEY_ENVIRONMENT: str = "sandbox"
    AIRTEL_MONEY_CALLBACK_URL: str = ""
    
    # ============================================================
    # International Transfers
    # ============================================================
    SWIFT_BIC_CODE: str = ""
    CORRESPONDENT_BANK_API_URL: str = ""
    CORRESPONDENT_BANK_API_KEY: str = ""
    INTERNATIONAL_TRANSFER_APPROVAL_THRESHOLD: int = 10000
    
    # ============================================================
    # FX Provider
    # ============================================================
    FX_PROVIDER: str = "internal"
    FX_API_KEY: str = ""
    FX_API_URL: str = ""
    FX_RATE_CACHE_MINUTES: int = 15
    
    # ============================================================
    # Transaction Settings
    # ============================================================
    DEFAULT_CURRENCY: str = "USD"
    TRANSACTION_REFERENCE_PREFIX: str = "TXN"
    MAX_TRANSACTION_AMOUNT: int = 1000000
    MIN_TRANSACTION_AMOUNT: int = 1
    
    # ============================================================
    # QR Code
    # ============================================================
    QR_CODE_DEFAULT_EXPIRY_HOURS: int = 24
    QR_CODE_MAX_EXPIRY_HOURS: int = 720
    
    # ============================================================
    # Bill Payment
    # ============================================================
    BILLER_AGGREGATOR_API_URL: str = ""
    BILLER_AGGREGATOR_API_KEY: str = ""
    
    # ============================================================
    # Logging
    # ============================================================
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"
    
    # ============================================================
    # Celery
    # ============================================================
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"
    
    class Config:
        env_file = ".env"
        case_sensitive = True
    
    @property
    def cors_origins_list(self) -> List[str]:
        """Convert CORS_ORIGINS string to list"""
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]
    
    @property
    def is_production(self) -> bool:
        """Check if running in production"""
        return self.ENVIRONMENT == "production"
    
    @property
    def is_development(self) -> bool:
        """Check if running in development"""
        return self.ENVIRONMENT == "development"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()


settings = get_settings()
