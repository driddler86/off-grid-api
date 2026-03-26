import os
import hashlib
import secrets
import logging
import requests
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger("off-grid-api.db")

# ── Cloudflare D1 config ──────────────────────────────────────────────────────
CF_ACCOUNT_ID     = os.getenv("CF_ACCOUNT_ID", "")
CF_D1_DATABASE_ID = os.getenv("CF_D1_DATABASE_ID", "672bd0a3-2912-41c8-bc81-6a0b9d63bdfa")
CF_API_TOKEN      = os.getenv("CF_API_TOKEN", "")

D1_URL = f"https://api.cloudflare.com/client/v4/accounts/{CF_ACCOUNT_ID}/d1/database/{CF_D1_DATABASE_ID}/query"

# ── Tier config ───────────────────────────────────────────────────────────────
TIER_LIMITS = {
    "free":     3,
    "scout":    25,
    "pioneer":  100,
    "lifetime": 100,
}

TIER_FEATURES = {
    "free":     {"scans_per_day": 3,   "pdf_export": False, "email_dossier": False, "priority_support": False},
    "scout":    {"scans_per_day": 25,  "pdf_export": True,  "email_dossier": True,  "priority_support": False},
    "pioneer":  {"scans_per_day": 100, "pdf_export": True,  "email_dossier": True,  "priority_support": True},
    "lifetime": {"scans_per_day": 100, "pdf_export": True,  "email_dossier": True,  "priority_support": True},
}

