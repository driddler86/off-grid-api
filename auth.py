"""User authentication and API key management for Off-Grid Scout."""
import json
import os
import secrets
import hashlib
from datetime import datetime, timezone
from typing import Optional
from pathlib import Path

# Storage file
USERS_FILE = os.path.join(os.path.dirname(__file__), "users.json")

# Tier limits (scans per day)
TIER_LIMITS = {
    "free": 3,
    "scout": 25,
    "pioneer": 100,
    "lifetime": 100,  # Same as pioneer
}

TIER_FEATURES = {
    "free": {
        "scans_per_day": 3,
        "pdf_export": False,
        "email_dossier": False,
        "priority_support": False,
    },
    "scout": {
        "scans_per_day": 25,
        "pdf_export": True,
        "email_dossier": True,
        "priority_support": False,
    },
    "pioneer": {
        "scans_per_day": 100,
        "pdf_export": True,
        "email_dossier": True,
        "priority_support": True,
    },
    "lifetime": {
        "scans_per_day": 100,
        "pdf_export": True,
        "email_dossier": True,
        "priority_support": True,
    },
}


def _load_users() -> dict:
    """Load users database from JSON file."""
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, "r") as f:
            return json.load(f)
    return {}


def _save_users(users: dict) -> None:
    """Save users database to JSON file."""
    with open(USERS_FILE, "w") as f:
        json.dump(users, f, indent=2, default=str)


def _hash_key(api_key: str) -> str:
    """Hash an API key for secure storage."""
    return hashlib.sha256(api_key.encode()).hexdigest()


def generate_api_key() -> str:
    """Generate a secure API key with ogs_ prefix."""
    return f"ogs_{secrets.token_urlsafe(32)}"


def create_user(
    email: str,
    stripe_customer_id: Optional[str] = None,
    tier: str = "free",
) -> dict:
    """Create a new user and return their API key.

    Returns dict with api_key (only time it's shown in plain text).
    """
    users = _load_users()

    # Check if email already exists
    for uid, user in users.items():
        if user["email"] == email:
            # User exists - update tier if upgrading
            if tier != "free":
                user["tier"] = tier
                user["stripe_customer_id"] = stripe_customer_id
                user["updated_at"] = datetime.now(timezone.utc).isoformat()
                _save_users(users)
            # Generate new key for existing user
            new_key = generate_api_key()
            user["api_key_hash"] = _hash_key(new_key)
            _save_users(users)
            return {"api_key": new_key, "user_id": uid, "tier": user["tier"], "existing": True}

    # Create new user
    api_key = generate_api_key()
    user_id = secrets.token_hex(8)

    users[user_id] = {
        "email": email,
        "api_key_hash": _hash_key(api_key),
        "tier": tier,
        "stripe_customer_id": stripe_customer_id,
        "stripe_subscription_id": None,
        "scans_today": 0,
        "scans_total": 0,
        "last_scan_date": None,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "active": True,
    }

    _save_users(users)
    return {"api_key": api_key, "user_id": user_id, "tier": tier, "existing": False}


def validate_api_key(api_key: str) -> Optional[dict]:
    """Validate an API key and return user data if valid.

    Returns None if invalid, user dict if valid.
    """
    if not api_key or not api_key.startswith("ogs_"):
        return None

    key_hash = _hash_key(api_key)
    users = _load_users()

    for uid, user in users.items():
        if user["api_key_hash"] == key_hash and user["active"]:
            return {"user_id": uid, **user}

    return None


def check_rate_limit(api_key: str) -> dict:
    """Check if user has remaining scans for today.

    Returns dict with allowed (bool), remaining (int), limit (int).
    """
    user = validate_api_key(api_key)
    if not user:
        return {"allowed": False, "reason": "Invalid API key", "remaining": 0, "limit": 0}

    tier = user.get("tier", "free")
    limit = TIER_LIMITS.get(tier, 3)
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    # Reset counter if new day
    if user.get("last_scan_date") != today:
        user["scans_today"] = 0

    remaining = max(0, limit - user["scans_today"])

    return {
        "allowed": remaining > 0,
        "remaining": remaining,
        "limit": limit,
        "tier": tier,
        "reason": None if remaining > 0 else f"Daily limit of {limit} scans reached for {tier} tier",
    }


def record_scan(api_key: str) -> bool:
    """Record a scan usage for the user. Returns True if successful."""
    key_hash = _hash_key(api_key)
    users = _load_users()
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    for uid, user in users.items():
        if user["api_key_hash"] == key_hash:
            # Reset if new day
            if user.get("last_scan_date") != today:
                user["scans_today"] = 0

            user["scans_today"] = user.get("scans_today", 0) + 1
            user["scans_total"] = user.get("scans_total", 0) + 1
            user["last_scan_date"] = today
            _save_users(users)
            return True

    return False


def update_tier(
    email: str = None,
    stripe_customer_id: str = None,
    tier: str = "free",
    subscription_id: str = None,
) -> bool:
    """Update a user's tier (called from Stripe webhook)."""
    users = _load_users()

    for uid, user in users.items():
        match = False
        if email and user["email"] == email:
            match = True
        if stripe_customer_id and user.get("stripe_customer_id") == stripe_customer_id:
            match = True

        if match:
            user["tier"] = tier
            if subscription_id:
                user["stripe_subscription_id"] = subscription_id
            user["updated_at"] = datetime.now(timezone.utc).isoformat()
            _save_users(users)
            return True

    return False


def deactivate_user(stripe_customer_id: str) -> bool:
    """Deactivate a user (subscription cancelled). Downgrade to free."""
    return update_tier(stripe_customer_id=stripe_customer_id, tier="free")


def get_user_stats(api_key: str) -> Optional[dict]:
    """Get user account stats for the extension dashboard."""
    user = validate_api_key(api_key)
    if not user:
        return None

    tier = user.get("tier", "free")
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    scans_today = user.get("scans_today", 0) if user.get("last_scan_date") == today else 0

    return {
        "email": user["email"],
        "tier": tier,
        "features": TIER_FEATURES.get(tier, TIER_FEATURES["free"]),
        "scans_today": scans_today,
        "scans_total": user.get("scans_total", 0),
        "daily_limit": TIER_LIMITS.get(tier, 3),
        "remaining_today": max(0, TIER_LIMITS.get(tier, 3) - scans_today),
        "member_since": user.get("created_at", ""),
    }
