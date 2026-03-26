from fastapi import FastAPI, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator
from typing import Optional
from live_scanner import LiveScanner
import requests
import logging
import time
from collections import defaultdict
from datetime import datetime, timedelta
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

# --- Issue #7: Simple in-memory rate limiting ---
class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, max_requests: int = 10, window_seconds: int = 60):
        super().__init__(app)
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests = defaultdict(list)

    async def dispatch(self, request: Request, call_next):
        # Skip rate limiting for health checks
        if request.url.path == "/health":
            return await call_next(request)

        client_ip = request.client.host
        now = datetime.now()
        cutoff = now - timedelta(seconds=self.window_seconds)

        # Clean old entries
        self.requests[client_ip] = [
            t for t in self.requests[client_ip] if t > cutoff
        ]

        if len(self.requests[client_ip]) >= self.max_requests:
            return JSONResponse(
                status_code=429,
                content={"detail": f"Rate limit exceeded. Max {self.max_requests} requests per {self.window_seconds} seconds."}
            )

        self.requests[client_ip].append(now)
        return await call_next(request)


# --- Issue #13: Proper logging instead of print() ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("off-grid-api")

app = FastAPI(
    title="Off-Grid Scout API",
    description="API for evaluating UK land plots for off-grid living potential",
    version="1.0.0"
)

# --- Issue #6: Tightened CORS (configurable for production) ---
import os
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"]
)
# --- Issue #7: Rate limiting (10 requests per minute per IP) ---
MAX_REQUESTS = int(os.getenv("RATE_LIMIT_MAX", "10"))
RATE_WINDOW = int(os.getenv("RATE_LIMIT_WINDOW", "60"))
app.add_middleware(RateLimitMiddleware, max_requests=MAX_REQUESTS, window_seconds=RATE_WINDOW)

# --- Initialize SQLite database ---
import os


# --- Issue #1 & #5: Updated PropertyData with lat/lon + validation ---
class PropertyData(BaseModel):
    url: str = Field(..., max_length=2000, description="Listing URL")
    title: str = Field(..., max_length=500, description="Listing title")
    lat: Optional[float] = Field(None, ge=-90, le=90, description="Latitude")
    lon: Optional[float] = Field(None, ge=-180, le=180, description="Longitude")
    description: Optional[str] = Field(None, max_length=5000, description="Listing description")

class EmailData(BaseModel):
    email: str = Field(..., max_length=320, description="Recipient email")
    dossier: str = Field(..., description="Dossier content to send")

    @field_validator("email")
    @classmethod
    def validate_email(cls, v):
        if "@" not in v or "." not in v:
            raise ValueError("Invalid email address")
        return v

scanner = LiveScanner()

# --- Issue #1: Geocoding fallback when lat/lon not provided ---
def geocode_from_title(title: str) -> tuple:
    """Use Nominatim to geocode a location from listing title or description."""
    import re

    def _query(q):
        try:
            r = requests.get(
                "https://nominatim.openstreetmap.org/search",
                params={"q": q, "format": "json", "limit": 1, "countrycodes": "gb"},
                headers={"User-Agent": "OffGridScout/1.0"},
                timeout=10,
            )
            results = r.json()
            if results:
                lat, lon = float(results[0]["lat"]), float(results[0]["lon"])
                # Validate UK bounding box
                if 49.0 <= lat <= 61.0 and -8.0 <= lon <= 2.0:
                    return lat, lon
        except Exception as e:
            logger.warning(f"Geocoding query failed for '{q}': {e}")
        return None, None

    # 1. Try extracting a UK postcode first — most reliable
    postcode_match = re.search(
        r'\b([A-Z]{1,2}\d{1,2}[A-Z]?\s*\d[A-Z]{2})\b', title, re.IGNORECASE
    )
    if postcode_match:
        lat, lon = _query(postcode_match.group(1))
        if lat: return lat, lon

    # 2. Try "Postcode: XX1 1XX" pattern (added by content script for UKLAF)
    postcode_tag = re.search(r'Postcode:\s*([A-Z]{1,2}\d{1,2}[A-Z]?\s*\d[A-Z]{2})', title, re.IGNORECASE)
    if postcode_tag:
        lat, lon = _query(postcode_tag.group(1))
        if lat: return lat, lon

    # 3. Extract town/county from title — strip acreage and land type words
    clean = re.sub(
        r'(\d[\d.,]*\s*acres?|for sale|guide price|£[\d,]+|POA|freehold|leasehold'
        r'|development land|agricultural land|pasture|woodland|equestrian'
        r'|smallholding|farm|estate|lot \d+|STP|BNG)',
        '', title, flags=re.IGNORECASE
    )
    # Remove short tokens and split on commas to get location fragments
    parts = [p.strip() for p in clean.split(',') if len(p.strip()) > 3]
    # Try each part from the end (most specific location usually at end)
    for part in reversed(parts):
        lat, lon = _query(part + ", UK")
        if lat: return lat, lon

    # 4. Last resort — try the full title
    lat, lon = _query(title)
    if lat: return lat, lon

    return None, None


