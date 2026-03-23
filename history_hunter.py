import requests
import json
import logging
logger = logging.getLogger("off-grid-api.history_hunter")


class HistoryHunter:
    def __init__(self):
        self.api_url = "https://www.planit.org.uk/api/applics/json"
        self.headers = {'User-Agent': 'OffGridScout/1.0'}
        
        # Keywords that indicate a standard residential application
        self.target_keywords = ["dwelling", "house", "residential", "new build", "bungalow", "property"]

    def search_ghost_applications(self, lat, lon, radius_m=200):
        # Convert radius in meters to rough degrees (1 deg lat ~ 111km)
        delta = radius_m / 111000.0
        bbox = f"{lon-delta},{lat-delta},{lon+delta},{lat+delta}"
        
        params = {
            "bbox": bbox,
            "pg_sz": 50, # Max results per page
            "sort": "-start_date" # Newest first
        }
        
        try:
            response = requests.get(self.api_url, params=params, headers=self.headers, timeout=15)
            if response.status_code != 200:
                return {"error": f"API returned {response.status_code}", "is_para84_candidate": False}
                
            data = response.json()
            records = data.get('records', [])
            
            ghosts_found = []
            other_apps = []
            
            for app in records:
                desc = app.get('description', '').lower()
                status = app.get('decided', 'Unknown').lower()
                
                # Check if it's a residential application
                is_residential = any(kw in desc for kw in self.target_keywords)
                
                if is_residential:
                    # If it was refused or withdrawn, it's a Ghost!
                    if "refused" in status or "withdrawn" in status or "rejected" in status:
                        ghosts_found.append({
                            "uid": app.get('uid'),
                            "description": app.get('description'),
                            "status": app.get('decided'),
                            "date": app.get('start_date'),
                            "url": app.get('url')
                        })
                    else:
                        other_apps.append({
                            "description": app.get('description'),
                            "status": app.get('decided')
                        })
                        
            # Scoring Logic
            is_candidate = len(ghosts_found) > 0
            score_modifier = 100 if is_candidate else 0
            
            return {
                "is_para84_candidate": is_candidate,
                "ghost_applications_found": len(ghosts_found),
                "ghost_details": ghosts_found,
                "total_applications_scanned": len(records),
                "score_modifier": score_modifier,
                "message": "Prime Paragraph 84 Candidate! Standard development was previously refused here." if is_candidate else "No refused residential applications found in immediate vicinity."
            }
            
        except Exception as e:
            return {"error": str(e), "is_para84_candidate": False, "score_modifier": 0}

if __name__ == "__main__":
    hunter = HistoryHunter()
    
    # Test 1: A random location in Cornwall (might not have ghosts, but will test the API)
    print("--- Testing Location 1 (Cornwall) ---")
    print(json.dumps(hunter.search_ghost_applications(50.2660, -5.0527, radius_m=500), indent=2))
    
    # Test 2: A location in a dense area (more likely to hit applications)
    print("\n--- Testing Location 2 (Bristol Outskirts) ---")
    print(json.dumps(hunter.search_ghost_applications(51.4545, -2.5879, radius_m=500), indent=2))
