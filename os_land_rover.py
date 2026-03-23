import requests
from cache import cached
import math
import json
import logging
logger = logging.getLogger("off-grid-api.os_land_rover")


class OSLandRover:
    def __init__(self):
        self.elevation_url = "https://api.opentopodata.org/v1/mapzen"
        self.overpass_url = "http://overpass-api.de/api/interpreter"

    def get_elevations(self, coords):
        # Batch request to avoid 429 Too Many Requests
        locations_str = "|".join([f"{lat},{lon}" for lat, lon in coords])
        try:
            response = requests.get(f"{self.elevation_url}?locations={locations_str}", timeout=10)
            response.raise_for_status()
            data = response.json()
            return [res['elevation'] for res in data['results']]
        except Exception as e:
            logger.info(f"Elevation API Error: {e}")
            return [None] * len(coords)

    def analyze_terrain(self, lat, lon):
        logger.info("Analyzing terrain (Elevation, Slope, and Aspect)...")
        delta = 0.001
        
        coords = [
            (lat, lon),             # center
            (lat + delta, lon),     # north
            (lat - delta, lon),     # south
            (lat, lon + delta),     # east
            (lat, lon - delta)      # west
        ]
        
        elevations = self.get_elevations(coords)
        z_center, z_north, z_south, z_east, z_west = elevations
        
        if None in elevations:
            return {"slope_degrees": 0, "aspect": "Unknown", "is_south_facing": False}
            
        # Calculate rate of change (dz/dx and dz/dy)
        lat_rad = math.radians(lat)
        dx = 2 * (delta * 111320 * math.cos(lat_rad)) # meters
        dy = 2 * (delta * 110574) # meters
        
        dz_dx = (z_east - z_west) / dx
        dz_dy = (z_north - z_south) / dy
        
        # Calculate slope
        slope_rad = math.atan(math.sqrt(dz_dx**2 + dz_dy**2))
        slope_deg = math.degrees(slope_rad)
        
        # Calculate aspect (direction of slope)
        aspect_rad = math.atan2(dz_dy, -dz_dx)
        aspect_deg = math.degrees(aspect_rad)
        if aspect_deg < 0:
            aspect_deg += 360
            
        # Determine if south-facing (between 135 and 225 degrees)
        is_south_facing = 135 <= aspect_deg <= 225
        
        # Compass direction
        dirs = ["N", "NE", "E", "SE", "S", "SW", "W", "NW", "N"]
        compass = dirs[round(aspect_deg / 45) % 8]
        
        return {
            "elevation_m": round(z_center, 2),
            "slope_degrees": round(slope_deg, 2),
            "aspect_degrees": round(aspect_deg, 2),
            "compass_direction": compass,
            "is_south_facing": is_south_facing
        }

    def check_access_rights(self, lat, lon, radius=500):
        logger.info(f"Checking for public roads within {radius}m...")
        query = f"[out:json];way['highway'](around:{radius},{lat},{lon});out center;"
        try:
            response = requests.post(self.overpass_url, data={'data': query}, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            roads = data.get('elements', [])
            if not roads:
                return {"nearest_road_m": ">500", "has_access": False}
            
            min_dist = radius
            for road in roads:
                if 'center' in road:
                    rlat, rlon = road['center']['lat'], road['center']['lon']
                    dist = math.sqrt(((lat - rlat)*111000)**2 + ((lon - rlon)*111000 * math.cos(math.radians(lat)))**2)
                    if dist < min_dist:
                        min_dist = dist
                        
            return {
                "nearest_road_m": round(min_dist, 1),
                "has_access": min_dist <= 150,
                "road_count_in_radius": len(roads)
            }
        except Exception as e:
            logger.info(f"Overpass API Error: {e}")
            return {"nearest_road_m": "Unknown", "has_access": False}

    @cached("terrain")
    def scout_location(self, lat, lon):
        logger.info(f"\n--- OS Land-Rover Scouting: {lat}, {lon} ---")
        terrain = self.analyze_terrain(lat, lon)
        access = self.check_access_rights(lat, lon)
        
        return {
            "terrain": terrain,
            "access": access
        }

if __name__ == '__main__':
    rover = OSLandRover()
    result = rover.scout_location(50.2660, -5.0527)
    print("\n--- Land-Rover Results ---")
    print(json.dumps(result, indent=2))