@app.get("/health")
def health_check():
    """Health check endpoint for Render."""
    return {"status": "healthy", "service": "off-grid-scout-api"}


# --- Issue #1, #2: Fixed /scan with dynamic coords + error handling ---
@app.post("/scan")
def scan_property(data: PropertyData, x_api_key: Optional[str] = Header(None, alias="X-API-Key")):
    try:
        # Check API key if provided (free scans allowed without key for demo)
        user_tier = "free"
        if x_api_key:
            limit_info = check_rate_limit(x_api_key)
            if not limit_info["allowed"]:
                raise HTTPException(
                    status_code=429,
                    detail=limit_info["reason"]
                )
            user_tier = limit_info.get("tier", "free")

        # Issue #1: Use provided coordinates or geocode from title
        lat, lon = data.lat, data.lon

        if lat is None or lon is None:
            logger.info(f"No coordinates provided, geocoding from title: {data.title}")
            lat, lon = geocode_from_title(data.title)

        if lat is None or lon is None:
            raise HTTPException(
                status_code=400,
                detail="Could not determine location. Please provide lat/lon coordinates or a more specific title with a UK location name."
            )

        # Validate UK coordinates (rough bounding box)
        if not (49.0 <= lat <= 61.0 and -8.0 <= lon <= 2.0):
            raise HTTPException(
                status_code=400,
                detail="Coordinates appear to be outside the UK. This tool currently only supports UK locations."
            )

        desc = data.description or data.title
        logger.info(f"Scanning property at ({lat}, {lon}): {data.title}")

        dossier = scanner.generate_dossier(data.title, "TBD", lat, lon, desc)

        # Record scan usage if API key provided
        if x_api_key:
            record_scan(x_api_key)
            features = TIER_FEATURES.get(user_tier, TIER_FEATURES["free"])
        else:
            features = TIER_FEATURES["free"]

        import re
        score_match = re.search(r'(?:FINAL OFF GRID SCORE|Sovereignty Score|Overall Score)[:\s]+(\d{1,3})', dossier, re.IGNORECASE)
        score = int(score_match.group(1)) if score_match else None

        return {
            "status": "success",
            "dossier": dossier,
            "score": score,
            "tier": user_tier,
            "features": features,
        }

    except HTTPException:
        raise  # Re-raise HTTP exceptions as-is
    except Exception as e:
        logger.error(f"Scan failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Internal error during property scan: {str(e)}"
        )


# --- Issue #3: Real email placeholder with SMTP support ---
@app.post("/email")
def send_email(data: EmailData):
    try:
        import smtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart

        smtp_host = os.getenv("SMTP_HOST")
        smtp_port = int(os.getenv("SMTP_PORT", "587"))
        smtp_user = os.getenv("SMTP_USER")
        smtp_pass = os.getenv("SMTP_PASS")
        from_email = os.getenv("FROM_EMAIL", smtp_user)

        if not all([smtp_host, smtp_user, smtp_pass]):
            # Fallback to simulation if SMTP not configured
            logger.warning("SMTP not configured - simulating email send")
            logger.info(f"[EMAIL SERVICE] Would send dossier to {data.email}")
            return {
                "status": "success",
                "message": f"Report queued for {data.email} (SMTP not configured - demo mode)",
                "demo_mode": True
            }

        # Real SMTP send
        msg = MIMEMultipart()
        msg["From"] = from_email
        msg["To"] = data.email
        msg["Subject"] = "Your Off-Grid Scout Report"
        msg.attach(MIMEText(data.dossier, "plain"))

        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.sendmail(from_email, data.email, msg.as_string())

        logger.info(f"Email sent successfully to {data.email}")
        return {"status": "success", "message": f"Report sent to {data.email}!"}

    except Exception as e:
        logger.error(f"Email failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to send email: {str(e)}"
        )

# --- Stripe payment endpoints ---
from stripe_integration import create_checkout_session, handle_webhook
from fastapi import Request

class CheckoutData(BaseModel):
    plan: str = Field(..., pattern="^(scout|pioneer|lifetime)$")
    email: str = Field(default=None, max_length=320)

@app.post("/checkout")
def create_checkout(data: CheckoutData):
    try:
        result = create_checkout_session(data.plan, data.email)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Checkout error: {e}")
        raise HTTPException(status_code=500, detail="Payment setup failed")

