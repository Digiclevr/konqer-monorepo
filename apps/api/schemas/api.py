"""
Pydantic schemas for API validation
"""
from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional, Dict, Any, List
from datetime import datetime
from uuid import UUID


# ===== User Schemas =====
class UserProfile(BaseModel):
    id: str
    email: EmailStr
    name: Optional[str] = None
    avatar_url: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class UserSubscriptionResponse(BaseModel):
    id: str
    plan: str
    status: str
    current_period_end: Optional[datetime] = None

    class Config:
        from_attributes = True


class ServiceAccessResponse(BaseModel):
    service: str
    unlocked_at: datetime

    class Config:
        from_attributes = True


# ===== Service Schemas =====
class GenerateRequest(BaseModel):
    prompt: str = Field(..., min_length=10, max_length=5000, description="User prompt for generation")
    context: Dict[str, Any] = Field(default_factory=dict, description="Additional context (company, role, etc.)")

    @field_validator('prompt')
    @classmethod
    def prompt_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError('Prompt cannot be empty')
        return v.strip()


class GenerateResponse(BaseModel):
    id: str
    service: str
    output: str
    personalization_score: Optional[float] = None
    tokens_used: Optional[int] = None
    created_at: datetime

    class Config:
        from_attributes = True


class GenerationHistory(BaseModel):
    id: str
    service: str
    prompt: str
    output: str
    personalization_score: Optional[float] = None
    created_at: datetime

    class Config:
        from_attributes = True


# ===== Checkout Schemas =====
class CheckoutRequest(BaseModel):
    plan: str = Field(
        ...,
        pattern="^(founding|monthly_single|monthly_bundle|annual_single|annual_bundle)$",
        description="Subscription plan type"
    )


class CheckoutResponse(BaseModel):
    checkout_url: str
    session_id: str


class CustomerPortalResponse(BaseModel):
    portal_url: str


# ===== Service Config Schemas =====
class ServiceConfigResponse(BaseModel):
    service: str
    name: str
    slug: str
    type: Optional[str] = None
    description: Optional[str] = None
    pricing_monthly: Optional[int] = None
    pricing_annual: Optional[int] = None
    enabled: bool
    config: Dict[str, Any]

    class Config:
        from_attributes = True


# ===== Admin Schemas =====
class UserListItem(BaseModel):
    id: str
    email: EmailStr
    name: Optional[str] = None
    stripe_customer_id: Optional[str] = None
    created_at: datetime


class UserListResponse(BaseModel):
    users: List[UserListItem]
    total: int
    skip: int
    limit: int


class MRRMetrics(BaseModel):
    mrr: float
    arr: float
    active_subscriptions: int
    subscription_breakdown: Dict[str, int]
    currency: str
    generated_at: datetime


class RevenueMetrics(BaseModel):
    total_revenue: float
    payment_count: int
    average_payment: float
    period_days: int
    currency: str


class UsageByService(BaseModel):
    service: str
    count: int


class UsageAnalytics(BaseModel):
    usage_by_service: List[UsageByService]
    total_generations: int
    unique_users: int
    period_days: int


# ===== Error Schemas =====
class ErrorResponse(BaseModel):
    error: str
    message: str
    details: Optional[Dict[str, Any]] = None


# ===== Health Check =====
class HealthCheck(BaseModel):
    status: str
    service: str
    version: str
