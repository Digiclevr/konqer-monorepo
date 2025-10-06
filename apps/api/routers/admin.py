"""
Admin router - Internal operations (port-forward only)
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime, timedelta
from typing import List, Optional
import logging

from models.database import (
    get_db, User, Subscription, Payment, Generation,
    ServiceAccess, ServiceConfig, AuditLog
)
from routers.auth import get_current_user

router = APIRouter()
logger = logging.getLogger(__name__)


# TODO: Implement admin role check
# For now, admin routes are protected by port-forward only
# In production, add decorator: @require_admin_role


@router.get("/metrics/mrr")
async def get_mrr(
    db: AsyncSession = Depends(get_db)
):
    """
    Get Monthly Recurring Revenue
    """
    # Query active subscriptions
    result = await db.execute(
        select(Subscription).where(Subscription.status == 'active')
    )
    subscriptions = result.scalars().all()

    # Calculate MRR
    mrr = 0.0
    subscription_breakdown = {
        'founding': 0,
        'monthly_single': 0,
        'monthly_bundle': 0,
        'annual_single': 0,
        'annual_bundle': 0
    }

    for sub in subscriptions:
        if sub.plan == 'founding':
            mrr += 699 / 12  # Annual divided by 12
            subscription_breakdown['founding'] += 1
        elif sub.plan == 'monthly_single':
            mrr += 99
            subscription_breakdown['monthly_single'] += 1
        elif sub.plan == 'monthly_bundle':
            mrr += 399
            subscription_breakdown['monthly_bundle'] += 1
        elif sub.plan == 'annual_single':
            mrr += 990 / 12
            subscription_breakdown['annual_single'] += 1
        elif sub.plan == 'annual_bundle':
            mrr += 3990 / 12
            subscription_breakdown['annual_bundle'] += 1

    return {
        "mrr": round(mrr, 2),
        "arr": round(mrr * 12, 2),
        "active_subscriptions": len(subscriptions),
        "subscription_breakdown": subscription_breakdown,
        "currency": "eur",
        "generated_at": datetime.now()
    }


@router.get("/metrics/revenue")
async def get_revenue_metrics(
    db: AsyncSession = Depends(get_db),
    days: int = 30
):
    """
    Get revenue metrics for last N days
    """
    start_date = datetime.now() - timedelta(days=days)

    # Total revenue
    result = await db.execute(
        select(func.sum(Payment.amount))
        .where(Payment.status == 'succeeded')
        .where(Payment.created_at >= start_date)
    )
    total_revenue = result.scalar() or 0

    # Payment count
    result = await db.execute(
        select(func.count(Payment.id))
        .where(Payment.status == 'succeeded')
        .where(Payment.created_at >= start_date)
    )
    payment_count = result.scalar() or 0

    return {
        "total_revenue": total_revenue / 100,  # Convert from cents
        "payment_count": payment_count,
        "average_payment": (total_revenue / payment_count / 100) if payment_count > 0 else 0,
        "period_days": days,
        "currency": "eur"
    }


@router.get("/users")
async def list_users(
    db: AsyncSession = Depends(get_db),
    skip: int = 0,
    limit: int = 50,
    search: Optional[str] = None
):
    """
    List all users (pagination + search)
    """
    query = select(User)

    if search:
        query = query.where(
            (User.email.ilike(f"%{search}%")) |
            (User.name.ilike(f"%{search}%"))
        )

    query = query.offset(skip).limit(limit).order_by(User.created_at.desc())

    result = await db.execute(query)
    users = result.scalars().all()

    # Get total count
    count_query = select(func.count(User.id))
    if search:
        count_query = count_query.where(
            (User.email.ilike(f"%{search}%")) |
            (User.name.ilike(f"%{search}%"))
        )
    result = await db.execute(count_query)
    total = result.scalar()

    return {
        "users": [
            {
                "id": str(user.id),
                "email": user.email,
                "name": user.name,
                "stripe_customer_id": user.stripe_customer_id,
                "created_at": user.created_at
            }
            for user in users
        ],
        "total": total,
        "skip": skip,
        "limit": limit
    }


@router.get("/users/{user_id}")
async def get_user_details(
    user_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Get detailed user information
    """
    # Get user
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(404, "User not found")

    # Get subscriptions
    result = await db.execute(
        select(Subscription)
        .where(Subscription.user_id == user_id)
        .order_by(Subscription.created_at.desc())
    )
    subscriptions = result.scalars().all()

    # Get service access
    result = await db.execute(
        select(ServiceAccess).where(ServiceAccess.user_id == user_id)
    )
    services = result.scalars().all()

    # Get generation count
    result = await db.execute(
        select(func.count(Generation.id)).where(Generation.user_id == user_id)
    )
    generation_count = result.scalar()

    # Get total spent
    result = await db.execute(
        select(func.sum(Payment.amount))
        .where(Payment.user_id == user_id)
        .where(Payment.status == 'succeeded')
    )
    total_spent = result.scalar() or 0

    return {
        "user": {
            "id": str(user.id),
            "email": user.email,
            "name": user.name,
            "stripe_customer_id": user.stripe_customer_id,
            "created_at": user.created_at
        },
        "subscriptions": [
            {
                "id": str(sub.id),
                "plan": sub.plan,
                "status": sub.status,
                "created_at": sub.created_at,
                "current_period_end": sub.current_period_end
            }
            for sub in subscriptions
        ],
        "services": [
            {
                "service": svc.service,
                "unlocked_at": svc.unlocked_at,
                "locked": svc.locked
            }
            for svc in services
        ],
        "stats": {
            "generation_count": generation_count,
            "total_spent": total_spent / 100,
            "currency": "eur"
        }
    }