@app.post("/webhook/stripe")
async def stripe_webhook(request: Request):
    payload = await request.body()
    sig = request.headers.get("stripe-signature", "")
    try:
        result = handle_webhook(payload, sig)
        # Auto-create/upgrade user account on successful payment
        if result.get("event_type") == "checkout.session.completed":
            email = result.get("customer_email")
            plan = result.get("plan", "scout")
            stripe_id = result.get("customer_id")
            if email:
                user_result = create_user(
                    email=email,
                    stripe_customer_id=stripe_id,
                    tier=plan,
                )
                logger.info(f"User account created/upgraded: {email} -> {plan}")
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# --- Auth endpoints ---
class RegisterData(BaseModel):
    email: str = Field(..., max_length=320)

    @field_validator("email")
    @classmethod
    def validate_email(cls, v):
        if "@" not in v or "." not in v:
            raise ValueError("Invalid email address")
        return v

@app.post("/auth/register")
def register_user(data: RegisterData):
    """Register for a free account and get an API key."""
    try:
        result = create_user(email=data.email, tier="free")
        return {
            "status": "success",
            "api_key": result["api_key"],
            "tier": result["tier"],
            "message": "Save your API key - it won't be shown again!"
                       + (" (Existing account - new key issued)" if result["existing"] else ""),
        }
    except Exception as e:
        logger.error(f"Registration failed: {e}")
        raise HTTPException(status_code=500, detail="Registration failed")


@app.get("/auth/verify")
def verify_key(x_api_key: str = Header(..., alias="X-API-Key")):
    """Verify an API key and return account info."""
    stats = get_user_stats(x_api_key)
    if not stats:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return {"status": "success", **stats}


@app.get("/auth/session")
def get_session(session_id: str):
    """Resolve a Stripe checkout session_id to the user's API key.
    Called by success.html after payment to display the key to the user.
    """
    import stripe
    from stripe_integration import PRICE_IDS
    stripe.api_key = os.getenv("STRIPE_SECRET_KEY", "")
    if not stripe.api_key:
        raise HTTPException(status_code=503, detail="Payment system not configured")
    try:
        session = stripe.checkout.Session.retrieve(session_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid session: {e}")

    customer_email = session.get("customer_email") or ""
    plan = session.get("metadata", {}).get("plan", "scout")

    if not customer_email:
        raise HTTPException(status_code=400, detail="No email associated with this session")

    # Create or update the user at the paid tier — issues a fresh key
    result = create_user(email=customer_email, tier=plan)
    return {"api_key": result["api_key"], "tier": plan, "email": customer_email}


@app.get("/auth/usage")
def get_usage(x_api_key: str = Header(..., alias="X-API-Key")):
    """Get current usage stats for rate limit display."""
    limit_check = check_rate_limit(x_api_key)
    if not limit_check["allowed"] and limit_check["remaining"] == 0 and limit_check["limit"] == 0:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return limit_check

# --- Waitlist endpoint ---
# --- Database (replaces auth.py and waitlist.py) ---
from db import (
    init_db, save_to_waitlist, get_waitlist_count,
    create_user, validate_api_key, check_rate_limit,
    record_scan, get_user_stats, TIER_FEATURES
)
from fastapi import Header


class WaitlistData(BaseModel):
    email: str = Field(..., max_length=320)

@app.post("/waitlist")
def join_waitlist(data: WaitlistData):
    try:
        result = save_to_waitlist(data.email)
        result["total_signups"] = get_waitlist_count()
        return result
    except Exception as e:
        logger.error(f"Waitlist error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# --- Serve landing page ---
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

@app.get("/")
def serve_landing():
    return FileResponse("static/index.html")


# --- Admin Dashboard ---
ADMIN_KEY = os.getenv("ADMIN_KEY", "change-me-in-production")

@app.get("/admin")
def serve_admin():
    return FileResponse("static/admin.html")

@app.get("/admin/dashboard")
def admin_dashboard(x_admin_key: str = Header(None, alias="X-Admin-Key")):
    if not x_admin_key or x_admin_key != ADMIN_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized")
    from db import _query
    users      = _query("SELECT COUNT(*) as n FROM users WHERE active=1")
    waitlist   = _query("SELECT COUNT(*) as n FROM waitlist")
    scans      = _query("SELECT SUM(scans_total) as n FROM users")
    paid       = _query("SELECT COUNT(*) as n FROM users WHERE tier != 'free' AND active=1")
    return {
        "stats": {
            "total_users":    users[0]["n"]    if users    else 0,
            "waitlist_count": waitlist[0]["n"] if waitlist else 0,
            "total_scans":    scans[0]["n"]    if scans    else 0,
            "paid_users":     paid[0]["n"]     if paid     else 0,
        }
    }

app.mount("/static", StaticFiles(directory="static"), name="static")

