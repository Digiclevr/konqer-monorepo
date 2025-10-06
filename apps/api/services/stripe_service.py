"""
Stripe Service - Payment processing
"""
import stripe
from typing import Dict, Any
from config import settings
import logging

logger = logging.getLogger(__name__)

stripe.api_key = settings.STRIPE_SECRET_KEY


class StripeService:
    async def create_checkout_session(
        self,
        user_id: str,
        email: str,
        plan: str = "founding",
        success_url: str = "https://konqer.app/success",
        cancel_url: str = "https://konqer.app/pricing"
    ) -> Dict[str, Any]:
        """
        Create Stripe Checkout Session

        Args:
            user_id: User UUID
            email: User email
            plan: 'founding', 'monthly_single', 'monthly_bundle', etc.
        """
        # Get price ID based on plan
        price_id = self._get_price_id(plan)

        session = stripe.checkout.Session.create(
            customer_email=email,
            payment_method_types=['card', 'paypal'],
            line_items=[{
                'price': price_id,
                'quantity': 1,
            }],
            mode='subscription',
            success_url=f"{success_url}?session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=cancel_url,
            metadata={
                'user_id': user_id,
                'plan': plan
            },
            subscription_data={
                'metadata': {
                    'user_id': user_id,
                    'plan': plan
                }
            }
        )

        return {
            "checkout_url": session.url,
            "session_id": session.id
        }

    async def create_customer_portal_session(
        self,
        stripe_customer_id: str,
        return_url: str = "https://konqer.app/dashboard"
    ) -> Dict[str, Any]:
        """
        Create Customer Portal session for subscription management
        """
        session = stripe.billing_portal.Session.create(
            customer=stripe_customer_id,
            return_url=return_url,
        )

        return {
            "portal_url": session.url
        }

    def _get_price_id(self, plan: str) -> str:
        """
        Map plan to Stripe Price ID
        These should be created in Stripe Dashboard first
        """
        price_mapping = {
            "founding": settings.STRIPE_FOUNDING_PRICE_ID,
            "monthly_single": "price_monthly_single_99eur",
            "monthly_bundle": "price_monthly_bundle_399eur",
            "annual_single": "price_annual_single_990eur",
            "annual_bundle": "price_annual_bundle_3990eur",
        }

        return price_mapping.get(plan, settings.STRIPE_FOUNDING_PRICE_ID)

    async def verify_webhook_signature(
        self,
        payload: bytes,
        sig_header: str
    ) -> stripe.Event:
        """
        Verify Stripe webhook signature
        """
        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
            )
            return event
        except ValueError:
            logger.error("Invalid payload")
            raise
        except stripe.error.SignatureVerificationError:
            logger.error("Invalid signature")
            raise
