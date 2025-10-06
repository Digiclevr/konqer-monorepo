"""
Services router - Generation endpoints for 12 services
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime, timedelta
import logging

from models.database import get_db, User, ServiceAccess, Generation, ServiceConfig
from routers.auth import get_current_user
from services.openai_service import OpenAIService
from schemas.api import GenerateRequest, GenerateResponse

router = APIRouter()
logger = logging.getLogger(__name__)


async def check_service_access(
    user: User,
    service: str,
    db: AsyncSession
) -> bool:
    """
    Check if user has access to service
    """
    result = await db.execute(
        select(ServiceAccess)
        .where(ServiceAccess.user_id == user.id)
        .where(ServiceAccess.service == service)
        .where(ServiceAccess.locked == False)
    )
    access = result.scalar_one_or_none()
    return access is not None


async def check_rate_limit(
    user: User,
    service: str,
    db: AsyncSession
) -> bool:
    """
    Check if user has exceeded daily rate limit
    """
    # Get service config
    result = await db.execute(
        select(ServiceConfig).where(ServiceConfig.service == service)
    )
    config = result.scalar_one_or_none()

    if not config:
        return True  # Service not found, allow

    daily_limit = config.rate_limit_daily

    # Count today's generations
    today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

    result = await db.execute(
        select(func.count(Generation.id))
        .where(Generation.user_id == user.id)
        .where(Generation.service == service)
        .where(Generation.created_at >= today_start)
    )
    count = result.scalar()

    return count < daily_limit


@router.get("/config/{service}")
async def get_service_config(
    service: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Get service configuration (public endpoint for frontend)
    """
    result = await db.execute(
        select(ServiceConfig).where(ServiceConfig.service == service)
    )
    config = result.scalar_one_or_none()

    if not config:
        raise HTTPException(404, "Service not found")

    return {
        "service": config.service,
        "name": config.name,
        "slug": config.slug,
        "type": config.type,
        "description": config.description,
        "pricing_monthly": config.pricing_monthly,
        "pricing_annual": config.pricing_annual,
        "enabled": config.enabled,
        "config": config.config
    }


@router.post("/{service}/generate", response_model=GenerateResponse)
async def generate_service(
    service: str,
    request: GenerateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Generate content for a specific service
    """
    # 1. Check service access
    has_access = await check_service_access(current_user, service, db)
    if not has_access:
        raise HTTPException(403, f"Access to {service} is locked. Upgrade your plan.")

    # 2. Check rate limit
    within_limit = await check_rate_limit(current_user, service, db)
    if not within_limit:
        raise HTTPException(429, "Daily rate limit exceeded")

    # 3. Generate based on service
    openai_service = OpenAIService()
    personalization_score = None

    try:
        if service == "cold-dm":
            # Import Apollo service
            from services.apollo_service import ApolloService
            apollo_service = ApolloService()

            # Enrich context with Apollo
            enriched_context = await apollo_service.enrich_profile(request.context)

            result = await openai_service.generate_cold_dm(enriched_context)

            # Calculate personalization score
            personalization_score = calculate_personalization_score(
                result["message"], enriched_context
            )

            output = result["message"]
            tokens_used = result["tokens_used"]

        elif service == "objection":
            result = await openai_service.generate_objection_response(
                objection=request.prompt,
                context=request.context,
                framework=request.context.get("framework", "Cost vs Value")
            )
            output = result["response"]
            tokens_used = result["tokens_used"]

        elif service == "carousel":
            result = await openai_service.generate_carousel(
                topic=request.prompt,
                target_audience=request.context.get("target_audience", "B2B professionals")
            )
            output = result["carousel_structure"]
            tokens_used = result["tokens_used"]

        else:
            # Generic generation for other services
            result = await openai_service.generate_generic(
                service=service,
                prompt=request.prompt,
                system_prompt=request.context.get("system_prompt")
            )
            output = result["output"]
            tokens_used = result["tokens_used"]

    except Exception as e:
        logger.error(f"Generation failed for {service}: {e}")
        raise HTTPException(500, f"Generation failed: {str(e)}")

    # 4. Save generation
    generation = Generation(
        user_id=current_user.id,
        service=service,
        prompt=request.prompt,
        output=output,
        tokens_used=tokens_used,
        personalization_score=personalization_score,
        metadata=request.context
    )
    db.add(generation)
    await db.commit()
    await db.refresh(generation)

    return {
        "id": str(generation.id),
        "service": service,
        "output": output,
        "personalization_score": personalization_score,
        "tokens_used": tokens_used,
        "created_at": generation.created_at
    }


def calculate_personalization_score(message: str, context: dict) -> float:
    """
    Calculate personalization score (0-100)
    """
    score = 0.0

    # Name mentioned
    name = context.get("name", "")
    if name and name.split()[0].lower() in message.lower():
        score += 20

    # Company mentioned
    company = context.get("company", "")
    if company and company.lower() in message.lower():
        score += 15

    # Activity referenced
    for activity in context.get("recent_activity", []):
        keywords = activity.get("summary", "").lower().split()[:5]
        if any(kw in message.lower() for kw in keywords):
            score += 30
            break

    # Tech stack mentioned
    if any(tech.lower() in message.lower() for tech in context.get("tech_stack", [])):
        score += 20

    # Penalize generic phrases
    generic_phrases = [
        "i hope this message finds you well",
        "i came across your profile",
        "quick question",
        "touching base"
    ]
    for phrase in generic_phrases:
        if phrase in message.lower():
            score -= 10

    return max(0, min(100, score))
