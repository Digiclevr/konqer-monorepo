"""
SQLAlchemy models matching the database schema
"""
from sqlalchemy import (
    Column, String, Integer, Float, Boolean, Text,
    ForeignKey, TIMESTAMP, Enum, Index, UniqueConstraint
)
from sqlalchemy.dialects.postgresql import UUID, JSONB, INET
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
from sqlalchemy.sql import func
import enum
from config import settings

# Base class
Base = declarative_base()

# Async engine
engine = create_async_engine(
    settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://"),
    echo=settings.ENVIRONMENT == "development",
    pool_size=10,
    max_overflow=20
)

# Async session factory
async_session = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)


# ============================================
# ENUMS
# ============================================
class SubscriptionPlan(str, enum.Enum):
    FOUNDING = "founding"
    MONTHLY_SINGLE = "monthly_single"
    MONTHLY_BUNDLE = "monthly_bundle"
    ANNUAL_SINGLE = "annual_single"
    ANNUAL_BUNDLE = "annual_bundle"


class SubscriptionStatus(str, enum.Enum):
    ACTIVE = "active"
    CANCELED = "canceled"
    PAST_DUE = "past_due"
    UNPAID = "unpaid"
    TRIALING = "trialing"


class PaymentStatus(str, enum.Enum):
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    REFUNDED = "refunded"
    PENDING = "pending"


class AdminRole(str, enum.Enum):
    SUPERADMIN = "superadmin"
    SUPPORT = "support"
    FINANCE = "finance"
    DEVELOPER = "developer"


# ============================================
# MODELS
# ============================================
class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    email = Column(String(255), unique=True, nullable=False, index=True)
    name = Column(String(255))
    stripe_customer_id = Column(String, unique=True, index=True)
    keycloak_user_id = Column(String, unique=True, index=True)
    avatar_url = Column(Text)
    metadata = Column(JSONB, server_default='{}')
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())

    # Relationships
    subscriptions = relationship("Subscription", back_populates="user", cascade="all, delete-orphan")
    service_access = relationship("ServiceAccess", back_populates="user", cascade="all, delete-orphan")
    payments = relationship("Payment", back_populates="user")
    generations = relationship("Generation", back_populates="user", cascade="all, delete-orphan")
    api_keys = relationship("APIKey", back_populates="user", cascade="all, delete-orphan")
    events = relationship("Event", back_populates="user")


class Subscription(Base):
    __tablename__ = "subscriptions"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    plan = Column(Enum(SubscriptionPlan), nullable=False)
    status = Column(Enum(SubscriptionStatus), nullable=False, default=SubscriptionStatus.ACTIVE, index=True)
    stripe_subscription_id = Column(String, unique=True, index=True)
    stripe_price_id = Column(String)
    current_period_start = Column(TIMESTAMP)
    current_period_end = Column(TIMESTAMP)
    cancel_at_period_end = Column(Boolean, default=False)
    canceled_at = Column(TIMESTAMP)
    metadata = Column(JSONB, server_default='{}')
    created_at = Column(TIMESTAMP, server_default=func.now(), index=True)
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())

    # Relationships
    user = relationship("User", back_populates="subscriptions")
    payments = relationship("Payment", back_populates="subscription")


class ServiceAccess(Base):
    __tablename__ = "service_access"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    service = Column(String(100), nullable=False, index=True)
    unlocked_at = Column(TIMESTAMP, server_default=func.now())
    locked = Column(Boolean, default=False)
    metadata = Column(JSONB, server_default='{}')
    created_at = Column(TIMESTAMP, server_default=func.now())

    __table_args__ = (
        UniqueConstraint('user_id', 'service', name='uq_user_service'),
        Index('idx_service_access_unlocked', 'user_id', 'service', postgresql_where=(locked == False)),
    )

    # Relationships
    user = relationship("User", back_populates="service_access")


class Payment(Base):
    __tablename__ = "payments"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), index=True)
    subscription_id = Column(UUID(as_uuid=True), ForeignKey("subscriptions.id", ondelete="SET NULL"), index=True)
    stripe_payment_intent_id = Column(String, unique=True, index=True)
    stripe_invoice_id = Column(String)
    amount = Column(Integer, nullable=False)  # Centimes
    currency = Column(String(3), default='eur')
    status = Column(Enum(PaymentStatus), nullable=False, index=True)
    payment_method = Column(String(50))
    metadata = Column(JSONB, server_default='{}')
    created_at = Column(TIMESTAMP, server_default=func.now(), index=True)

    # Relationships
    user = relationship("User", back_populates="payments")
    subscription = relationship("Subscription", back_populates="payments")


