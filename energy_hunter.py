import requests
from cache import cached
import logging
logger = logging.getLogger("off-grid-api.energy_hunter")


class EnergyHunter:
    def __init__(self):
        pass

    def get_nasa_power(self, lat, lon):
        # NASA POWER Climatology API (Long term averages for Renewable Energy)
        url = f"https://power.larc.nasa.gov/api/temporal/climatology/point?parameters=ALLSKY_SFC_SW_DWN,WS50M&community=RE&longitude={lon}&latitude={lat}&format=JSON"
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            # 'ANN' is the annual average
            solar = data['properties']['parameter']['ALLSKY_SFC_SW_DWN']['ANN']
            wind = data['properties']['parameter']['WS50M']['ANN']
            return {"solar_kwh_m2_day": solar, "wind_m_s": wind, "source": "NASA POWER"}
        except Exception as e:
            logger.info(f"NASA POWER Error: {e}")
            return None

    def get_open_meteo(self, lat, lon):
        # Open-Meteo Historical API (Averaging the last full year - 2023)
        url = f"https://archive-api.open-meteo.com/v1/archive?latitude={lat}&longitude={lon}&start_date=2023-01-01&end_date=2023-12-31&daily=wind_speed_10m_max,shortwave_radiation_sum&timezone=GMT"
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()

            daily_wind = data['daily']['wind_speed_10m_max']
            daily_solar_mj = data['daily']['shortwave_radiation_sum'] # in MJ/m2

            valid_wind = [w for w in daily_wind if w is not None]
            valid_solar = [s for s in daily_solar_mj if s is not None]

            avg_wind = sum(valid_wind) / len(valid_wind) if valid_wind else 0
            # Convert MJ/m2 to kWh/m2 (1 kWh = 3.6 MJ)
            avg_solar_mj = sum(valid_solar) / len(valid_solar) if valid_solar else 0
            avg_solar_kwh = avg_solar_mj / 3.6

            return {"solar_kwh_m2_day": round(avg_solar_kwh, 2), "wind_m_s": round(avg_wind, 2), "source": "Open-Meteo"}
        except Exception as e:
            logger.info(f"Open-Meteo Error: {e}")
            return None

    @cached("energy")
    def get_energy_score_data(self, lat, lon):
        logger.info(f"Fetching energy data for coordinates: {lat}, {lon}...")
        nasa_data = self.get_nasa_power(lat, lon)
        om_data = self.get_open_meteo(lat, lon)

        logger.info(f"NASA Data: {nasa_data}")
        logger.info(f"Open-Meteo Data: {om_data}")

        # Combine and average if both succeed for maximum reliability
        if nasa_data and om_data:
            avg_solar = (nasa_data['solar_kwh_m2_day'] + om_data['solar_kwh_m2_day']) / 2.0
            avg_wind = (nasa_data['wind_m_s'] + om_data['wind_m_s']) / 2.0
            return {
                "solar_kwh_m2_day": round(avg_solar, 2),
                "wind_m_s": round(avg_wind, 2),
                "sources_used": "NASA POWER & Open-Meteo Combined"
            }
        elif nasa_data:
            return nasa_data
        elif om_data:
            return om_data
        else:
            raise Exception("Failed to fetch data from both energy APIs.")

if __name__ == '__main__':
    hunter = EnergyHunter()
    # Test with Truro, Cornwall (50.2660, -5.0527)
    result = hunter.get_energy_score_data(50.2660, -5.0527)
    print("\n--- Final Energy Data ---")
    print(f"Solar Irradiance: {result['solar_kwh_m2_day']} kWh/m^2/day")
    print(f"Wind Speed: {result['wind_m_s']} m/s")
    print(f"Source: {result.get('sources_used', result.get('source'))}")
