import json
from autonomous_scout import AutonomousScout
from master_scout import evaluate_location
import logging
logger = logging.getLogger("off-grid-api.unified_scout")


class UnifiedScout:
    def __init__(self):
        self.discovery_engine = AutonomousScout()

    def run_full_scout(self, lat, lon, text_description=None, url=None, pdf_url=None):
        logger.info("\n==================================================")
        logger.info("\U0001F30D INITIATING GRAND UNIFICATION SCOUT")
        logger.info("==================================================")
        
        # PHASE 1: DISCOVERY
        logger.info("\n>>> PHASE 1: DISCOVERY ENGINE (Filtering) <<<")
        discovery_report = self.discovery_engine.evaluate_plot(lat, lon, text_description, url)
        
        verdict = discovery_report.get("FINAL_VERDICT", "")
        
        final_report = {
            "coordinates": {"lat": lat, "lon": lon},
            "phase_1_discovery": discovery_report,
            "phase_2_evaluation": None,
            "status": "COMPLETED"
        }

        # Check if we should proceed to Phase 2
        if "NO-GO" in verdict:
            logger.info("\n\u274C Plot failed critical discovery checks (e.g., Flood Zone, Developer Trap).")
            logger.info("\U0001F6D1 ABORTING Phase 2 (Evaluation) to save API calls and time.")
            final_report["status"] = "ABORTED_AT_PHASE_1"
            return final_report
        
        logger.info("\n\u2705 Plot passed Discovery Phase! Proceeding to Deep Evaluation...")
        
        # PHASE 2: EVALUATION (Sovereignty Score)
        logger.info("\n>>> PHASE 2: EVALUATION ENGINE (Sovereignty Score) <<<")
        if not pdf_url:
            # Default to National Planning Policy Framework if no local plan provided
            pdf_url = "https://assets.publishing.service.gov.uk/media/65a11af7e8f5ec000f1f8c46/NPPF_December_2023.pdf"
        
        try:
            logger.info("[1/4] Analyzing Terrain & Access...")
            logger.info("[2/4] Fetching Solar & Wind Data...")
            logger.info("[3/4] Checking Soil & Aquifers...")
            logger.info("[4/4] Analyzing Planning Policy...")
            
            evaluation_report = evaluate_location(lat, lon, pdf_url)
            final_report["phase_2_evaluation"] = evaluation_report
            
            # Boost Sovereignty Score if it's a Ghost Application (Para 84)
            if "PRIME PARAGRAPH 84 CANDIDATE" in verdict:
                logger.info("\n\U0001F47B Ghost Application detected! Applying +20% Sovereignty Score boost for Para 84 potential.")
                boosted_score = min(100.0, final_report["phase_2_evaluation"]["final_score"] * 1.2)
                final_report["phase_2_evaluation"]["final_score"] = round(boosted_score, 2)
                final_report["phase_2_evaluation"]["para_84_boost_applied"] = True
                
        except Exception as e:
            logger.warning(f"\n\u26A0\uFE0F Error during Phase 2: {e}")
            final_report["phase_2_evaluation"] = {"error": str(e)}
            final_report["status"] = "ERROR_IN_PHASE_2"

        return final_report

if __name__ == "__main__":
    scout = UnifiedScout()
    
    # Test Case: A viable plot in Cornwall
    test_lat = 50.2660
    test_lon = -5.0527
    test_desc = "Beautiful off-grid amenity land. No services, completely unconnected. Spring water available."
    
    report = scout.run_full_scout(lat=test_lat, lon=test_lon, text_description=test_desc)
    
    print("\n==================================================")
    print("\U0001F3C6 FINAL UNIFIED SCOUTING REPORT")
    print("==================================================")
    print(json.dumps(report, indent=2))
