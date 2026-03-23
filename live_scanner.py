import json
import time
from unified_scout import UnifiedScout
import logging
logger = logging.getLogger("off-grid-api.live_scanner")


class LiveScanner:
    def __init__(self):
        self.scout = UnifiedScout()

    def generate_dossier(self, property_name, price, lat, lon, description):
        logger.info(f"\n🔍 Scanning: {property_name}...")
        
        # Run the Grand Unification Engine
        report = self.scout.run_full_scout(lat, lon, text_description=description)
        
        if report['status'] == 'ABORTED_AT_PHASE_1':
            return f"\n❌ {property_name} rejected at Phase 1 (Failed critical checks: Developer Trap or Flood Zone)."
            
        p1 = report.get('phase_1_discovery', {})
        p2 = report.get('phase_2_evaluation', {})
        
        score = p2.get('final_score', 'N/A')
        breakdown = p2.get('breakdown', {})
        
        # Format sub-scores (convert 0.94 to 94)
        plan_score = int(breakdown.get('planning', 0) * 100)
        nrg_score = int(breakdown.get('energy', 0) * 100)
        res_score = int(breakdown.get('resources', 0) * 100)
        
        # Build "Why"
        terrain = p2.get('raw_data', {}).get('terrain', {})
        slope = terrain.get('slope_degrees', 0)
        aspect = terrain.get('compass_direction', 'Unknown')
        green_flags = p1.get('1_LISTING_ANALYSIS', {}).get('green_flags', [])
        why_text = f"Class Q permitted development is likely. {aspect}-facing {slope}° slope. Features: {', '.join(green_flags[:2])}."
        
        # Build "The Catch"
        access = p2.get('raw_data', {}).get('access', {}).get('has_access', False)
        flood = p1.get('2_ENVIRONMENTAL_STRESS', {}).get('flood_risk', 'Unknown')
        catch_text = ""
        if not access:
            catch_text += "No direct public road access. "
        if "Zone 3" in flood:
            catch_text += "High flood risk area. "
        if not catch_text:
            catch_text = "Within an AONB; solar panels must be ground-mounted and screened by hedging."
            
        # Build "AI Prediction"
        aquifer = p2.get('raw_data', {}).get('resources', {}).get('aquifer', {}).get('productivity', 'Unknown')
        ai_pred = f"High potential for a zero-carbon retrofit. Aquifer productivity is {str(aquifer).lower()}."

        # --- FINANCIALS & CAPEX CALCULATOR ---
        grid_dist = p1.get('2_ENVIRONMENTAL_STRESS', {}).get('grid_distance_m', 350)
        try:
            grid_dist = float(grid_dist)
        except:
            grid_dist = 350.0
            
        grid_cost = 10000 + max(0, (grid_dist - 50) * 100)
        
        solar_kwh = p2.get('raw_data', {}).get('energy', {}).get('solar_kwh_m2_day', 3.0)
        solar_cost = 12000 if float(solar_kwh) >= 3.0 else 16000
        
        if 'high' in str(aquifer).lower():
            water_cost = 6000
        elif 'low' in str(aquifer).lower():
            water_cost = 12000
        else:
            water_cost = 8500
            
        sewage_cost = 8000
        total_off_grid = solar_cost + water_cost + sewage_cost
        savings = grid_cost - total_off_grid
        
        fin_text = f"🔌 Grid Connection Est: £{int(grid_cost):,} ({int(grid_dist)}m away)\n"
        fin_text += f"☀️ Off-Grid Setup Est: £{int(total_off_grid):,} (Solar: £{int(solar_cost/1000)}k, Water: £{int(water_cost/1000)}k, Waste: £{int(sewage_cost/1000)}k)\n"
        if savings > 0:
            fin_text += f"💡 VERDICT: Going off-grid saves £{int(savings):,} in CapEx."
        else:
            fin_text += f"💡 VERDICT: Grid connection is cheaper by £{int(abs(savings)):,}."

        dossier = f"""
==================================================
📄 OFF GRID SCOUT DOSSIER
==================================================
Property: {property_name}
Current Price: {price}

🏆 FINAL OFF GRID SCORE: {score}/100

📊 SCORE BREAKDOWN
--------------------------------------------------
🏛️ Planning & Policy: {plan_score}/100
⚡ Energy Potential:  {nrg_score}/100
💧 Water & Soil:      {res_score}/100

✅ Why: {why_text}

⚠️ The Catch: {catch_text}

🤖 AI Prediction: "{ai_pred}"

💰 FINANCIALS & CAPEX ESTIMATE
--------------------------------------------------
{fin_text}
==================================================
"""
        return dossier
