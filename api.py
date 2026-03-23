from fastapi import FastAPI, HTTPException
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
    """Use Nominatim to geocode a location from listing title."""
    try:
        # Extract potential location words from title
        response = requests.get(
            "https://nominatim.openstreetmap.org/search",
            params={
                "q": title,
                "format": "json",
                "limit": 1,
                "countrycodes": "gb"  # Limit to UK
            },
            headers={"User-Agent": "OffGridScout/1.0"},
            timeout=10
        )
        results = response.json()
        if results:
            return float(results[0]["lat"]), float(results[0]["lon"])
    except Exception as e:
        logger.warning(f"Geocoding failed: {e}")
    return None, None


@app.get("/health")
def health_check():
    """Health check endpoint for Render."""
    return {"status": "healthy", "service": "off-grid-scout-api"}


# --- Issue #1, #2: Fixed /scan with dynamic coords + error handling ---
@app.post("/scan")
def scan_property(data: PropertyData):
    try:
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
        return {"status": "success", "dossier": dossier}

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
