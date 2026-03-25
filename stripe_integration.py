
import os
import stripe
import logging
import smtplib
from email.mime.text import MIMEText
from dotenv import load_dotenv
from auth import create_user, update_tier, deactivate_user, generate_api_key, _load_users, _save_users, _hash_key

load_dotenv()
logger = logging.getLogger("off-grid-api.stripe")

stripe.api_key = os.getenv("STRIPE_SECRET_KEY", "")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:8888")

# Price IDs - set these after creating products in Stripe Dashboard
PRICE_IDS = {
    "scout": os.getenv("STRIPE_PRICE_SCOUT", "price_1TEUEODq7JpYvSe24fMOocLX"),
    "pioneer": os.getenv("STRIPE_PRICE_PIONEER", "price_1TEUEODq7JpYvSe2YXcbhx5h"),
    "lifetime": os.getenv("STRIPE_PRICE_LIFETIME", "price_1TEUEPDq7JpYvSe2AHqdvC91"),
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
        customer_id = data.get("customer", "")
        subscription_id = data.get("subscription", "")
        plan = data.get("metadata", {}).get("plan", "scout")
        logger.info(f"Payment completed: {customer_email} -> {plan}")

        # Upgrade or create user at the paid tier
        result = create_user(
            email=customer_email,
            stripe_customer_id=customer_id,
            tier=plan,
        )
        # Also store subscription_id on the user record
        if subscription_id:
            update_tier(
                email=customer_email,
                stripe_customer_id=customer_id,
                tier=plan,
                subscription_id=subscription_id,
            )

        # Send welcome email with their API key
        _send_welcome_email(customer_email, result["api_key"], plan)
        logger.info(f"User activated: {customer_email} tier={plan} key={result['api_key'][:12]}...")
        return {"status": "success", "event": event_type, "email": customer_email, "plan": plan}

    elif event_type == "customer.subscription.updated":
        customer_id = data.get("customer", "")
        status = data.get("status", "")
        plan_id = data.get("items", {}).get("data", [{}])[0].get("price", {}).get("id", "")
        # Map price ID back to tier name
        reverse_map = {v: k for k, v in PRICE_IDS.items()}
        tier = reverse_map.get(plan_id, "scout")
        if status == "active":
            update_tier(stripe_customer_id=customer_id, tier=tier)
            logger.info(f"Subscription updated: {customer_id} -> {tier}")
        return {"status": "success", "event": event_type, "customer": customer_id}

    elif event_type == "customer.subscription.deleted":
        customer_id = data.get("customer", "")
        logger.info(f"Subscription cancelled: {customer_id}")
        deactivate_user(stripe_customer_id=customer_id)
        _send_cancellation_email_by_customer(customer_id)
        return {"status": "success", "event": event_type, "customer": customer_id}

    elif event_type == "invoice.payment_failed":
        customer_email = data.get("customer_email", "")
        logger.warning(f"Payment failed: {customer_email}")
        _send_payment_failed_email(customer_email)
        return {"status": "success", "event": event_type, "email": customer_email}
    
    logger.info(f"Unhandled webhook event: {event_type}")
    return {"status": "ignored", "event": event_type}


def _send_email(to: str, subject: str, body: str):
    """Send a plain-text email via SMTP."""
    smtp_host = os.getenv("SMTP_HOST")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USER")
    smtp_pass = os.getenv("SMTP_PASS")
    from_email = os.getenv("FROM_EMAIL", smtp_user)

    if not all([smtp_host, smtp_user, smtp_pass]):
        logger.warning("SMTP not configured — skipping email send")
        return

    try:
        msg = MIMEText(body, "plain")
        msg["Subject"] = subject
        msg["From"] = f"Off-Grid Scout <{from_email}>"
        msg["To"] = to
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.sendmail(from_email, to, msg.as_string())
        logger.info(f"Email sent to {to}: {subject}")
    except Exception as e:
        logger.error(f"Failed to send email to {to}: {e}")


def _send_welcome_email(email: str, api_key: str, plan: str):
    plan_label = plan.title()
    body = f"""Welcome to Off-Grid Scout {plan_label}! 🏕️

Your API key is:

  {api_key}

Keep this safe — it's your login to the extension.

HOW TO GET STARTED
──────────────────
1. Install the Chrome Extension:
   https://www.offgridscout.co.uk

2. Click the Off-Grid Scout icon in your browser toolbar

3. Paste your API key above when prompted, then hit Connect

4. Browse any Rightmove, Zoopla, or OnTheMarket land listing
   and click "Scan This Property"

Your plan: {plan_label}
Daily scans: {"25" if plan == "scout" else "100" if plan in ("pioneer","lifetime") else "3"}

Questions? Reply to this email.

— The Off-Grid Scout Team
https://www.offgridscout.co.uk
"""
    _send_email(email, "Your Off-Grid Scout API Key 🔑", body)


def _send_cancellation_email_by_customer(customer_id: str):
    """Look up user by Stripe customer ID and send cancellation notice."""
    users = _load_users()
    for uid, user in users.items():
        if user.get("stripe_customer_id") == customer_id:
            body = f"""Hi,

Your Off-Grid Scout subscription has been cancelled and your account
has been downgraded to the free tier (3 scans/day).

Your API key still works — you can reactivate anytime at:
https://www.offgridscout.co.uk/#pricing

— The Off-Grid Scout Team
"""
            _send_email(user["email"], "Off-Grid Scout — Subscription Cancelled", body)
            return


def _send_payment_failed_email(email: str):
    body = f"""Hi,

We couldn't process your Off-Grid Scout payment. Your subscription
may be paused if payment continues to fail.

Please update your payment method:
https://www.offgridscout.co.uk/billing

— The Off-Grid Scout Team
"""
    _send_email(email, "Off-Grid Scout — Payment Failed ⚠️", body)


def get_customer_portal_url(customer_id: str) -> str:
    """Create a Stripe Customer Portal session for managing subscriptions."""
    session = stripe.billing_portal.Session.create(
        customer=customer_id,
        return_url=f"{FRONTEND_URL}/",
    )
    return session.url
