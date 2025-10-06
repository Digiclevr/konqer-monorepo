"""
Configuration management using Pydantic Settings
Environment variables loaded from DO Secrets in K8s
"""
from pydantic_settings import BaseSettings
from typing import List
from functools import lru_cache


class Settings(BaseSettings):
    # Environment
    ENVIRONMENT: str = "production"

    # Database (postgres-central.platform)
    DATABASE_URL: str

    # Keycloak (Auth)
    KEYCLOAK_SERVER_URL: str = "https://auth.konqer.app"
    KEYCLOAK_REALM: str = "konqer"
    KEYCLOAK_CLIENT_ID: str = "konqer-api"
    KEYCLOAK_CLIENT_SECRET: str

    # JWT
    JWT_ALGORITHM: str = "RS256"
    JWT_PUBLIC_KEY: str  # Keycloak public key

    # Stripe
    STRIPE_SECRET_KEY: str
    STRIPE_WEBHOOK_SECRET: str
    STRIPE_FOUNDING_PRICE_ID: str = "price_founding_699eur_annual"

    # OpenAI
    OPENAI_API_KEY: str
    OPENAI_MODEL: str = "gpt-4o"

    # Apollo.io
    APOLLO_API_KEY: str
    APOLLO_BASE_URL: str = "https://api.apollo.io/v1"

    # LinkedIn (if using official API)
    LINKEDIN_CLIENT_ID: str = ""
    LINKEDIN_CLIENT_SECRET: str = ""

    # Redis (rate limiting)
    REDIS_URL: str = "redis://platform-pool-redis-master.platform:6379"

    # CORS Origins (Kinsta Static sites)
    CORS_ORIGINS: List[str] = [
        "https://konqer.app",
        "https://cold-dm.konqer.app",
        "https://objection.konqer.app",
        "https://carousel.konqer.app",
        "https://community-finder.konqer.app",
        "https://cold-email.konqer.app",
        "https://pitch-deck.konqer.app",
        "https://whitepaper.konqer.app",
        "https://deck-heatmap.konqer.app",
        "https://webinar.konqer.app",
        "https://warmranker.konqer.app",
        "https://no-show-shield.konqer.app",
        "https://battlecards.konqer.app",
        "http://localhost:3100",  # Local dev
        "http://localhost:3101",
        "http://localhost:3102",
        "http://localhost:3103",
        "http://localhost:3104",
        "http://localhost:3105",
        "http://localhost:3106",
        "http://localhost:3107",
        "http://localhost:3108",
        "http://localhost:3109",
        "http://localhost:3110",
        "http://localhost:3111",
        "http://localhost:3112",
    ]

    # Email (Resend or SendGrid)
    EMAIL_PROVIDER: str = "resend"
    RESEND_API_KEY: str = ""
    SENDGRID_API_KEY: str = ""
    EMAIL_FROM: str = "noreply@konqer.app"

    # Rate Limiting
    RATE_LIMIT_DAILY: int = 100
    RATE_LIMIT_BURST: int = 10

    # Pagination
    DEFAULT_PAGE_SIZE: int = 20
    MAX_PAGE_SIZE: int = 100

    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """
    Cached settings instance
    """
    return Settings()


settings = get_settings()
