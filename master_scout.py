import argparse
import json
from policy_hunter import PolicyHunter
from energy_hunter import EnergyHunter
from resource_hunter import ResourceHunter
from os_land_rover import OSLandRover

def normalize_energy(energy_data, terrain_data):
    if not energy_data: return 0.0
    solar = energy_data.get('solar_kwh_m2_day', 0)
    wind = energy_data.get('wind_m_s', 0)
    
    solar_score = min(solar / 4.0, 1.0)
    wind_score = min(wind / 10.0, 1.0)
    
    # Terrain modifier for solar
    if terrain_data:
        aspect = terrain_data.get('aspect_degrees', 0)
        is_south = terrain_data.get('is_south_facing', False)
        if is_south:
            solar_score = min(solar_score * 1.1, 1.0) # 10% boost for south-facing
        elif aspect > 315 or aspect < 45: # North facing
            solar_score *= 0.7 # 30% penalty for north-facing
            
    return round((solar_score + wind_score) / 2.0, 4)

def normalize_resource(resource_data):
    if not resource_data: return 0.0
    aquifer_prod = resource_data.get('aquifer', {}).get('productivity', '').lower()
    if 'high' in aquifer_prod: aq_score = 1.0
    elif 'moderate' in aquifer_prod: aq_score = 0.7
    elif 'low' in aquifer_prod: aq_score = 0.4
    else: aq_score = 0.2
    soil_score = 0.5 
    return round((aq_score + soil_score) / 2.0, 4)

def evaluate_location(lat, lon, pdf_url):
    # 1. Terrain & Access
    rover = OSLandRover()
    land_data = rover.scout_location(lat, lon)
    terrain = land_data['terrain']
    access = land_data['access']

    # 2. Energy
    e_hunter = EnergyHunter()
    e_data = e_hunter.get_energy_score_data(lat, lon)
    e_score = normalize_energy(e_data, terrain)

    # 3. Resource
    r_hunter = ResourceHunter()
    r_data = r_hunter.get_resource_score_data(lat, lon)
    r_score = normalize_resource(r_data)

    # 4. Planning
    p_hunter = PolicyHunter()
    pdf_path = "temp_plan.pdf"
    p_hunter.download_pdf(pdf_url, pdf_path)
    doc_text = p_hunter.extract_text(pdf_path)
    p_score, findings = p_hunter.score_document(doc_text)

    # Base Score
    s_score = (p_score * 0.40) + (e_score * 0.30) + (r_score * 0.30)
    
    # Access Modifier (Critical)
    if not access.get('has_access', False):
        s_score *= 0.5 # 50% penalty for no road access
        
    return {
        "final_score": round(s_score * 100, 2),
        "breakdown": {
            "planning": p_score,
            "energy": e_score,
            "resources": r_score
        },
        "raw_data": {
            "terrain": terrain,
            "access": access,
            "energy": e_data,
            "resources": r_data,
            "planning_findings": findings
        }
    }

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--lat', type=float, required=True)
    parser.add_argument('--lon', type=float, required=True)
    parser.add_argument('--pdf', type=str, default="https://assets.publishing.service.gov.uk/media/65a11af7e8f5ec000f1f8c46/NPPF_December_2023.pdf")
    args = parser.parse_args()
    
    result = evaluate_location(args.lat, args.lon, args.pdf)
    print(json.dumps(result, indent=2))

if __name__ == '__main__':
    main()
