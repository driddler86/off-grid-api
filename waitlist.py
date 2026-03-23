import json
import os
import logging
from datetime import datetime

logger = logging.getLogger("off-grid-api.waitlist")

WAITLIST_FILE = os.getenv("WAITLIST_FILE", "waitlist.json")

def load_waitlist():
    if os.path.exists(WAITLIST_FILE):
        with open(WAITLIST_FILE, "r") as f:
            return json.load(f)
    return []

def save_to_waitlist(email: str) -> dict:
    waitlist = load_waitlist()
    
    # Check for duplicates
    existing = [e for e in waitlist if e["email"] == email.lower().strip()]
    if existing:
        logger.info(f"Duplicate waitlist signup: {email}")
        return {"status": "already_registered", "message": "You're already on the list!"}
    
    entry = {
        "email": email.lower().strip(),
        "signed_up": datetime.utcnow().isoformat(),
        "source": "landing_page"
    }
    waitlist.append(entry)
    
    with open(WAITLIST_FILE, "w") as f:
        json.dump(waitlist, f, indent=2)
    
    logger.info(f"New waitlist signup: {email} (total: {len(waitlist)}")
    return {"status": "success", "message": "You're on the list!", "position": len(waitlist)}

def get_waitlist_count() -> int:
    return len(load_waitlist())
