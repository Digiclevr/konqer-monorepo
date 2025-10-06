"""
Webhooks router - Stripe events
"""
from fastapi import APIRouter, Request, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime
import logging

from models.database import get_db, User, Subscription, Payment, ServiceAccess
from services.stripe_service import StripeService

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/stripe")
async def stripe_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Handle Stripe webhook events
    """
    payload = await request.body()
    sig_header = request.headers.get('stripe-signature')

    stripe_service = StripeService()

    try:
        event = await stripe_service.verify_webhook_signature(payload, sig_header)
    except Exception as e:
        logger.error(f"Webhook signature verification failed: {e}")
        raise HTTPException(400, "Invalid signature")

    # Handle event types
    event_type = event['type']
    logger.info(f"Received Stripe event: {event_type}")

    if event_type == 'checkout.session.completed':
        await handle_checkout_completed(event, db)
    elif event_type == 'customer.subscription.updated':
        await handle_subscription_updated(event, db)
    elif event_type == 'customer.subscription.deleted':
        await handle_subscription_deleted(event, db)
    elif event_type == 'invoice.payment_succeeded':
        await handle_payment_succeeded(event, db)
    elif event_type == 'invoice.payment_failed':
        await handle_payment_failed(event, db)
    else:
        logger.info(f"Unhandled event type: {event_type}")

    return {"status": "success"}


async def handle_checkout_completed(event, db: AsyncSession):
    """
    Handle checkout.session.completed
    Create subscription and unlock initial services
    """
    session = event['data']['object']
    user_id = session['metadata'].get('user_id')
    plan = session['metadata'].get('plan')

    if not user_id or not plan:
        logger.error(f"Missing metadata in checkout session: {session['id']}")
        return

    # Get user
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        logger.error(f"User {user_id} not found")
        return

    # Update Stripe customer ID
    if not user.stripe_customer_id and session.get('customer'):
        user.stripe_customer_id = session['customer']

    # Create subscription
    subscription = Subscription(
        user_id=user_id,
        plan=plan,
        status='active',
        stripe_subscription_id=session.get('subscription'),
        stripe_price_id=session.get('price_id'),
        current_period_start=datetime.now(),
        current_period_end=datetime.fromtimestamp(session.get('expires_at', 0)) if session.get('expires_at') else None
    )
    db.add(subscription)

    # Unlock initial services based on plan
    if plan == 'founding':
        # Founding Members: unlock 3 initial services
        initial_services = ['cold-dm', 'objection', 'carousel']
        for service in initial_services:
            # Check if already exists
            result = await db.execute(
                select(ServiceAccess)
                .where(ServiceAccess.user_id == user_id)
                .where(ServiceAccess.service == service)
            )
            existing = result.scalar_one_or_none()

            if not existing:
                access = ServiceAccess(user_id=user_id, service=service, locked=False)
                db.add(access)
    elif 'single' in plan:
        # Single service plan - unlock the specific service
        # TODO: Get service from plan metadata
        pass
    elif 'bundle' in plan:
        # Bundle: unlock all 12 services
        all_services = [
            'cold-dm', 'battlecards', 'objection', 'community-finder',
            'carousel', 'cold-email', 'pitch-deck', 'whitepaper',
            'deck-heatmap', 'webinar', 'warmranker', 'no-show-shield'
        ]
        for service in all_services:
            result = await db.execute(
                select(ServiceAccess)
                .where(ServiceAccess.user_id == user_id)
                .where(ServiceAccess.service == service)
            )
            existing = result.scalar_one_or_none()

            if not existing:
                access = ServiceAccess(user_id=user_id, service=service, locked=False)
                db.add(access)

    await db.commit()
    logger.info(f"Subscription created for user {user_id}, plan {plan}")

    # TODO: Send welcome email
    # await send_email(user_id, 'founding_welcome' if plan == 'founding' else 'subscription_welcome')


async def handle_subscription_updated(event, db: AsyncSession):
    """
    Handle subscription updates
    """
    subscription_data = event['data']['object']
    stripe_sub_id = subscription_data['id']

    result = await db.execute(
        select(Subscription).where(Subscription.stripe_subscription_id == stripe_sub_id)
    )
    subscription = result.scalar_one_or_none()

    if subscription:
        subscription.status = subscription_data['status']
        subscription.current_period_start = datetime.fromtimestamp(subscription_data['current_period_start'])
        subscription.current_period_end = datetime.fromtimestamp(subscription_data['current_period_end'])
        subscription.cancel_at_period_end = subscription_data.get('cancel_at_period_end', False)

        await db.commit()
        logger.info(f"Subscription {stripe_sub_id} updated: {subscription_data['status']}")


async def handle_subscription_deleted(event, db: AsyncSession):
    """
    Handle subscription cancellation
    """
    subscription_data = event['data']['object']
    stripe_sub_id = subscription_data['id']

    result = await db.execute(
        select(Subscription).where(Subscription.stripe_subscription_id == stripe_sub_id)
    )
    subscription = result.scalar_one_or_none()

    if subscription:
        subscription.status = 'canceled'
        subscription.canceled_at = datetime.now()

        await db.commit()
        logger.info(f"Subscription {stripe_sub_id} canceled")

        # TODO: Send cancellation email


async def handle_payment_succeeded(event, db: AsyncSession):
    """
    Record successful payment
    """
    invoice = event['data']['object']
    customer_id = invoice['customer']

    result = await db.execute(
        select(User).where(User.stripe_customer_id == customer_id)
    )
    user = result.scalar_one_or_none()

    if user:
        payment = Payment(
            user_id=user.id,
            stripe_payment_intent_id=invoice.get('payment_intent'),
            stripe_invoice_id=invoice['id'],
            amount=invoice['amount_paid'],
            currency=invoice['currency'],
            status='succeeded',
            payment_method=invoice.get('payment_method_types', [None])[0] if invoice.get('payment_method_types') else None
        )
        db.add(payment)
        await db.commit()

        logger.info(f"Payment succeeded for user {user.id}: {invoice['amount_paid']} {invoice['currency']}")


async def handle_payment_failed(event, db: AsyncSession):
    """
    Handle failed payment
    """
    invoice = event['data']['object']
    customer_id = invoice['customer']

    result = await db.execute(
        select(User).where(User.stripe_customer_id == customer_id)
    )
    user = result.scalar_one_or_none()

    if user:
        payment = Payment(
            user_id=user.id,
            stripe_invoice_id=invoice['id'],
            amount=invoice['amount_due'],
            currency=invoice['currency'],
            status='failed'
        )
        db.add(payment)
        await db.commit()

        logger.warning(f"Payment failed for user {user.id}: {invoice['amount_due']} {invoice['currency']}")

        # TODO: Send payment failed email notification