@router.post("/users/{user_id}/unlock/{service}")
async def unlock_service_for_user(
    user_id: str,
    service: str,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_user)  # TODO: Check admin role
):
    """
    Manually unlock a service for a user
    """
    # Check if user exists
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(404, "User not found")

    # Check if service exists
    result = await db.execute(select(ServiceConfig).where(ServiceConfig.service == service))
    service_config = result.scalar_one_or_none()

    if not service_config:
        raise HTTPException(404, "Service not found")

    # Check if already has access
    result = await db.execute(
        select(ServiceAccess)
        .where(ServiceAccess.user_id == user_id)
        .where(ServiceAccess.service == service)
    )
    existing = result.scalar_one_or_none()

    if existing:
        if not existing.locked:
            return {"message": "Service already unlocked"}

        # Unlock
        existing.locked = False
        existing.unlocked_at = datetime.now()
    else:
        # Create new access
        access = ServiceAccess(
            user_id=user_id,
            service=service,
            locked=False
        )
        db.add(access)

    # Log action
    audit_log = AuditLog(
        admin_user_id=current_admin.id,
        action="service.unlock",
        entity_type="service_access",
        metadata={
            "user_id": user_id,
            "service": service
        }
    )
    db.add(audit_log)

    await db.commit()

    logger.info(f"Admin {current_admin.id} unlocked {service} for user {user_id}")

    return {"message": f"Service {service} unlocked for user"}


@router.put("/services/{service}/config")
async def update_service_config(
    service: str,
    config_update: dict,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_user)  # TODO: Check admin role
):
    """
    Update service configuration
    """
    result = await db.execute(select(ServiceConfig).where(ServiceConfig.service == service))
    service_config = result.scalar_one_or_none()

    if not service_config:
        raise HTTPException(404, "Service not found")

    # Update allowed fields
    allowed_fields = [
        'name', 'description', 'pricing_monthly', 'pricing_annual',
        'rate_limit_daily', 'rate_limit_monthly', 'enabled', 'config'
    ]

    for field, value in config_update.items():
        if field in allowed_fields and hasattr(service_config, field):
            setattr(service_config, field, value)

    service_config.updated_at = datetime.now()

    # Log action
    audit_log = AuditLog(
        admin_user_id=current_admin.id,
        action="service.config.update",
        entity_type="service_config",
        entity_id=service_config.id,
        metadata=config_update
    )
    db.add(audit_log)

    await db.commit()

    logger.info(f"Admin {current_admin.id} updated config for {service}")

    return {"message": "Service config updated"}


@router.get("/analytics/usage")
async def get_usage_analytics(
    db: AsyncSession = Depends(get_db),
    days: int = 7
):
    """
    Get service usage analytics
    """
    start_date = datetime.now() - timedelta(days=days)

    # Generations by service
    result = await db.execute(
        select(
            Generation.service,
            func.count(Generation.id).label('count')
        )
        .where(Generation.created_at >= start_date)
        .group_by(Generation.service)
        .order_by(func.count(Generation.id).desc())
    )
    usage_by_service = [
        {"service": row[0], "count": row[1]}
        for row in result.all()
    ]

    # Total generations
    result = await db.execute(
        select(func.count(Generation.id))
        .where(Generation.created_at >= start_date)
    )
    total_generations = result.scalar()

    # Unique users
    result = await db.execute(
        select(func.count(func.distinct(Generation.user_id)))
        .where(Generation.created_at >= start_date)
    )
    unique_users = result.scalar()

    return {
        "usage_by_service": usage_by_service,
        "total_generations": total_generations,
        "unique_users": unique_users,
        "period_days": days
    }