# ── D1 query helper ───────────────────────────────────────────────────────────
def _query(sql: str, params: list = None) -> list:
    """Execute a D1 SQL query and return rows."""
    if not CF_ACCOUNT_ID or not CF_API_TOKEN:
        logger.error("Cloudflare credentials not set — CF_ACCOUNT_ID and CF_API_TOKEN required")
        return []
    try:
        payload = {"sql": sql}
        if params:
            payload["params"] = params
        resp = requests.post(
            D1_URL,
            headers={
                "Authorization": f"Bearer {CF_API_TOKEN}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        if data.get("success") and data.get("result"):
            return data["result"][0].get("results", [])
        logger.warning(f"D1 query returned no result: {data}")
        return []
    except Exception as e:
        logger.error(f"D1 query failed: {e} — SQL: {sql[:80]}")
        return []


def _execute(sql: str, params: list = None) -> bool:
    """Execute a D1 write query. Returns True on success."""
    if not CF_ACCOUNT_ID or not CF_API_TOKEN:
        logger.error("Cloudflare credentials not set")
        return False
    try:
        payload = {"sql": sql}
        if params:
            payload["params"] = params
        resp = requests.post(
            D1_URL,
            headers={
                "Authorization": f"Bearer {CF_API_TOKEN}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        return data.get("success", False)
    except Exception as e:
        logger.error(f"D1 execute failed: {e} — SQL: {sql[:80]}")
        return False


# ── Utilities ─────────────────────────────────────────────────────────────────
def _hash_key(api_key: str) -> str:
    return hashlib.sha256(api_key.encode()).hexdigest()

def generate_api_key() -> str:
    return f"ogs_{secrets.token_urlsafe(32)}"

def _now() -> str:
    return datetime.now(timezone.utc).isoformat()

def _today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


# ── User management ───────────────────────────────────────────────────────────
def create_user(email: str, stripe_customer_id: str = None, tier: str = "free") -> dict:
    """Create or update a user. Returns dict with api_key (plaintext, shown once)."""
    # Check if user already exists
    rows = _query("SELECT user_id, tier FROM users WHERE email = ?", [email.lower().strip()])
    api_key = generate_api_key()
    key_hash = _hash_key(api_key)
    now = _now()

    if rows:
        user = rows[0]
        # Update existing user — new key, possibly new tier
        new_tier = tier if tier != "free" else user.get("tier", "free")
        _execute(
            "UPDATE users SET api_key_hash=?, tier=?, stripe_customer_id=?, updated_at=? WHERE email=?",
            [key_hash, new_tier, stripe_customer_id, now, email.lower().strip()]
        )
        return {"api_key": api_key, "user_id": user["user_id"], "tier": new_tier, "existing": True}

    # Create new user
    user_id = secrets.token_hex(8)
    _execute(
        """INSERT INTO users
           (user_id, email, api_key_hash, tier, stripe_customer_id, scans_today, scans_total,
            last_scan_date, active, created_at, updated_at)
           VALUES (?, ?, ?, ?, ?, 0, 0, NULL, 1, ?, ?)""",
        [user_id, email.lower().strip(), key_hash, tier, stripe_customer_id, now, now]
    )
    return {"api_key": api_key, "user_id": user_id, "tier": tier, "existing": False}


def validate_api_key(api_key: str) -> Optional[dict]:
    """Validate an API key. Returns user dict or None."""
    if not api_key or not api_key.startswith("ogs_"):
        return None
    key_hash = _hash_key(api_key)
    rows = _query("SELECT * FROM users WHERE api_key_hash = ? AND active = 1", [key_hash])
    return rows[0] if rows else None


def check_rate_limit(api_key: str) -> dict:
    """Check if user has scans remaining today."""
    user = validate_api_key(api_key)
    if not user:
        return {"allowed": False, "reason": "Invalid API key", "remaining": 0, "limit": 0}

    tier  = user.get("tier", "free")
    limit = TIER_LIMITS.get(tier, 3)
    today = _today()

    scans_today = user.get("scans_today", 0) if user.get("last_scan_date") == today else 0
    remaining   = max(0, limit - scans_today)

    return {
        "allowed":   remaining > 0,
        "remaining": remaining,
        "limit":     limit,
        "tier":      tier,
        "reason":    None if remaining > 0 else f"Daily limit of {limit} scans reached",
    }


def record_scan(api_key: str) -> bool:
    """Increment scan count for today."""
    key_hash = _hash_key(api_key)
    today    = _now()[:10]  # YYYY-MM-DD

    # Reset if new day, then increment
    _execute(
        """UPDATE users SET
             scans_today  = CASE WHEN last_scan_date = ? THEN scans_today + 1 ELSE 1 END,
             scans_total  = scans_total + 1,
             last_scan_date = ?,
             updated_at   = ?
           WHERE api_key_hash = ?""",
        [today, today, _now(), key_hash]
    )
    return True


def get_user_stats(api_key: str) -> Optional[dict]:
    """Get account stats for extension popup."""
    user = validate_api_key(api_key)
    if not user:
        return None

    tier        = user.get("tier", "free")
    today       = _today()
    scans_today = user.get("scans_today", 0) if user.get("last_scan_date") == today else 0

    return {
        "email":          user.get("email", ""),
        "tier":           tier,
        "features":       TIER_FEATURES.get(tier, TIER_FEATURES["free"]),
        "scans_today":    scans_today,
        "scans_total":    user.get("scans_total", 0),
        "daily_limit":    TIER_LIMITS.get(tier, 3),
        "remaining_today": max(0, TIER_LIMITS.get(tier, 3) - scans_today),
        "member_since":   user.get("created_at", ""),
    }


def update_tier(email: str = None, stripe_customer_id: str = None,
                tier: str = "free", subscription_id: str = None) -> bool:
    """Update user tier (called from Stripe webhook)."""
    now = _now()
    if email:
        return _execute(
            "UPDATE users SET tier=?, stripe_subscription_id=?, updated_at=? WHERE email=?",
            [tier, subscription_id, now, email.lower().strip()]
        )
    if stripe_customer_id:
        return _execute(
            "UPDATE users SET tier=?, stripe_subscription_id=?, updated_at=? WHERE stripe_customer_id=?",
            [tier, subscription_id, now, stripe_customer_id]
        )
    return False


def deactivate_user(stripe_customer_id: str) -> bool:
    """Downgrade cancelled subscription to free tier."""
    return update_tier(stripe_customer_id=stripe_customer_id, tier="free")


# ── Waitlist ──────────────────────────────────────────────────────────────────
def save_to_waitlist(email: str) -> dict:
    rows = _query("SELECT email FROM waitlist WHERE email = ?", [email.lower().strip()])
    if rows:
        return {"status": "already_registered", "message": "You're already on the list!"}
    _execute(
        "INSERT INTO waitlist (email, signed_up, source) VALUES (?, ?, ?)",
        [email.lower().strip(), _now(), "landing_page"]
    )
    count = _query("SELECT COUNT(*) as n FROM waitlist")
    return {"status": "success", "message": "You're on the list!", "position": count[0]["n"] if count else 0}


def get_waitlist_count() -> int:
    rows = _query("SELECT COUNT(*) as n FROM waitlist")
    return rows[0]["n"] if rows else 0


def init_db():
    """No-op — D1 tables already created via MCP."""
    logger.info("Using Cloudflare D1 for persistent storage")
