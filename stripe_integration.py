import os
import stripe
import logging
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger("off-grid-api.stripe")

stripe.api_key = os.getenv("STRIPE_SECRET_KEY", "")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:8888")

# Price IDs - set these after creating products in Stripe Dashboard
PRICE_IDS = {
    "scout": os.getenv("STRIPE_PRICE_SCOUT", ""),
    "pioneer": os.getenv("STRIPE_PRICE_PIONEER", ""),
    "lifetime": os.getenv("STRIPE_PRICE_LIFETIME", ""),
}

def create_checkout_session(plan: str, customer_email: str = None) -> dict:
    """Create a Stripe Checkout session for the given plan."""
    if plan not in PRICE_IDS:
        raise ValueError(f"Invalid plan: {plan}. Choose from: {list(PRICE_IDS.keys())}")
    
    price_id = PRICE_IDS[plan]
    if not price_id:
        raise ValueError(f"Price ID not configured for plan: {plan}. Set STRIPE_PRICE_{plan.upper()} in .env")
    
    mode = "payment" if plan == "lifetime" else "subscription"
    
    session_params = {
        "payment_method_types": ["card"],
        "line_items": [{"price": price_id, "quantity": 1}],
        "mode": mode,
        "success_url": f"{FRONTEND_URL}/static/success.html?session_id={{CHECKOUT_SESSION_ID}}",
        "cancel_url": f"{FRONTEND_URL}/#pricing",
        "metadata": {"plan": plan},
    }
    
    if customer_email:
        session_params["customer_email"] = customer_email
    
    session = stripe.checkout.Session.create(**session_params)
    logger.info(f"Checkout session created: {session.id} for plan: {plan}")
    return {"checkout_url": session.url, "session_id": session.id}


def handle_webhook(payload: bytes, sig_header: str) -> dict:
    """Handle Stripe webhook events."""
    try:
        event = stripe.Webhook.construct_event(payload, sig_header, STRIPE_WEBHOOK_SECRET)
    except (ValueError, stripe.error.SignatureVerificationError) as e:
        logger.error(f"Webhook verification failed: {e}")
        raise ValueError(f"Webhook error: {e}")
    
    event_type = event["type"]
    data = event["data"]["object"]
    
    if event_type == "checkout.session.completed":
        customer_email = data.get("customer_email", "")
        plan = data.get("metadata", {}).get("plan", "unknown")
        logger.info(f"Payment completed: {customer_email} -> {plan}")
        # TODO: Activate user account, generate API key, send welcome email
        return {"status": "success", "event": event_type, "email": customer_email, "plan": plan}
    
    elif event_type == "customer.subscription.deleted":
        customer_id = data.get("customer", "")
        logger.info(f"Subscription cancelled: {customer_id}")
        # TODO: Deactivate user account
        return {"status": "success", "event": event_type, "customer": customer_id}
    
    elif event_type == "invoice.payment_failed":
        customer_email = data.get("customer_email", "")
        logger.warning(f"Payment failed: {customer_email}")
        # TODO: Notify user of failed payment
        return {"status": "success", "event": event_type, "email": customer_email}
    
    logger.info(f"Unhandled webhook event: {event_type}")
    return {"status": "ignored", "event": event_type}


def get_customer_portal_url(customer_id: str) -> str:
    """Create a Stripe Customer Portal session for managing subscriptions."""
    session = stripe.billing_portal.Session.create(
        customer=customer_id,
        return_url=f"{FRONTEND_URL}/",
    )
    return session.url
