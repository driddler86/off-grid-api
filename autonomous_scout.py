import json
from listing_hunter import ListingHunter
from stress_hunter import StressHunter
from history_hunter import HistoryHunter

class AutonomousScout:
    def __init__(self):
        self.listing_hunter = ListingHunter()
        self.stress_hunter = StressHunter()
        self.history_hunter = HistoryHunter()

    def evaluate_plot(self, lat, lon, text_description=None, url=None):
        print(f"\n[1/3] 🕵️  Running Broad Sweep (Listing Analysis)...")
        if text_description:
            listing_data = self.listing_hunter.analyze_text(text_description)
        elif url:
            listing_data = self.listing_hunter.scrape_listing(url)
        else:
            listing_data = {"score": 0, "is_viable": True, "error": "No text or URL provided"}

        print(f"[2/3] 🌊 Running Environmental Stress Test (Flood & Grid)...")
        stress_data = self.stress_hunter.run_stress_test(lat, lon)

        print(f"[3/3] 👻 Hunting for 'Ghost' Planning Applications...")
        history_data = self.history_hunter.search_ghost_applications(lat, lon, radius_m=200)

        # Aggregate Scores
        total_score = listing_data.get('score', 0) + stress_data.get('total_stress_score', 0) + history_data.get('score_modifier', 0)
        
        # Determine Verdict
        is_viable = listing_data.get('is_viable', False) and stress_data.get('is_viable', False)
        
        if not is_viable:
            verdict = "❌ NO-GO (Failed critical viability checks)"
        elif history_data.get('is_para84_candidate', False):
            verdict = "🌟 PRIME PARAGRAPH 84 CANDIDATE (Ghost App Found!)"
        elif total_score > 50:
            verdict = "✅ STRONG OFF-GRID POTENTIAL"
        else:
            verdict = "⚠️ MARGINAL (Requires further manual review)"

        report = {
            "FINAL_VERDICT": verdict,
            "TOTAL_SCORE": total_score,
            "1_LISTING_ANALYSIS": {
                "score": listing_data.get('score', 0),
                "green_flags": listing_data.get('positive_matches', []),
                "red_flags": listing_data.get('negative_matches', [])
            },
            "2_ENVIRONMENTAL_STRESS": {
                "score": stress_data.get('total_stress_score', 0),
                "flood_risk": stress_data.get('flood_risk', {}).get('risk_level', 'Unknown'),
                "grid_distance": stress_data.get('grid_proximity', {}).get('status', 'Unknown')
            },
            "3_PLANNING_HISTORY": {
                "score": history_data.get('score_modifier', 0),
                "ghosts_found": history_data.get('ghost_applications_found', 0),
                "message": history_data.get('message', '')
            }
        }
        return report

if __name__ == "__main__":
    scout = AutonomousScout()
    
    # Simulated Test: A perfect off-grid plot in a remote area
    # We will use coordinates in the Scottish Highlands (remote, no flood, no grid)
    test_lat = 57.1000
    test_lon = -4.5000
    test_desc = "Rare opportunity to acquire 5 acres of amenity land. Features a dilapidated barn and spring water. Completely unconnected and off-grid. No services available."
    
    print("==================================================")
    print("🚀 INITIATING AUTONOMOUS OFF-GRID SCOUT")
    print("==================================================")
    
    report = scout.evaluate_plot(lat=test_lat, lon=test_lon, text_description=test_desc)
    
    print("\n==================================================")
    print("📊 FINAL SCOUTING REPORT")
    print("==================================================")
    print(json.dumps(report, indent=2))
