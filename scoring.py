class SovereigntyScorer:
    def __init__(self):
        self.weight_planning = 0.40
        self.weight_energy = 0.30
        self.weight_resources = 0.30

    def calculate_planning_score(self, class_q_prob: float, para_84_prob: float, brownfield_prob: float) -> float:
        # Simple max probability for now, can be adjusted based on specific rules
        return max(class_q_prob, para_84_prob, brownfield_prob)

    def calculate_energy_score(self, solar_irradiance: float, wind_speed: float) -> float:
        # Normalize and combine solar and wind (placeholder logic, needs actual normalization bounds)
        # Assuming solar is 0-5 kWh/m2 and wind is 0-10 m/s for a normalized 0-1 score
        norm_solar = min(solar_irradiance / 5.0, 1.0)
        norm_wind = min(wind_speed / 10.0, 1.0)
        return (norm_solar + norm_wind) / 2.0

    def calculate_resource_score(self, soil_grade: float, aquifer_depth: float) -> float:
        # Normalize soil grade (assuming 1 is best, 5 is worst in UK ALC) and aquifer depth
        # Placeholder normalization
        norm_soil = max(0.0, 1.0 - ((soil_grade - 1) / 4.0)) if 1 <= soil_grade <= 5 else 0.0
        # Assuming shallower aquifer is better, max depth 100m for scoring
        norm_aquifer = max(0.0, 1.0 - (aquifer_depth / 100.0))
        return (norm_soil + norm_aquifer) / 2.0

    def calculate_total_score(self, p_score: float, e_score: float, r_score: float) -> float:
        s = (p_score * self.weight_planning) + (e_score * self.weight_energy) + (r_score * self.weight_resources)
        return round(s, 4)

# Example usage
if __name__ == '__main__':
    scorer = SovereigntyScorer()
    p = scorer.calculate_planning_score(0.8, 0.1, 0.0) # 80% chance of Class Q
    e = scorer.calculate_energy_score(3.5, 6.0)        # 3.5 kWh/m2 solar, 6 m/s wind
    r = scorer.calculate_resource_score(3.0, 45.0)     # Grade 3 soil, 45m aquifer depth

    total_score = scorer.calculate_total_score(p, e, r)
    print(f'Planning Score: {p}')
    print(f'Energy Score: {e}')
    print(f'Resource Score: {r}')
    print(f'Total Sovereignty Score (S): {total_score}')
