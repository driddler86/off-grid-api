"""SQLite database layer for Off-Grid Scout."""
import sqlite3, os, secrets, hashlib
from datetime import datetime, timezone
from typing import Optional
from contextlib import contextmanager

DB_PATH = os.getenv("DATABASE_PATH", os.path.join(os.path.dirname(__file__), "offgridscout.db"))

@contextmanager
def get_db():
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

def init_db():
    with get_db() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY, email TEXT UNIQUE NOT NULL, api_key_hash TEXT NOT NULL,
                tier TEXT DEFAULT 'free', stripe_customer_id TEXT, stripe_subscription_id TEXT,
                scans_today INTEGER DEFAULT 0, scans_total INTEGER DEFAULT 0,
                last_scan_date TEXT, active INTEGER DEFAULT 1,
                created_at TEXT NOT NULL, updated_at TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS waitlist (
                id INTEGER PRIMARY KEY AUTOINCREMENT, email TEXT UNIQUE NOT NULL,
                signed_up_at TEXT NOT NULL, source TEXT DEFAULT 'landing_page', converted INTEGER DEFAULT 0);
            CREATE TABLE IF NOT EXISTS scan_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT NOT NULL,
                url TEXT, title TEXT, lat REAL, lon REAL, score INTEGER, tier TEXT,
                scanned_at TEXT NOT NULL, FOREIGN KEY (user_id) REFERENCES users(id));
            CREATE TABLE IF NOT EXISTS payments (
                id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT,
                stripe_session_id TEXT, stripe_customer_id TEXT, plan TEXT,
                amount_pence INTEGER, currency TEXT DEFAULT 'gbp',
                status TEXT DEFAULT 'completed', created_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id));
            CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
            CREATE INDEX IF NOT EXISTS idx_users_api_key ON users(api_key_hash);
            CREATE INDEX IF NOT EXISTS idx_users_stripe ON users(stripe_customer_id);
            CREATE INDEX IF NOT EXISTS idx_waitlist_email ON waitlist(email);
            CREATE INDEX IF NOT EXISTS idx_scans_user ON scan_history(user_id);
            CREATE INDEX IF NOT EXISTS idx_scans_date ON scan_history(scanned_at);
        """);

TIER_LIMITS = {"free": 3, "scout": 25, "pioneer": 100, "lifetime": 100}
TIER_FEATURES = {
    "free": {"scans_per_day": 3, "pdf_export": False, "email_dossier": False, "priority_support": False},
    "scout": {"scans_per_day": 25, "pdf_export": True, "email_dossier": True, "priority_support": False},
    "pioneer": {"scans_per_day": 100, "pdf_export": True, "email_dossier": True, "priority_support": True},
    "lifetime": {"scans_per_day": 100, "pdf_export": True, "email_dossier": True, "priority_support": True},
}

def _hash_key(k): return hashlib.sha256(k.encode()).hexdigest()
def _now(): return datetime.now(timezone.utc).isoformat()
def _today(): return datetime.now(timezone.utc).strftime("%Y-%m-%d")
def generate_api_key(): return f"ogs_{secrets.token_urlsafe(32)}"

# --- User Management ---

def create_user(email, stripe_customer_id=None, tier="free"):
    api_key = generate_api_key()
    key_hash = _hash_key(api_key)
    now = _now()
    with get_db() as conn:
        row = conn.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
        if row:
            new_tier = tier if tier != "free" else row["tier"]
            conn.execute(
                "UPDATE users SET api_key_hash=?, tier=?, stripe_customer_id=COALESCE(?,stripe_customer_id), updated_at=? WHERE email=?",
                (key_hash, new_tier, stripe_customer_id, now, email))
            return {"api_key": api_key, "user_id": row["id"], "tier": new_tier, "existing": True}
        user_id = secrets.token_hex(8)
        conn.execute(
            "INSERT INTO users (id,email,api_key_hash,tier,stripe_customer_id,scans_today,scans_total,active,created_at,updated_at) VALUES (?,?,?,?,?,0,0,1,?,?)",
            (user_id, email, key_hash, tier, stripe_customer_id, now, now))
        return {"api_key": api_key, "user_id": user_id, "tier": tier, "existing": False}

def validate_api_key(api_key):
    if not api_key or not api_key.startswith("ogs_"): return None
    with get_db() as conn:
        row = conn.execute("SELECT * FROM users WHERE api_key_hash=? AND active=1", (_hash_key(api_key),)).fetchone()
        return dict(row) if row else None

def check_rate_limit(api_key):
    user = validate_api_key(api_key)
    if not user:
        return {"allowed": False, "reason": "Invalid API key", "remaining": 0, "limit": 0}
    tier = user.get("tier", "free")
    limit = TIER_LIMITS.get(tier, 3)
    today = _today()
    scans = user["scans_today"] if user.get("last_scan_date") == today else 0
    rem = max(0, limit - scans)
    return {"allowed": rem > 0, "remaining": rem, "limit": limit, "tier": tier,
            "reason": None if rem > 0 else f"Daily limit of {limit} scans reached for {tier} tier"}

def record_scan(api_key, url=None, title=None, lat=None, lon=None, score=None):
    key_hash = _hash_key(api_key)
    today, now = _today(), _now()
    with get_db() as conn:
        row = conn.execute("SELECT * FROM users WHERE api_key_hash=?", (key_hash,)).fetchone()
        if not row: return False
        scans = row["scans_today"] if row["last_scan_date"] == today else 0
        conn.execute("UPDATE users SET scans_today=?, scans_total=scans_total+1, last_scan_date=?, updated_at=? WHERE id=?",
                     (scans + 1, today, now, row["id"]))
        conn.execute("INSERT INTO scan_history (user_id,url,title,lat,lon,score,tier,scanned_at) VALUES (?,?,?,?,?,?,?,?)",
                     (row["id"], url, title, lat, lon, score, row["tier"], now))
        return True

def get_user_stats(api_key):
    user = validate_api_key(api_key)
    if not user: return None
    tier = user.get("tier", "free")
    today = _today()
    scans = user["scans_today"] if user.get("last_scan_date") == today else 0
    return {"email": user["email"], "tier": tier, "features": TIER_FEATURES.get(tier, TIER_FEATURES["free"]),
            "scans_today": scans, "scans_total": user.get("scans_total", 0),
            "daily_limit": TIER_LIMITS.get(tier, 3),
            "remaining_today": max(0, TIER_LIMITS.get(tier, 3) - scans),
            "member_since": user.get("created_at", "")}

def update_tier(email=None, stripe_customer_id=None, tier="free", subscription_id=None):
    with get_db() as conn:
        row = None
        if email:
            row = conn.execute("SELECT id FROM users WHERE email=?", (email,)).fetchone()
        elif stripe_customer_id:
            row = conn.execute("SELECT id FROM users WHERE stripe_customer_id=?", (stripe_customer_id,)).fetchone()
        if not row: return False
        parts, params = ["tier=?", "updated_at=?"], [tier, _now()]
        if subscription_id:
            parts.append("stripe_subscription_id=?")
            params.append(subscription_id)
        params.append(row["id"])
        conn.execute(f"UPDATE users SET {', '.join(parts)} WHERE id=?", params)
        return True

def deactivate_user(stripe_customer_id):
    return update_tier(stripe_customer_id=stripe_customer_id, tier="free")

# --- Waitlist ---

def save_to_waitlist(email, source="landing_page"):
    with get_db() as conn:
        existing = conn.execute("SELECT id FROM waitlist WHERE email=?", (email,)).fetchone()
        if existing:
            return {"status": "already_registered", "message": "Email already on waitlist"}
        conn.execute("INSERT INTO waitlist (email,signed_up_at,source) VALUES (?,?,?)", (email, _now(), source))
        return {"status": "success", "message": "Welcome to the waitlist!"}

def get_waitlist_count():
    with get_db() as conn:
        row = conn.execute("SELECT COUNT(*) as cnt FROM waitlist").fetchone()
        return row["cnt"] if row else 0


# --- Payments ---

def record_payment(user_id=None, stripe_session_id=None, stripe_customer_id=None,
                   plan=None, amount_pence=None, currency="gbp"):
    with get_db() as conn:
        conn.execute(
            "INSERT INTO payments (user_id,stripe_session_id,stripe_customer_id,plan,amount_pence,currency,created_at) VALUES (?,?,?,?,?,?,?)",
            (user_id, stripe_session_id, stripe_customer_id, plan, amount_pence, currency, _now()))


# --- Analytics ---

def get_dashboard_stats():
    """Admin dashboard stats."""
    with get_db() as conn:
        users = conn.execute("SELECT COUNT(*) as c FROM users").fetchone()["c"]
        paid = conn.execute("SELECT COUNT(*) as c FROM users WHERE tier != 'free'").fetchone()["c"]
        waitlist = conn.execute("SELECT COUNT(*) as c FROM waitlist").fetchone()["c"]
        st = conn.execute("SELECT SUM(scans_today) as s FROM users WHERE last_scan_date=?", (_today(),)).fetchone()["s"] or 0
        total = conn.execute("SELECT SUM(scans_total) as s FROM users").fetchone()["s"] or 0
        tiers = {}
        for row in conn.execute("SELECT tier, COUNT(*) as c FROM users GROUP BY tier"):
            tiers[row["tier"]] = row["c"]
        revenue = conn.execute("SELECT SUM(amount_pence) as r FROM payments WHERE status='completed'").fetchone()["r"] or 0
        return {"total_users": users, "paid_users": paid, "waitlist": waitlist,
                "scans_today": st, "scans_total": total, "tiers": tiers,
                "total_revenue_pence": revenue}

def get_recent_scans(limit=20):
    """Get recent scan history for admin."""
    with get_db() as conn:
        rows = conn.execute(
            "SELECT s.*, u.email FROM scan_history s JOIN users u ON s.user_id=u.id ORDER BY s.scanned_at DESC LIMIT ?",
            (limit,)).fetchall()
        return [dict(r) for r in rows]


# --- Migration from JSON ---

def migrate_from_json():
    """One-time migration from JSON files to SQLite."""
    import json
    init_db()
    base = os.path.dirname(__file__)
    migrated = {"users": 0, "waitlist": 0}

    users_file = os.path.join(base, "users.json")
    if os.path.exists(users_file):
        with open(users_file) as f:
            users = json.load(f)
        with get_db() as conn:
            for uid, u in users.items():
                try:
                    conn.execute(
                        "INSERT OR IGNORE INTO users (id,email,api_key_hash,tier,stripe_customer_id,stripe_subscription_id,scans_today,scans_total,last_scan_date,active,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                        (uid, u["email"], u["api_key_hash"], u.get("tier","free"),
                         u.get("stripe_customer_id"), u.get("stripe_subscription_id"),
                         u.get("scans_today",0), u.get("scans_total",0),
                         u.get("last_scan_date"), 1, u.get("created_at",_now()), u.get("updated_at",_now())))
                    migrated["users"] += 1
                except Exception as e:
                    print(f"Skip user {uid}: {e}")
        os.rename(users_file, users_file + ".bak")
        print(f"Migrated {migrated['users']} users, backed up to users.json.bak")

    wl_file = os.path.join(base, "waitlist.json")
    if os.path.exists(wl_file):
        with open(wl_file) as f:
            wl = json.load(f)
        with get_db() as conn:
            for entry in wl:
                try:
                    conn.execute(
                        "INSERT OR IGNORE INTO waitlist (email,signed_up_at,source) VALUES (?,?,?)",
                        (entry["email"], entry.get("signed_up_at", _now()), entry.get("source", "landing_page")))
                    migrated["waitlist"] += 1
                except Exception as e:
                    print(f"Skip waitlist: {e}")
        os.rename(wl_file, wl_file + ".bak")
        print(f"Migrated {migrated['waitlist']} waitlist entries")

    return migrated


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "migrate":
        migrate_from_json()
    elif len(sys.argv) > 1 and sys.argv[1] == "stats":
        init_db()
        import json
        print(json.dumps(get_dashboard_stats(), indent=2))
    else:
        init_db()
        print(f"Database initialized at {DB_PATH}")
