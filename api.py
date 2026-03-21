from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from live_scanner import LiveScanner
import time

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

class PropertyData(BaseModel):
    url: str
    title: str

class EmailData(BaseModel):
    email: str
    dossier: str

scanner = LiveScanner()

@app.post("/scan")
def scan_property(data: PropertyData):
    lat, lon = 50.5600, -4.6500 
    desc = data.title + " | dilapidated stone barn, off-grid, spring water, agricultural"
    try:
        dossier = scanner.generate_dossier("Scraped Property", "TBD", lat, lon, desc)
        return {"status": "success", "dossier": dossier}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/email")
def send_email(data: EmailData):
    # Simulate sending an email for the prototype
    print(f"\n📧 [EMAIL SERVICE] Sending Dossier to {data.email}...")
    time.sleep(1.5) # Simulate network delay
    print(f"✅ [EMAIL SERVICE] Successfully delivered to {data.email}!")
    return {"status": "success", "message": f"Report successfully sent to {data.email}!"}
