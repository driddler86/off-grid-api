import requests
from cache import cached
import json
from pyproj import Transformer
import logging
logger = logging.getLogger("off-grid-api.resource_hunter")


class ResourceHunter:
    def __init__(self):
        # Corrected endpoints
        self.hydro_url = "https://map.bgs.ac.uk/arcgis/rest/services/GeoIndex_Onshore/hydrogeology/MapServer/identify"
        self.soil_url = "https://map.bgs.ac.uk/arcgis/rest/services/UKSO/mysoil/MapServer/identify"

        # Transformer from WGS84 (GPS) to British National Grid (BNG)
        self.transformer = Transformer.from_crs("epsg:4326", "epsg:27700", always_xy=True)

    def query_arcgis_identify(self, url, easting, northing):
        params = {
            'geometry': f"{easting},{northing}",
            'geometryType': 'esriGeometryPoint',
            'sr': '27700',
            'layers': 'all',
            'tolerance': '50',
            'mapExtent': f"{easting-100},{northing-100},{easting+100},{northing+100}",
            'imageDisplay': '800,600,96',
            'returnGeometry': 'false',
            'f': 'json'
        }
        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.info(f"API Error for {url}: {e}")
            return None

    def get_aquifer_data(self, easting, northing):
        data = self.query_arcgis_identify(self.hydro_url, easting, northing)
        if data and 'results' in data and len(data['results']) > 0:
            attr = data['results'][0].get('attributes', {})
            return {
                "rock_unit": attr.get('ROCK_UNIT', 'Unknown'),
                "productivity": attr.get('CHARACTER', 'Unknown'),
                "flow_mechanism": attr.get('FLOW_MECHA', 'Unknown'),
                "summary": attr.get('SUMMARY', 'Unknown')
            }
        return {"rock_unit": "No data", "productivity": "Unknown"}

    def get_soil_data(self, easting, northing):
        data = self.query_arcgis_identify(self.soil_url, easting, northing)
        if data and 'results' in data and len(data['results']) > 0:
            attr = data['results'][0].get('attributes', {})
            # mysoil uses 'Desc_' for description and 'Texture_1' for texture
            return {
                "soil_description": attr.get('Desc_', 'Unknown'),
                "texture": attr.get('Texture_1', 'Unknown'),
                "layer_name": data['results'][0].get('layerName', 'Unknown')
            }
        return {"soil_description": "No data"}

    @cached("resource")
    def get_resource_score_data(self, lat, lon):
        easting, northing = self.transformer.transform(lon, lat)

        aquifer = self.get_aquifer_data(easting, northing)
        soil = self.get_soil_data(easting, northing)

        return {
            "aquifer": aquifer,
            "soil": soil
        }

if __name__ == '__main__':
    hunter = ResourceHunter()
    # Test with Truro, Cornwall (50.2660, -5.0527)
    result = hunter.get_resource_score_data(50.2660, -5.0527)
    print("\n--- Final Resource Data ---")
    print(json.dumps(result, indent=2))
