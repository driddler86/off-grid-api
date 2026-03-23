import requests
from cache import cached
import json
import math
from pyproj import Transformer
import logging
logger = logging.getLogger("off-grid-api.stress_hunter")


class StressHunter:
    def __init__(self):
        self.flood_api_url = "https://environment.data.gov.uk/KB6uNVj5ZcJr7jUP/ArcGIS/rest/services/Flood_Map_for_Planning/FeatureServer/1/query"
        self.overpass_url = "http://overpass-api.de/api/interpreter"
        self.transformer = Transformer.from_crs("epsg:4326", "epsg:27700", always_xy=True)

    def check_flood_risk(self, lat, lon):
        try:
            easting, northing = self.transformer.transform(lon, lat)
            params = {
                'geometry': f"{easting},{northing}",
                'geometryType': 'esriGeometryPoint',
                'spatialRel': 'esriSpatialRelIntersects',
                'inSR': '27700',
                'outSR': '4326',
                'f': 'json',
                'returnGeometry': 'false'
            }
            response = requests.get(self.flood_api_url, params=params, timeout=10)
            data = response.json()
            is_flood_zone_3 = len(data.get('features', [])) > 0
            return {
                "in_flood_zone_3": is_flood_zone_3,
                "risk_level": "HIGH (Zone 3)" if is_flood_zone_3 else "LOW/MODERATE (Zone 1/2)",
                "score_modifier": -100 if is_flood_zone_3 else 10
            }
        except Exception as e:
            return {"error": str(e), "in_flood_zone_3": False, "score_modifier": 0}

    def check_grid_distance(self, lat, lon):
        try:
            query = f"""
            [out:json];
            (
              node["power"~"line|transformer|substation|pole|tower"](around:2000, {lat}, {lon});
              way["power"~"line|transformer|substation|pole|tower"](around:2000, {lat}, {lon});
            );
            out center;
            """
            response = requests.post(self.overpass_url, data={'data': query}, timeout=15)
            data = response.json()
            elements = data.get('elements', [])
            if not elements:
                return {"nearest_grid_m": 2000, "status": "Completely Off-Grid (>2km)", "score_modifier": 50}
                
            min_dist = float('inf')
            for el in elements:
                el_lat = el.get('lat') or el.get('center', {}).get('lat')
                el_lon = el.get('lon') or el.get('center', {}).get('lon')
                if el_lat and el_lon:
                    R = 6371e3
                    phi1, phi2 = math.radians(lat), math.radians(el_lat)
                    delta_phi = math.radians(el_lat - lat)
                    delta_lambda = math.radians(el_lon - lon)
                    a = math.sin(delta_phi/2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda/2)**2
                    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
                    dist = R * c
                    if dist < min_dist: min_dist = dist
                        
            min_dist = round(min_dist, 2)
            if min_dist > 500:
                status, mod = "Prime Off-Grid (>500m)", 30
            elif min_dist > 200:
                status, mod = "Viable Off-Grid (200m-500m)", 10
            else:
                status, mod = "Grid Adjacent (<200m)", -20
                
            return {"nearest_grid_m": min_dist, "status": status, "score_modifier": mod}
        except Exception as e:
            return {"error": str(e), "score_modifier": 0}

    @cached("stress")
    def run_stress_test(self, lat, lon):
        flood_data = self.check_flood_risk(lat, lon)
        grid_data = self.check_grid_distance(lat, lon)
        total_stress_score = flood_data.get('score_modifier', 0) + grid_data.get('score_modifier', 0)
        return {
            "total_stress_score": total_stress_score,
            "is_viable": not flood_data.get('in_flood_zone_3', False),
            "flood_risk": flood_data,
            "grid_proximity": grid_data
        }

if __name__ == "__main__":
    hunter = StressHunter()
    print("--- Testing Remote Location (Highlands) ---")
    print(json.dumps(hunter.run_stress_test(57.1000, -4.5000), indent=2))
    print("\n--- Testing Urban/Flood Location (London Thames) ---")
    print(json.dumps(hunter.run_stress_test(51.5050, -0.0900), indent=2))