class Generation(Base):
    __tablename__ = "generations"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    service = Column(String(100), nullable=False, index=True)
    prompt = Column(Text)
    output = Column(Text)
    tokens_used = Column(Integer)
    personalization_score = Column(Float)
    metadata = Column(JSONB, server_default='{}')
    created_at = Column(TIMESTAMP, server_default=func.now(), index=True)

    __table_args__ = (
        Index('idx_generations_user_service', 'user_id', 'service', 'created_at'),
        Index('idx_generations_user_created', 'user_id', 'created_at'),
    )

    # Relationships
    user = relationship("User", back_populates="generations")


class ServiceConfig(Base):
    __tablename__ = "service_configs"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    service = Column(String(100), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    slug = Column(String(255), unique=True, nullable=False, index=True)
    type = Column(String(50))
    description = Column(Text)
    pricing_monthly = Column(Integer)
    pricing_annual = Column(Integer)
    rate_limit_daily = Column(Integer, default=100)
    rate_limit_monthly = Column(Integer, default=3000)
    enabled = Column(Boolean, default=True, index=True)
    config = Column(JSONB, server_default='{}')
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())
    created_at = Column(TIMESTAMP, server_default=func.now())


class AdminUser(Base):
    __tablename__ = "admin_users"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    email = Column(String(255), unique=True, nullable=False, index=True)
    role = Column(Enum(AdminRole), nullable=False, default=AdminRole.SUPPORT, index=True)
    keycloak_user_id = Column(String, unique=True)
    last_login_at = Column(TIMESTAMP)
    metadata = Column(JSONB, server_default='{}')
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())

    # Relationships
    audit_logs = relationship("AuditLog", back_populates="admin_user")


class FeatureFlag(Base):
    __tablename__ = "feature_flags"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    flag_key = Column(String(100), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    enabled = Column(Boolean, default=False, index=True)
    rollout_percentage = Column(Integer, default=100)
    config = Column(JSONB, server_default='{}')
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())
    created_at = Column(TIMESTAMP, server_default=func.now())


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    admin_user_id = Column(UUID(as_uuid=True), ForeignKey("admin_users.id", ondelete="SET NULL"), index=True)
    action = Column(String(100), nullable=False, index=True)
    entity_type = Column(String(50))
    entity_id = Column(UUID(as_uuid=True))
    metadata = Column(JSONB, server_default='{}')
    created_at = Column(TIMESTAMP, server_default=func.now(), index=True)

    __table_args__ = (
        Index('idx_audit_logs_entity', 'entity_type', 'entity_id'),
    )

    # Relationships
    admin_user = relationship("AdminUser", back_populates="audit_logs")


class Event(Base):
    __tablename__ = "events"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), index=True)
    event_type = Column(String(100), nullable=False, index=True)
    service = Column(String(100), index=True)
    metadata = Column(JSONB, server_default='{}')
    ip_address = Column(INET)
    user_agent = Column(Text)
    created_at = Column(TIMESTAMP, server_default=func.now(), index=True)

    __table_args__ = (
        Index('idx_events_type_created', 'event_type', 'created_at'),
        Index('idx_events_user_created', 'user_id', 'created_at'),
    )

    # Relationships
    user = relationship("User", back_populates="events")


class APIKey(Base):
    __tablename__ = "api_keys"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    key_hash = Column(String(255), unique=True, nullable=False, index=True)
    key_prefix = Column(String(20), nullable=False)
    name = Column(String(255))
    last_used_at = Column(TIMESTAMP)
    expires_at = Column(TIMESTAMP)
    revoked = Column(Boolean, default=False)
    metadata = Column(JSONB, server_default='{}')
    created_at = Column(TIMESTAMP, server_default=func.now())

    # Relationships
    user = relationship("User", back_populates="api_keys")


class EmailTemplate(Base):
    __tablename__ = "email_templates"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    template_key = Column(String(100), unique=True, nullable=False, index=True)
    subject = Column(String(255), nullable=False)
    body_html = Column(Text, nullable=False)
    body_text = Column(Text)
    variables = Column(JSONB, server_default='[]')
    metadata = Column(JSONB, server_default='{}')
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())
    created_at = Column(TIMESTAMP, server_default=func.now())


class EmailQueue(Base):
    __tablename__ = "email_queue"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), index=True)
    template_key = Column(String(100), nullable=False)
    to_email = Column(String(255), nullable=False)
    subject = Column(String(255), nullable=False)
    body_html = Column(Text, nullable=False)
    variables = Column(JSONB, server_default='{}')
    status = Column(String(50), default='pending', index=True)
    sent_at = Column(TIMESTAMP)
    error_message = Column(Text)
    metadata = Column(JSONB, server_default='{}')
    created_at = Column(TIMESTAMP, server_default=func.now(), index=True)


# ============================================
# DEPENDENCY INJECTION
# ============================================
async def get_db() -> AsyncSession:
    """
    Dependency for FastAPI routes
    """
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
