"""
User router - Profile, subscriptions, history
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
import logging

from models.database import get_db, User, Subscription, ServiceAccess, Generation
from routers.auth import get_current_user
from schemas.api import (
    UserProfile, UserSubscriptionResponse,
    ServiceAccessResponse, GenerationHistory
)

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/me", response_model=UserProfile)
async def get_user_profile(
    current_user: User = Depends(get_current_user)
):
    """
    Get current user profile
    """
    return {
        "id": str(current_user.id),
        "email": current_user.email,
        "name": current_user.name,
        "avatar_url": current_user.avatar_url,
        "created_at": current_user.created_at
    }


@router.get("/subscriptions", response_model=List[UserSubscriptionResponse])
async def get_user_subscriptions(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get user's active subscriptions
    """
    result = await db.execute(
        select(Subscription)
        .where(Subscription.user_id == current_user.id)
        .order_by(Subscription.created_at.desc())
    )
    subscriptions = result.scalars().all()

    return [
        {
            "id": str(sub.id),
            "plan": sub.plan,
            "status": sub.status,
            "current_period_end": sub.current_period_end
        }
        for sub in subscriptions
    ]


@router.get("/services", response_model=List[ServiceAccessResponse])
async def get_user_services(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get list of services accessible to user
    """
    result = await db.execute(
        select(ServiceAccess)
        .where(ServiceAccess.user_id == current_user.id)
        .where(ServiceAccess.locked == False)
        .order_by(ServiceAccess.unlocked_at)
    )
    access_list = result.scalars().all()

    return [
        {
            "service": access.service,
            "unlocked_at": access.unlocked_at
        }
        for access in access_list
    ]


@router.get("/history", response_model=List[GenerationHistory])
async def get_user_history(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    service: str = None,
    limit: int = 20,
    offset: int = 0
):
    """
    Get user's generation history (all services or filtered)
    """
    query = select(Generation).where(Generation.user_id == current_user.id)

    if service:
        query = query.where(Generation.service == service)

    query = (
        query
        .order_by(Generation.created_at.desc())
        .limit(limit)
        .offset(offset)
    )

    result = await db.execute(query)
    generations = result.scalars().all()

    return [
        {
            "id": str(gen.id),
            "service": gen.service,
            "prompt": gen.prompt,
            "output": gen.output,
            "personalization_score": gen.personalization_score,
            "created_at": gen.created_at
        }
        for gen in generations
    ]


@router.post("/checkout")
async def create_checkout_session(
    plan: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Create Stripe checkout session
    """
    from services.stripe_service import StripeService

    stripe_service = StripeService()

    try:
        session = await stripe_service.create_checkout_session(
            user_id=str(current_user.id),
            email=current_user.email,
            plan=plan
        )

        return session

    except Exception as e:
        logger.error(f"Checkout creation failed: {e}")
        raise HTTPException(500, "Failed to create checkout session")


@router.post("/portal")
async def create_customer_portal(
    current_user: User = Depends(get_current_user)
):
    """
    Create Stripe Customer Portal session
    """
    from services.stripe_service import StripeService

    if not current_user.stripe_customer_id:
        raise HTTPException(400, "No active subscription")

    stripe_service = StripeService()

    try:
        portal = await stripe_service.create_customer_portal_session(
            stripe_customer_id=current_user.stripe_customer_id
        )

        return portal

    except Exception as e:
        logger.error(f"Portal creation failed: {e}")
        raise HTTPException(500, "Failed to create portal session")
